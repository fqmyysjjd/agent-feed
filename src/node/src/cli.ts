#!/usr/bin/env node
import { existsSync, readFileSync } from "node:fs";
import { basename, resolve } from "node:path";

import { ALL_CLIENTS, installedClients, parseClients, syncClients } from "./adapters.js";
import { runChecks } from "./checks.js";
import {
  applyConfigEffects,
  checkConfig,
  configPreflightErrors,
  getConfigValue,
  pruneConfig,
  setConfigValue,
} from "./config.js";
import {
  applyEnvUninstallPlan,
  envUninstallPlan,
  getEnvStatus,
  hasDeletions,
  resolveShell,
  setupAgentFeedHome,
  shellExportText,
  suggestedAgentFeedHome,
} from "./env.js";
import { indexSkillMetadata } from "./skill-index.js";
import { TRUST_ENV, syncAssetTrust, trustConfigPath } from "./trust.js";
import {
  applyTemplates,
  inferProfile,
  inferProjectName,
  isInstalled,
  parseProfile,
  planTemplateWrites,
  upgradePlan,
  type VerificationProfile,
  type WriteAction,
} from "./template.js";
import { VERSION } from "./version.js";

function printHelp(): void {
  console.log(`Agent Feed ${VERSION}

Usage:
  agent-feed init [path] [--clients all|none|codex,claude,cursor] [--profile python|node|custom|none]
  agent-feed sync [path] [-a|--all] [--clients all|none|codex,claude,cursor] [--dry-run]
  agent-feed preview [path]
  agent-feed upgrade [path] [--dry-run]
  agent-feed check [path]
  agent-feed status [path]
  agent-feed config get [key] [--path path]
  agent-feed config set <key> <value> [--path path] [--dry-run]
  agent-feed config check [--path path]
  agent-feed config prune [--dry-run] [-y]
  agent-feed env status [path]
  agent-feed env setup [path] [--home path] [--shell auto|zsh|bash|fish|powershell] [--force] [--dry-run]
  agent-feed env print [--home path] [--shell auto|zsh|bash|fish|powershell]
  agent-feed env uninstall [--home path] [--shell auto|zsh|bash|fish|powershell] [--remove-home] [--dry-run] [-y]
  agent-feed index-skills [path] [--dry-run] [-y]
  agent-feed --version
  agent-feed --help
`);
}

function printCommandHelp(command: string): void {
  const help: Record<string, string> = {
    init: `Agent Feed ${VERSION}

Usage:
  agent-feed init [path] [--clients all|none|codex,claude,cursor] [--profile python|node|custom|none] [--project-name name] [--env-home path] [--dry-run]

Install AGENTS.md and the .agents protocol into a project.
`,
    sync: `Agent Feed ${VERSION}

Usage:
  agent-feed sync [path] [-a|--all] [--clients all|none|codex,claude,cursor] [--dry-run]

Update generated client adapters for an installed Agent Feed project.
`,
    preview: `Agent Feed ${VERSION}

Usage:
  agent-feed preview [path] [--clients all|none|codex,claude,cursor] [--profile python|node|custom|none]

Show init writes or installed-project upgrade diffs without changing files.
`,
    upgrade: `Agent Feed ${VERSION}

Usage:
  agent-feed upgrade [path] [--clients all|none|codex,claude,cursor] [--dry-run]

Refresh managed Agent Feed assets without overwriting project/domain files.
`,
    check: `Agent Feed ${VERSION}

Usage:
  agent-feed check [path]

Validate Agent Feed structure, metadata, and configured client adapters.
`,
    status: `Agent Feed ${VERSION}

Usage:
  agent-feed status [path]

Show a compact health and managed-drift summary.
`,
    config: `Agent Feed ${VERSION}

Usage:
  agent-feed config get [key] [--path path]
  agent-feed config set <key> <value> [--path path] [--dry-run]
  agent-feed config check [--path path]
  agent-feed config prune [--dry-run] [-y]

Read, validate, or update Agent Feed project config and user-level trust config.
`,
    env: `Agent Feed ${VERSION}

Usage:
  agent-feed env status [path]
  agent-feed env setup [path] [--home path] [--shell auto|zsh|bash|fish|powershell] [--force] [--dry-run]
  agent-feed env print [--home path] [--shell auto|zsh|bash|fish|powershell]
  agent-feed env uninstall [--home path] [--shell auto|zsh|bash|fish|powershell] [--remove-home] [--dry-run] [-y]

Create, inspect, print, or remove the user-level AGENT_FEED_HOME binding and config.json.
`,
    "index-skills": `Agent Feed ${VERSION}

Usage:
  agent-feed index-skills [path] [--dry-run] [-y]

Regenerate .agents/skills/README.md and refresh external trust state.
`,
  };
  console.log(help[command] ?? `Unknown command: ${command}`);
}

function parsePath(arg?: string): string {
  return resolve(arg ?? process.cwd());
}

function parseProjectName(target: string): string {
  return basename(target);
}

type ParsedArgs = {
  path?: string;
  options: Map<string, string | boolean>;
};

function parseArgs(args: string[]): ParsedArgs {
  const options = new Map<string, string | boolean>();
  let path: string | undefined;
  const valueOptions = new Set([
    "--clients",
    "--profile",
    "--project-name",
    "--path",
    "--env-home",
    "--home",
    "--shell",
  ]);
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === "-a") {
      options.set("--all", true);
      continue;
    }
    if (arg === "-y") {
      options.set("-y", true);
      continue;
    }
    if (arg.startsWith("--")) {
      const [key, inlineValue] = arg.split("=", 2);
      if (inlineValue !== undefined) {
        options.set(key, inlineValue);
      } else if (valueOptions.has(key) && args[index + 1] && !args[index + 1].startsWith("-")) {
        options.set(key, args[index + 1]);
        index += 1;
      } else {
        options.set(key, true);
      }
      continue;
    }
    path ??= arg;
  }
  return { path, options };
}

function optionString(options: Map<string, string | boolean>, key: string): string | undefined {
  const value = options.get(key);
  return typeof value === "string" ? value : undefined;
}

function initCommand(target: string, args: ParsedArgs): number {
  if (isInstalled(target)) {
    console.error("Agent Feed is already installed; use agent-feed status or upgrade.");
    return 3;
  }
  const projectName = optionString(args.options, "--project-name") ?? parseProjectName(target);
  const profile = parseProfile(optionString(args.options, "--profile"), "none");
  const dryRun = args.options.has("--dry-run");
  const clients = parseClients(
    optionString(args.options, "--clients"),
    args.options.has("--all"),
    ALL_CLIENTS,
  );
  if (dryRun) {
    const envActions = ensureTrustHomeForInit(target, {
      envHome: optionString(args.options, "--env-home"),
      dryRun,
      noInput: true,
    });
    if (!envActions.ok) {
      printErrors("Environment setup blocked", envActions.errors);
      return 3;
    }
    printActions([
      ...envActions.actions,
      ...planTemplateWrites(target, projectName, profile),
      ...syncClients(target, clients, true, true).actions,
    ]);
    return 0;
  }
  const envReady = ensureTrustHomeForInit(target, {
    envHome: optionString(args.options, "--env-home"),
    dryRun,
    noInput: true,
  });
  if (!envReady.ok) {
    printErrors("Environment setup blocked", envReady.errors);
    return 3;
  }
  const adapterPreflight = syncClients(target, clients, true, true);
  if (adapterPreflight.errors.length > 0) {
    printErrors("Init blocked", adapterPreflight.errors);
    return 3;
  }
  const actions = applyTemplates(target, projectName, profile);
  const adapters = syncClients(target, clients, false);
  const trust = syncAssetTrust(target, {
    dryRun: false,
    acceptChanged: true,
    projectName,
    pruneMissing: true,
  });
  printActions([...envReady.actions, ...actions, ...adapters.actions, ...trust.actions]);
  if (adapters.errors.length > 0 || trust.errors.length > 0) {
    printErrors("Init blocked", [...adapters.errors, ...trust.errors]);
    return 3;
  }
  console.log(`Initialized Agent Feed in ${target}`);
  return 0;
}

function checkCommand(target: string): number {
  const report = runChecks(target);
  if (report.errors.length > 0) {
    printErrors("Checks blocked", report.errors);
    for (const warning of report.warnings) {
      console.warn(`warning: ${warning}`);
    }
    return 1;
  }
  if (report.warnings.length > 0) {
    console.log("Checks passed with warnings:");
    for (const warning of report.warnings) {
      console.log(`- ${warning}`);
    }
  } else {
    console.log("Checks passed.");
  }
  return 0;
}

function statusCommand(target: string): number {
  const installed = isInstalled(target);
  const report = runChecks(target);
  const managed = resolve(target, ".agents/agent-feed.json");
  const metadata = existsSync(managed)
    ? (JSON.parse(readFileSync(managed, "utf8")) as { verification_profile?: unknown })
    : {};
  const drift = installed ? upgradePlan(target, inferProjectName(target), inferProfile(target), true) : null;
  const changed = drift ? drift.actions.filter((action) => !action.action.startsWith("skip")) : [];

  console.log(`Agent Feed Status: ${target}`);
  console.log(`Canonical: ${installed && report.errors.length === 0 ? "ready" : "blocked"}`);
  console.log(
    `Verification profile: ${
      typeof metadata.verification_profile === "string" ? metadata.verification_profile : "unknown"
    }`,
  );
  if (installed) {
    console.log(`Managed drift: ${changed.length === 0 ? "none" : `${changed.length} change(s)`}`);
  }
  if (report.errors.length > 0) {
    printErrors("Diagnostics", report.errors);
  }
  for (const warning of report.warnings) {
    console.warn(`warning: ${warning}`);
  }
  console.log(statusNextStep(installed, report.errors.length, report.warnings.length, changed.length));
  return report.errors.length === 0 ? 0 : 1;
}

function syncCommand(target: string, args: ParsedArgs): number {
  const clients = parseClients(
    optionString(args.options, "--clients"),
    args.options.has("--all"),
    ALL_CLIENTS,
  );
  const result = syncClients(target, clients, args.options.has("--dry-run"));
  printActions(result.actions);
  if (result.errors.length > 0) {
    printErrors("Sync blocked", result.errors);
    return 3;
  }
  console.log("agent-feed: sync complete");
  return 0;
}

function previewCommand(target: string, args: ParsedArgs): number {
  const installed = isInstalled(target);
  const projectName = optionString(args.options, "--project-name") ?? inferProjectName(target);
  const profile = installed
    ? inferProfile(target)
    : parseProfile(optionString(args.options, "--profile"), "python");
  const clients = installed
    ? installedClients(target)
    : parseClients(optionString(args.options, "--clients"), args.options.has("--all"), ALL_CLIENTS);
  const actions = installed
    ? upgradePlan(target, projectName, profile, true)
    : { actions: planTemplateWrites(target, projectName, profile), errors: [] };
  const adapters = syncClients(target, clients, true, !installed);
  printActions([...actions.actions, ...adapters.actions], true);
  if (actions.errors.length > 0 || adapters.errors.length > 0) {
    printErrors("Preview blocked", [...actions.errors, ...adapters.errors]);
    return 3;
  }
  return 0;
}

function upgradeCommand(target: string, args: ParsedArgs): number {
  const dryRun = args.options.has("--dry-run");
  const projectName = optionString(args.options, "--project-name") ?? inferProjectName(target);
  const profile = inferProfile(target);
  const clients = parseClients(
    optionString(args.options, "--clients"),
    args.options.has("--all"),
    installedClients(target),
  );
  const canonical = upgradePlan(target, projectName, profile, dryRun);
  const adapters = syncClients(target, clients, dryRun);
  const trust = syncAssetTrust(target, {
    dryRun,
    acceptChanged: true,
    projectName,
    pruneMissing: true,
  });
  printActions([...canonical.actions, ...adapters.actions, ...trust.actions], true);
  if (canonical.errors.length > 0 || adapters.errors.length > 0 || trust.errors.length > 0) {
    printErrors("Upgrade blocked", [...canonical.errors, ...adapters.errors, ...trust.errors]);
    return 3;
  }
  console.log(dryRun ? "agent-feed: upgrade preview complete" : "agent-feed: upgrade complete");
  return 0;
}

function configCommand(args: string[]): number {
  const [subcommand = "get", ...rest] = args;
  const parsed = parseArgs(rest);
  const target = parsePath(optionString(parsed.options, "--path") ?? parsed.path);
  if (subcommand === "get") {
    const result = getConfigValue(target, parsed.path);
    if (result.errors.length > 0) {
      printErrors("Config read blocked", result.errors);
      return 3;
    }
    console.log(typeof result.value === "string" ? result.value : JSON.stringify(result.value, null, 2));
    return 0;
  }
  if (subcommand === "check") {
    const report = checkConfig(target);
    if (report.errors.length > 0) {
      printErrors("Config diagnostics", report.errors);
    }
    for (const warning of report.warnings) {
      console.warn(`warning: ${warning}`);
    }
    if (report.errors.length === 0 && report.warnings.length === 0) {
      console.log("Config checks passed.");
    }
    if (report.warnings.length > 0) {
      console.log("Next: run agent-feed config prune -y to remove stale project records.");
    }
    return report.errors.length === 0 ? 0 : 1;
  }
  if (subcommand === "prune") {
    const dryRun = parsed.options.has("--dry-run");
    const yes = parsed.options.has("-y") || parsed.options.has("--yes");
    if (!dryRun && !yes) {
      const preview = pruneConfig(true);
      if (preview.errors.length > 0) {
        printErrors("Config prune blocked", preview.errors);
        return 3;
      }
      if (preview.actions.length === 0) {
        console.log("No stale project entries found.");
        return 0;
      }
      printActions(preview.actions);
      console.error("Config prune blocked:");
      console.error("- pass -y to remove stale project records");
      return 3;
    }
    const result = pruneConfig(dryRun);
    if (result.errors.length > 0) {
      printErrors("Config prune blocked", result.errors);
      return 3;
    }
    if (result.actions.length === 0) {
      console.log("No stale project entries found.");
      return 0;
    }
    printActions(result.actions);
    if (!dryRun) {
      console.log("agent-feed: stale project entries removed");
    }
    return 0;
  }
  if (subcommand === "set") {
    const positional = positionalArgs(rest, new Set(["--path"]));
    const [key, value] = positional;
    if (!key || value === undefined) {
      printErrors("Config update blocked", ["config set requires <key> and <value>"]);
      return 3;
    }
    const dryRun = parsed.options.has("--dry-run");
    if (!dryRun) {
      const preflight = configPreflightErrors(target);
      if (preflight.length > 0) {
        printErrors("Config update blocked", preflight);
        return 3;
      }
    }
    const write = setConfigValue(target, key, value, dryRun);
    const effects = dryRun ? { actions: [] as WriteAction[], errors: [] as string[] } : applyConfigEffects(target, false);
    printActions([...write.actions, ...effects.actions], true);
    if (write.errors.length > 0 || effects.errors.length > 0) {
      printErrors("Config update blocked", [...write.errors, ...effects.errors]);
      return 3;
    }
    if (!dryRun) {
      const report = checkConfig(target);
      if (report.errors.length > 0) {
        printErrors("Config diagnostics", report.errors);
        return 3;
      }
      for (const warning of report.warnings) {
        console.warn(`warning: ${warning}`);
      }
      console.log("agent-feed: config updated");
    }
    return 0;
  }
  printCommandHelp("config");
  return 1;
}

function envCommand(args: string[]): number {
  const [subcommand = "status", ...rest] = args;
  const parsed = parseArgs(rest);
  if (subcommand === "status") {
    const target = parsePath(parsed.path);
    const status = getEnvStatus(target);
    if (status.errors.length === 0 && status.configured) {
      console.log("Agent Feed environment is ready.");
    } else {
      console.log("Agent Feed environment needs setup.");
    }
    console.log(`${TRUST_ENV}: ${status.home ?? "<not set>"}`);
    console.log(`recommended: ${status.recommendation}`);
    if (status.configFile) {
      console.log(`config: ${status.configFile}`);
    }
    if (status.errors.length > 0) {
      printErrors("Environment diagnostics", status.errors);
      return 1;
    }
    return 0;
  }
  if (subcommand === "print") {
    const shell = resolveShell(optionString(parsed.options, "--shell"));
    if (!shell.shell) {
      printErrors("Environment print blocked", [shell.error ?? "unsupported shell"]);
      return 3;
    }
    const home = parsePath(optionString(parsed.options, "--home") ?? suggestedAgentFeedHome());
    console.log(shellExportText(home, shell.shell));
    return 0;
  }
  if (subcommand === "setup") {
    const dryRun = parsed.options.has("--dry-run");
    const result = setupAgentFeedHome({
      home: optionString(parsed.options, "--home"),
      target: parsePath(parsed.path),
      shell: optionString(parsed.options, "--shell"),
      dryRun,
      force: parsed.options.has("--force"),
    });
    printActions(result.actions);
    if (result.errors.length > 0) {
      printErrors("Environment setup blocked", result.errors);
      return 3;
    }
    if (dryRun) {
      console.log("agent-feed: environment setup preview complete");
    } else {
      console.log("agent-feed: environment configured");
      console.log(`${TRUST_ENV}: ${result.home}`);
    }
    return 0;
  }
  if (subcommand === "uninstall") {
    const dryRun = parsed.options.has("--dry-run");
    const yes = parsed.options.has("-y") || parsed.options.has("--yes");
    const plan = envUninstallPlan({
      home: optionString(parsed.options, "--home"),
      shell: optionString(parsed.options, "--shell"),
      dryRun,
      removeHome: parsed.options.has("--remove-home"),
    });
    printActions(plan.actions);
    if (plan.errors.length > 0) {
      printErrors("Environment uninstall blocked", plan.errors);
      return 3;
    }
    if (!hasDeletions(plan.actions)) {
      console.log("No Agent Feed environment changes were found.");
      return 0;
    }
    if (dryRun) {
      console.log("agent-feed: environment uninstall preview complete. Rerun with -y to apply.");
      return 0;
    }
    if (!yes) {
      printErrors("Environment uninstall blocked", ["confirmation is required; pass -y to apply the cleanup plan"]);
      return 3;
    }
    const applied = applyEnvUninstallPlan(plan.actions, {
      shell: optionString(parsed.options, "--shell"),
    });
    printActions(applied);
    console.log("agent-feed: environment uninstall complete");
    return 0;
  }
  printCommandHelp("env");
  return 1;
}

function positionalArgs(args: string[], valueOptions: Set<string>): string[] {
  const values: string[] = [];
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (valueOptions.has(arg)) {
      index += 1;
      continue;
    }
    if (arg.startsWith("--")) {
      continue;
    }
    values.push(arg);
  }
  return values;
}

function ensureTrustHomeForInit(
  target: string,
  options: { envHome?: string; dryRun: boolean; noInput: boolean },
): { ok: boolean; actions: WriteAction[]; errors: string[] } {
  const config = trustConfigPath();
  if (config.errors.length === 0) {
    return { ok: true, actions: [], errors: [] };
  }
  const missingEnv = config.errors.some((error) => error.includes(`${TRUST_ENV} is required`));
  if (!missingEnv) {
    return { ok: true, actions: [], errors: [] };
  }
  const recommended = options.envHome ?? suggestedAgentFeedHome(target);
  if (!options.envHome && !options.dryRun && options.noInput) {
    return {
      ok: false,
      actions: [],
      errors: [
        `${TRUST_ENV} is required before init can record AI asset trust.`,
        `Run: agent-feed env setup ${target}`,
        "Or rerun init with --env-home PATH.",
      ],
    };
  }
  const result = setupAgentFeedHome({
    home: recommended,
    target,
    dryRun: options.dryRun,
    force: false,
  });
  if (options.dryRun && result.errors.length === 0) {
    process.env[TRUST_ENV] = result.home;
  }
  return {
    ok: result.errors.length === 0,
    actions: result.actions,
    errors:
      result.errors.length === 0
        ? []
        : [
            ...result.errors,
            `Run: agent-feed env setup ${target}${options.envHome ? ` --home ${recommended}` : ""}`,
            "If shell detection failed, add --shell zsh, bash, fish, or powershell.",
          ],
  };
}

function indexSkillsCommand(target: string, args: ParsedArgs): number {
  const dryRun = args.options.has("--dry-run");
  const acceptChanged = args.options.has("-y") || args.options.has("--yes");
  const preflight = configPreflightErrors(target);
  if (preflight.length > 0) {
    printErrors("Skill indexing blocked", preflight);
    return 3;
  }
  const actions = indexSkillMetadata(target, dryRun);
  const trust = syncAssetTrust(target, {
    dryRun,
    acceptChanged,
    projectName: inferProjectName(target),
    pruneMissing: true,
  });
  printActions([...actions.actions, ...trust.actions], true);
  if (actions.errors.length > 0 || trust.errors.length > 0) {
    printErrors("Skill indexing blocked", [...actions.errors, ...trust.errors]);
    return 3;
  }
  console.log(dryRun ? "agent-feed: skill index preview complete" : "agent-feed: skills indexed");
  return 0;
}

function printActions(actions: WriteAction[], showDiff = false): void {
  for (const action of actions) {
    const detail = action.detail ? ` ${action.detail}` : "";
    console.log(`${action.action} ${action.path}${detail}`);
    if (showDiff && action.diff) {
      console.log(action.diff);
    }
  }
}

function printErrors(title: string, errors: string[]): void {
  console.error(`${title}:`);
  for (const error of errors) {
    console.error(`- ${error}`);
  }
}

function statusNextStep(
  installed: boolean,
  errors: number,
  warnings: number,
  driftChanges: number,
): string {
  if (!installed) {
    return "Next: run agent-feed init";
  }
  if (errors > 0) {
    return "Next: run agent-feed check for the full failure list";
  }
  if (warnings > 0) {
    return "Next: review warnings, then run agent-feed preview";
  }
  if (driftChanges > 0) {
    return "Next: run agent-feed preview to inspect managed diffs";
  }
  return "Next: no action required";
}

function main(argv: string[]): number {
  const [first, ...rest] = argv;
  const command = first ?? "--help";
  if (command === "--help" || command === "-h") {
    printHelp();
    return 0;
  }
  if (command === "--version" || command === "-v") {
    console.log(VERSION);
    return 0;
  }

  try {
    if (rest.includes("--help") || rest.includes("-h")) {
      printCommandHelp(command);
      return command in {
        init: true,
        sync: true,
        preview: true,
        upgrade: true,
        check: true,
        status: true,
        config: true,
        env: true,
        "index-skills": true,
      }
        ? 0
        : 1;
    }
    const parsed = parseArgs(rest);
    const target = parsePath(parsed.path);
    if (command === "config") {
      return configCommand(rest);
    }
    if (command === "env") {
      return envCommand(rest);
    }
    if (command === "index-skills") {
      return indexSkillsCommand(target, parsed);
    }
    if (command === "init") {
      return initCommand(target, parsed);
    }
    if (command === "sync") {
      return syncCommand(target, parsed);
    }
    if (command === "preview") {
      return previewCommand(target, parsed);
    }
    if (command === "upgrade") {
      return upgradeCommand(target, parsed);
    }
    if (command === "check") {
      return checkCommand(target);
    }
    if (command === "status") {
      return statusCommand(target);
    }
    printHelp();
    return 1;
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    return 3;
  }
}

process.exit(main(process.argv.slice(2)));
