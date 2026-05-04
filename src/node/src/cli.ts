#!/usr/bin/env node
import { existsSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { basename, dirname, join, resolve } from "node:path";

import ora from "ora";

import { ALL_CLIENTS, installedClients, parseClients, syncClients, type Client } from "./adapters.js";
import { ALL_CHECKS, collectStatus, parseChecks, runChecks, type CheckName } from "./checks.js";
import {
  applyConfigEffects,
  checkConfig,
  configPreflightErrors,
  getConfigValue,
  pruneConfig,
  setConfigValue,
} from "./config.js";
import {
  hasDiffDetails,
  printActionResult,
  printCheckReport,
  printConfigCheckReport,
  printDiffDetails,
  printDiffHint,
  printErrorPanel,
  printInfo,
  printInspectionPlan,
  printNextStep,
  printPanel,
  printRecommendedCommand,
  printStatus,
  printWarning,
  printWelcome,
  printWritePlan,
} from "./console.js";
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
import { backupActionsInclude, backupLegacyAiAssets } from "./legacy-migration.js";
import { indexSkillMetadata } from "./skill-index.js";
import {
  CURATED_HUBS,
  fetchRemoteSkill,
  installRemoteSkillPackage,
  preferredGithubToken,
  previewSkillTree,
  saveGithubToken,
  searchRemoteSkills,
  skillHubFailureHelp,
  type RemoteSkill,
  type RemoteSkillPackage,
} from "./skill-hub.js";
import {
  canPrompt,
  isPromptCanceled,
  promptChecks,
  promptClients,
  promptClientsStep,
  promptConfirm,
  promptMainAction,
  promptPathStep,
  promptSecret,
  promptSkillKeyword,
  promptSkillSelection,
  promptTextStep,
  promptViewDiffKey,
  promptVerificationProfile,
  promptVerificationProfileStep,
} from "./prompts.js";
import { TRUST_ENV, syncAssetTrust, trustConfigPath, trustPreviewActions } from "./trust.js";
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
import { applyUninstallPlan, uninstallHasDeletions, uninstallPlan } from "./uninstall.js";
import { VERSION } from "./version.js";

function printHelp(): void {
  console.log(`Agent Feed ${VERSION}

Usage:
  agent-feed init [path] [--clients all|none|codex,claude,cursor] [--profile python|node|custom|none] [--project-name name] [--env-home path] [--dry-run] [-y] [--no-input] [--force-generated]
  agent-feed sync [path] [-a|--all] [--clients all|none|codex,claude,cursor] [--dry-run] [--force-generated] [--no-input]
  agent-feed preview [path] [--clients all|none|codex,claude,cursor] [--profile python|node|custom|none] [--project-name name]
  agent-feed upgrade [path] [--clients all|none|codex,claude,cursor] [--project-name name] [--dry-run] [-y] [--no-input]
  agent-feed uninstall [path] [--dry-run] [-y] [--no-input]
  agent-feed check [path] [--checks ...|--only ...] [--clients ...] [-a|--all] [--json] [--no-input]
  agent-feed status [path] [--json]
  agent-feed config get [key] [--path path] [--json]
  agent-feed config set <key> <value> [--path path] [--dry-run]
  agent-feed config check [--path path] [--json]
  agent-feed config prune [--dry-run] [-y] [--no-input]
  agent-feed env status [path]
  agent-feed env setup [path] [--home path] [--shell auto|zsh|bash|fish|powershell] [--force] [--dry-run]
  agent-feed env print [--home path] [--shell auto|zsh|bash|fish|powershell]
  agent-feed env uninstall [--home path] [--shell auto|zsh|bash|fish|powershell] [--remove-home] [--dry-run] [-y] [--no-input]
  agent-feed index-skills [path] [--dry-run] [-y]
  agent-feed skill-hub [path] [-k|--keyword keyword] [--dry-run] [--save-token|--no-save-token] [--no-input]
  agent-feed --version
  agent-feed --help
`);
}

function printVersion(): void {
  console.log(`agent-feed ${VERSION}`);
  console.log(`executable: ${resolve(process.argv[1] ?? "agent-feed")}`);
  console.log(`package: ${dirname(fileURLToPath(import.meta.url))}`);
}

function printCommandHelp(command: string): void {
  const help: Record<string, string> = {
    init: `Agent Feed ${VERSION}

Usage:
  agent-feed init [path] [--clients all|none|codex,claude,cursor] [--profile python|node|custom|none] [--project-name name] [--env-home path] [--dry-run] [-y] [--no-input]

Install AGENTS.md and the .agents protocol into a project.
`,
    sync: `Agent Feed ${VERSION}

Usage:
  agent-feed sync [path] [-a|--all] [--clients all|none|codex,claude,cursor] [--dry-run] [--force-generated] [--no-input]

Update generated client adapters for an installed Agent Feed project.
`,
    preview: `Agent Feed ${VERSION}

Usage:
  agent-feed preview [path] [--clients all|none|codex,claude,cursor] [--profile python|node|custom|none]

Show init writes or installed-project upgrade diffs without changing files.
`,
    upgrade: `Agent Feed ${VERSION}

Usage:
  agent-feed upgrade [path] [--clients all|none|codex,claude,cursor] [--dry-run] [-y] [--no-input]

Refresh managed Agent Feed assets without overwriting project/domain files.
`,
    uninstall: `Agent Feed ${VERSION}

Usage:
  agent-feed uninstall [path] [--dry-run] [-y] [--no-input]

Remove Agent Feed-managed assets without deleting unmanaged user files.
`,
    check: `Agent Feed ${VERSION}

Usage:
  agent-feed check [path] [--checks ...|--only ...] [--clients ...] [-a|--all] [--json] [--no-input]

Validate Agent Feed structure, metadata, and configured client adapters.
`,
    status: `Agent Feed ${VERSION}

Usage:
  agent-feed status [path] [--json]

Show a compact health and managed-drift summary.
`,
    config: `Agent Feed ${VERSION}

Usage:
  agent-feed config get [key] [--path path] [--json]
  agent-feed config set <key> <value> [--path path] [--dry-run]
  agent-feed config check [--path path] [--json]
  agent-feed config prune [--dry-run] [-y] [--no-input]

Read, validate, or update Agent Feed project config and user-level trust config.
`,
    env: `Agent Feed ${VERSION}

Usage:
  agent-feed env status [path]
  agent-feed env setup [path] [--home path] [--shell auto|zsh|bash|fish|powershell] [--force] [--dry-run]
  agent-feed env print [--home path] [--shell auto|zsh|bash|fish|powershell]
  agent-feed env uninstall [--home path] [--shell auto|zsh|bash|fish|powershell] [--remove-home] [--dry-run] [-y] [--no-input]

Create, inspect, print, or remove the user-level AGENT_FEED_HOME binding and config.json.
`,
    "index-skills": `Agent Feed ${VERSION}

Usage:
  agent-feed index-skills [path] [--dry-run] [-y]

Regenerate .agents/skills/README.md and refresh external trust state.
`,
    "skill-hub": `Agent Feed ${VERSION}

Usage:
  agent-feed skill-hub [path] [-k|--keyword keyword] [--dry-run] [--save-token|--no-save-token] [--no-input]

Search curated public skill hubs and install matched skills.
`,
  };
  console.log(help[command] ?? `Unknown command: ${command}`);
}

function normalizeCommandAlias(command: string | undefined, rest: string[]): { command: string | undefined; rest: string[] } {
  if (command === "i") {
    return { command: "init", rest };
  }
  if (command === "s") {
    return { command: "sync", rest: rest.includes("--no-input") ? rest : [...rest, "--no-input"] };
  }
  if (command === "c") {
    return { command: "check", rest: rest.includes("--no-input") ? rest : [...rest, "--no-input"] };
  }
  return { command, rest };
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
    "--checks",
    "--only",
    "--profile",
    "--project-name",
    "--path",
    "--env-home",
    "--home",
    "--shell",
    "--keyword",
  ]);
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === "-a") {
      options.set("--all", true);
      continue;
    }
    if (arg === "-k" && args[index + 1] && !args[index + 1].startsWith("-")) {
      options.set("--keyword", args[index + 1]);
      index += 1;
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

function isNoInput(options: Map<string, string | boolean>): boolean {
  return options.has("-y") || options.has("--yes") || options.has("--no-input");
}

type InitWizardResult = {
  target: string;
  projectName: string;
  clients: Client[];
  profile: VerificationProfile;
};

type UpgradeWizardResult = {
  target: string;
  projectName: string;
  clients: Client[];
};

async function promptInitWizard(options: {
  target: string;
  projectName: string;
  clients: Client[];
  profile: VerificationProfile;
  projectNameExplicit: boolean;
}): Promise<InitWizardResult | undefined> {
  let step = 0;
  let currentTarget = options.target;
  let currentProjectName = options.projectName;
  let currentClients = options.clients;
  let currentProfile = options.profile;

  while (step < 4) {
    if (step === 0) {
      const value = await promptPathStep("Project path", currentTarget);
      if (value === undefined) {
        return undefined;
      }
      currentTarget = parsePath(value || currentTarget);
      if (!options.projectNameExplicit) {
        currentProjectName = parseProjectName(currentTarget);
      }
      step += 1;
      continue;
    }
    if (step === 1) {
      const value = await promptTextStep("Project display name", currentProjectName);
      if (value === undefined) {
        step -= 1;
        printStepBack("Project path");
        continue;
      }
      currentProjectName = value.trim() || currentProjectName;
      step += 1;
      continue;
    }
    if (step === 2) {
      const value = await promptClientsStep("Select AI clients to configure", currentClients);
      if (value === undefined) {
        step -= 1;
        printStepBack("project display name");
        continue;
      }
      currentClients = value;
      step += 1;
      continue;
    }
    const value = await promptVerificationProfileStep("Select project verification profile", currentProfile);
    if (value === undefined) {
      step -= 1;
      printStepBack("AI clients");
      continue;
    }
    currentProfile = value;
    step += 1;
  }

  return {
    target: currentTarget,
    projectName: currentProjectName,
    clients: currentClients,
    profile: currentProfile,
  };
}

async function promptUpgradeWizard(options: {
  target: string;
  projectName: string;
  clients: Client[];
  clientsExplicit: boolean;
  projectNameExplicit: boolean;
}): Promise<UpgradeWizardResult | undefined> {
  let step = 0;
  let currentTarget = options.target;
  let currentProjectName = options.projectName;
  let currentClients = options.clients;

  while (step < 3) {
    if (step === 0) {
      const value = await promptPathStep("Project path", currentTarget);
      if (value === undefined) {
        return undefined;
      }
      currentTarget = parsePath(value || currentTarget);
      if (!options.projectNameExplicit) {
        currentProjectName = inferProjectName(currentTarget);
      }
      if (!options.clientsExplicit) {
        currentClients = installedClients(currentTarget);
      }
      step += 1;
      continue;
    }
    if (step === 1) {
      const value = await promptTextStep("Project display name", currentProjectName);
      if (value === undefined) {
        step -= 1;
        printStepBack("Project path");
        continue;
      }
      currentProjectName = value.trim() || currentProjectName;
      step += 1;
      continue;
    }
    const value = await promptClientsStep("Select AI clients to configure", currentClients);
    if (value === undefined) {
      step -= 1;
      printStepBack("project display name");
      continue;
    }
    currentClients = value;
    step += 1;
  }

  return {
    target: currentTarget,
    projectName: currentProjectName,
    clients: currentClients,
  };
}

function printStepBack(label: string): void {
  printInfo(`Returned to ${label}.`);
}

async function initCommand(target: string, args: ParsedArgs): Promise<number> {
  let currentTarget = target;
  let projectName = optionString(args.options, "--project-name") ?? parseProjectName(target);
  let clients = parseClients(optionString(args.options, "--clients"), args.options.has("--all"), ALL_CLIENTS);
  let explicitProfile = optionString(args.options, "--profile");
  const dryRun = args.options.has("--dry-run");
  const noInput = isNoInput(args.options);

  if (canPrompt() && !args.path && !noInput) {
    printWelcome();
    const wizard = await promptInitWizard({
      target: currentTarget,
      projectName,
      clients,
      profile: parseProfile(explicitProfile, "python"),
      projectNameExplicit: Boolean(optionString(args.options, "--project-name")),
    });
    if (!wizard) {
      printActionResult({
        title: "Initialization",
        message: "Canceled",
        kind: "warning",
      });
      return 0;
    }
    currentTarget = wizard.target;
    projectName = wizard.projectName;
    clients = wizard.clients;
    explicitProfile = wizard.profile;
  }

  const profile = await resolveInitProfile(explicitProfile, { noInput });
  if (!profile) {
    return 3;
  }

  const envActions = await ensureTrustHomeForInit(currentTarget, {
    envHome: optionString(args.options, "--env-home"),
    dryRun,
    noInput,
  });
  if (!envActions.ok) {
    printErrorPanel("Environment setup blocked", envActions.errors);
    return 3;
  }

  if (dryRun) {
    const conflicts = initConflictErrors(currentTarget);
    if (conflicts.length > 0) {
      printErrorPanel("Init blocked", conflicts);
      return 3;
    }
    const backup = backupLegacyAiAssets(currentTarget, {
      projectName,
      verificationProfile: profile,
      dryRun,
    });
    if (backup.errors.length > 0) {
      printErrorPanel("Init blocked", backup.errors);
      return 3;
    }
    const adapters = syncClients(currentTarget, clients, {
      dryRun: true,
      assumeInitialized: true,
      forceGenerated: true,
    });
    const adapterErrors = adapters.errors.filter((error) =>
      !plannedBackupResolvesInitAdapterError(error, backup.actions, currentTarget),
    );
    printWritePlan([
      ...envActions.actions,
      ...backup.actions,
      ...planTemplateWrites(currentTarget, projectName, profile),
      ...adapters.actions,
    ]);
    if (adapterErrors.length > 0) {
      printErrorPanel("Init blocked", adapterErrors);
      return 3;
    }
    return 0;
  }

  const conflicts = initConflictErrors(currentTarget);
  if (conflicts.length > 0) {
    printErrorPanel("Init blocked", conflicts);
    return 3;
  }
  const backup = backupLegacyAiAssets(currentTarget, {
    projectName,
    verificationProfile: profile,
    dryRun: false,
  });
  if (backup.errors.length > 0) {
    printErrorPanel("Init blocked", backup.errors);
    return 3;
  }
  const adapterPreflight = syncClients(currentTarget, clients, {
    dryRun: true,
    assumeInitialized: true,
    forceGenerated: true,
  });
  if (adapterPreflight.errors.length > 0) {
    printErrorPanel("Init blocked", adapterPreflight.errors);
    return 3;
  }
  const actions = applyTemplates(currentTarget, projectName, profile);
  const adapters = syncClients(currentTarget, clients, {
    dryRun: false,
    forceGenerated: false,
  });
  const trust = syncAssetTrust(currentTarget, {
    dryRun: false,
    acceptChanged: true,
    projectName,
    pruneMissing: true,
  });
  printWritePlan([...envActions.actions, ...backup.actions, ...actions, ...adapters.actions, ...trust.actions]);
  if (adapters.errors.length > 0 || trust.errors.length > 0) {
    printErrorPanel("Init blocked", [...adapters.errors, ...trust.errors]);
    return 3;
  }
  printActionResult({
    title: "Agent Feed",
    message: `Initialized Agent Feed in ${currentTarget}`,
    kind: "success",
  });
  return 0;
}

function initConflictErrors(target: string): string[] {
  const errors: string[] = [];
  if (isInstalled(target) && existsSync(join(target, ".agents", "agent-feed.json"))) {
    errors.push("Agent Feed is already installed; use `agent-feed status` or `agent-feed upgrade`.");
  }
  for (const relPath of ["AGENTS.md", ".agents"]) {
    const path = join(target, relPath);
    if (!existsSync(path)) {
      continue;
    }
    const stats = statSync(path);
    if (relPath === "AGENTS.md" && !stats.isFile()) {
      errors.push("AGENTS.md exists but is not a file.");
    }
    if (relPath === ".agents" && !stats.isDirectory()) {
      errors.push(".agents exists but is not a directory.");
    }
  }
  return errors;
}

function plannedBackupResolvesInitAdapterError(error: string, backupActions: WriteAction[], target: string): boolean {
  if (error.includes("CLAUDE.md") && backupActionsInclude(backupActions, "CLAUDE.md", target)) {
    return true;
  }
  if (error.includes(".claude/skills") && backupActionsInclude(backupActions, ".claude/skills", target)) {
    return true;
  }
  if (error.includes(".cursor/rules/agent-feed.mdc") && backupActionsInclude(backupActions, ".cursor/rules", target)) {
    return true;
  }
  return false;
}

async function parseCheckSelection(args: ParsedArgs): Promise<CheckName[]> {
  if (args.options.has("--all")) {
    return [...ALL_CHECKS];
  }
  const raw = optionString(args.options, "--checks") ?? optionString(args.options, "--only");
  const clientChecks =
    optionString(args.options, "--clients") !== undefined
      ? parseClients(optionString(args.options, "--clients"), false, []).map((client): CheckName => client)
      : [];
  if (raw) {
    return [...new Set([...parseChecks(raw, [...ALL_CHECKS]), ...clientChecks])];
  }
  if (isNoInput(args.options) || !canPrompt()) {
    return [...new Set([...ALL_CHECKS, ...clientChecks])];
  }
  const selected = await promptChecks([...ALL_CHECKS]);
  if (selected.length === 0) {
    throw new Error("select at least one check, or pass `-a` to run every check");
  }
  return [...new Set([...selected, ...clientChecks])];
}

async function parseSyncClients(args: ParsedArgs): Promise<Client[]> {
  const raw = optionString(args.options, "--clients");
  if (args.options.has("--all") && raw) {
    throw new Error("use either -a/--all or --clients, not both");
  }
  if (args.options.has("--all") || raw || args.options.has("--no-input")) {
    return parseClients(raw, args.options.has("--all"), ALL_CLIENTS);
  }
  if (!canPrompt()) {
    return parseClients(raw, false, ALL_CLIENTS);
  }
  return promptClients("Select AI clients to configure", ALL_CLIENTS);
}

function previewActions(
  target: string,
  options: Map<string, string | boolean>,
): { actions: WriteAction[]; errors: string[] } {
  const installed = isInstalled(target);
  const projectName = optionString(options, "--project-name") ?? inferProjectName(target);
  const profile = installed
    ? inferProfile(target)
    : parseProfile(optionString(options, "--profile"), "python");
  const explicitClientSelection = Boolean(optionString(options, "--clients")) || options.has("--all");
  const clients = installed
    ? explicitClientSelection
      ? parseClients(optionString(options, "--clients"), options.has("--all"), installedClients(target))
      : installedClients(target)
    : parseClients(optionString(options, "--clients"), options.has("--all"), ALL_CLIENTS);
  const canonical = installed
    ? upgradePlan(target, projectName, profile, true)
    : { actions: planTemplateWrites(target, projectName, profile), errors: [] };
  const adapters = syncClients(target, clients, {
    dryRun: true,
    assumeInitialized: !installed,
    forceGenerated: !installed,
    pruneGenerated: installed ? false : true,
  });
  const trust = installed ? trustPreviewActions(target) : [];
  return {
    actions: [...canonical.actions, ...adapters.actions, ...trust],
    errors: [...canonical.errors, ...adapters.errors],
  };
}

async function checkCommand(target: string, args: ParsedArgs): Promise<number> {
  const selectedChecks = await parseCheckSelection(args);
  const report = runChecks(target, selectedChecks);
  printCheckReport(report, { asJson: args.options.has("--json") });
  return report.ok ? 0 : 1;
}

async function statusCommand(target: string, args: ParsedArgs): Promise<number> {
  if (args.options.has("--json")) {
    printStatus(collectStatus(target), { asJson: true });
    return 0;
  }
  const drift = previewActions(target, new Map());
  printInspectionPlan(target, drift.actions, canPrompt());
  if (hasDiffDetails(drift.actions) && canPrompt() && (await promptViewDiffKey())) {
    previewCommand(target, { options: new Map() });
  }
  if (drift.errors.length > 0) {
    printErrorPanel("Status blocked", drift.errors);
    return 3;
  }
  return 0;
}

async function syncCommand(target: string, args: ParsedArgs): Promise<number> {
  const clients = await parseSyncClients(args);
  const result = syncClients(target, clients, {
    dryRun: args.options.has("--dry-run"),
    forceGenerated: args.options.has("--force-generated"),
    pruneGenerated: true,
  });
  printWritePlan(result.actions);
  if (result.errors.length > 0) {
    printErrorPanel("Sync blocked", result.errors);
    return 3;
  }
  printActionResult({
    title: "Agent Feed",
    message: "Sync complete",
    kind: "success",
  });
  return 0;
}

function previewCommand(target: string, args: ParsedArgs): number {
  const result = previewActions(target, args.options);
  printWritePlan(result.actions, { showDiffs: true });
  if (result.errors.length > 0) {
    printErrorPanel("Preview blocked", result.errors);
    return 3;
  }
  return 0;
}

async function promptWriteDiffDetails(actions: WriteAction[], command: string, target: string): Promise<void> {
  if (!hasDiffDetails(actions)) {
    return;
  }
  const interactive = canPrompt();
  printDiffHint({
    command: `${command} ${target}`,
    interactive,
  });
  if (interactive && (await promptViewDiffKey())) {
    printDiffDetails(actions);
  }
}

async function upgradeCommand(target: string, args: ParsedArgs): Promise<number> {
  const dryRun = args.options.has("--dry-run");
  const noInput = isNoInput(args.options);
  let currentTarget = target;
  let projectName = optionString(args.options, "--project-name") ?? inferProjectName(target);
  let clients = parseClients(
    optionString(args.options, "--clients"),
    args.options.has("--all"),
    installedClients(target),
  );

  if (canPrompt() && !args.path && !noInput) {
    printWelcome();
    const wizard = await promptUpgradeWizard({
      target: currentTarget,
      projectName,
      clients,
      clientsExplicit: Boolean(optionString(args.options, "--clients")) || args.options.has("--all"),
      projectNameExplicit: Boolean(optionString(args.options, "--project-name")),
    });
    if (!wizard) {
      printInfo("agent-feed: upgrade canceled");
      return 0;
    }
    currentTarget = wizard.target;
    projectName = wizard.projectName;
    clients = wizard.clients;
  }

  const envReady = await ensureTrustHomeForUpgrade(currentTarget, { noInput });
  if (!envReady.ok) {
    printErrorPanel("Environment setup blocked", envReady.errors);
    return 3;
  }

  const profile = inferProfile(currentTarget);
  const canonical = upgradePlan(currentTarget, projectName, profile, dryRun);
  const adapters = syncClients(currentTarget, clients, {
    dryRun,
    forceGenerated: true,
    pruneGenerated: false,
  });
  const trust = syncAssetTrust(currentTarget, {
    dryRun,
    acceptChanged: true,
    projectName,
    pruneMissing: true,
  });
  const actions = [...canonical.actions, ...adapters.actions, ...trust.actions];
  printWritePlan(actions);
  await promptWriteDiffDetails(actions, "agent-feed preview", currentTarget);
  if (canonical.errors.length > 0 || adapters.errors.length > 0 || trust.errors.length > 0) {
    printErrorPanel("Upgrade blocked", [...canonical.errors, ...adapters.errors, ...trust.errors]);
    return 3;
  }
  printActionResult({
    title: "Agent Feed",
    message: dryRun ? "Upgrade preview complete" : "Upgrade complete",
    kind: "success",
  });
  return 0;
}

async function uninstallCommand(target: string, args: ParsedArgs): Promise<number> {
  const dryRun = args.options.has("--dry-run");
  let yes = args.options.has("-y") || args.options.has("--yes");
  const actions = uninstallPlan(target, dryRun);
  if (actions.length === 0) {
    printInfo("agent-feed: no Agent Feed assets found");
    return 0;
  }
  printWritePlan(actions);
  if (!uninstallHasDeletions(actions)) {
    printInfo("agent-feed: no managed files are safe to delete");
    return 0;
  }
  if (dryRun) {
    printNextStep("Rerun with `agent-feed uninstall -y` to apply the uninstall plan listed above.");
    return 0;
  }
  if (!yes && canPrompt() && !args.options.has("--no-input")) {
    yes = await promptConfirm("Apply the uninstall plan shown above?", false);
  }
  if (!yes) {
    printErrorPanel("Uninstall blocked", [
      "pass `-y` to apply the uninstall plan listed above",
      "pass `--dry-run` to preview removals without deleting files",
    ]);
    return 3;
  }
  const applied = applyUninstallPlan(target, actions);
  printWritePlan(applied);
  printActionResult({
    title: "Agent Feed",
    message: "Uninstall complete",
    kind: "success",
  });
  return 0;
}

async function configCommand(args: string[]): Promise<number> {
  const [subcommand = "get", ...rest] = args;
  const parsed = parseArgs(rest);
  const target = parsePath(optionString(parsed.options, "--path") ?? parsed.path);
  if (subcommand === "get") {
    const asJson = parsed.options.has("--json");
    const result = getConfigValue(target, parsed.path);
    if (result.errors.length > 0) {
      printErrorPanel("Config read blocked", result.errors);
      return 3;
    }
    console.log(asJson || typeof result.value !== "string" ? JSON.stringify(result.value, null, 2) : result.value);
    return 0;
  }
  if (subcommand === "check") {
    const asJson = parsed.options.has("--json");
    const report = checkConfig(target);
    printConfigCheckReport(report, { asJson });
    return report.ok ? 0 : 1;
  }
  if (subcommand === "prune") {
    const dryRun = parsed.options.has("--dry-run");
    let yes = parsed.options.has("-y") || parsed.options.has("--yes");
    if (!dryRun && !yes) {
      const preview = pruneConfig(true);
      if (preview.errors.length > 0) {
        printErrorPanel("Config prune blocked", preview.errors);
        return 3;
      }
      if (preview.actions.length === 0) {
        printInfo("No stale project entries found.");
        return 0;
      }
      printWritePlan(preview.actions);
      if (canPrompt() && !parsed.options.has("--no-input")) {
        yes = await promptConfirm("Remove the stale project records shown above?", false);
      }
      if (!yes) {
        printErrorPanel("Config prune blocked", ["pass `-y` to remove stale project records"]);
        return 3;
      }
    }
    const result = pruneConfig(dryRun);
    if (result.errors.length > 0) {
      printErrorPanel("Config prune blocked", result.errors);
      return 3;
    }
    if (result.actions.length === 0) {
      printInfo("No stale project entries found.");
      return 0;
    }
    printWritePlan(result.actions);
    if (!dryRun) {
      printActionResult({
        title: "Agent Feed",
        message: "Stale project entries removed",
        kind: "success",
      });
    }
    return 0;
  }
  if (subcommand === "set") {
    const positional = positionalArgs(rest, new Set(["--path"]));
    const [key, value] = positional;
    if (!key || value === undefined) {
      printErrorPanel("Config update blocked", ["config set requires <key> and <value>"]);
      return 3;
    }
    const dryRun = parsed.options.has("--dry-run");
    if (!dryRun) {
      const preflight = configPreflightErrors(target);
      if (preflight.length > 0) {
        printErrorPanel("Config update blocked", preflight);
        return 3;
      }
    }
    const write = setConfigValue(target, key, value, dryRun);
    const effects = dryRun ? { actions: [] as WriteAction[], errors: [] as string[] } : applyConfigEffects(target, false);
    printWritePlan([...write.actions, ...effects.actions], { showDiffs: true });
    if (write.errors.length > 0 || effects.errors.length > 0) {
      printErrorPanel("Config update blocked", [...write.errors, ...effects.errors]);
      return 3;
    }
    if (!dryRun) {
      const report = checkConfig(target);
      if (report.errors.length > 0) {
        printConfigCheckReport(report);
        return 3;
      }
      if (report.warnings.length > 0) {
        printConfigCheckReport(report);
      }
      printActionResult({
        title: "Agent Feed",
        message: "Config updated",
        kind: "success",
      });
    }
    return 0;
  }
  printCommandHelp("config");
  return 1;
}

async function envCommand(args: string[]): Promise<number> {
  const [subcommand = "status", ...rest] = args;
  const parsed = parseArgs(rest);
  if (subcommand === "status") {
    const target = parsePath(parsed.path);
    const status = getEnvStatus(target);
    printActionResult({
      title: "Agent Feed Environment",
      message: status.errors.length === 0 && status.configured ? "Environment is ready" : "Environment needs setup",
      kind: status.errors.length === 0 && status.configured ? "success" : "warning",
      detail: `${TRUST_ENV}: ${status.home ?? "<not set>"}\nRecommended: ${status.recommendation}${status.configFile ? `\nConfig: ${status.configFile}` : ""}`,
    });
    if (status.errors.length > 0) {
      printErrorPanel("Environment diagnostics", status.errors);
      return 1;
    }
    return 0;
  }
  if (subcommand === "print") {
    const shell = resolveShell(optionString(parsed.options, "--shell"));
    if (!shell.shell) {
      printErrorPanel("Environment print blocked", [shell.error ?? "unsupported shell"]);
      return 3;
    }
    const home = parsePath(optionString(parsed.options, "--home") ?? suggestedAgentFeedHome());
    console.log(shellExportText(home, shell.shell));
    return 0;
  }
  if (subcommand === "setup") {
    const dryRun = parsed.options.has("--dry-run");
    let result = setupAgentFeedHome({
      home: optionString(parsed.options, "--home"),
      target: parsePath(parsed.path),
      shell: optionString(parsed.options, "--shell"),
      dryRun,
      force: parsed.options.has("--force"),
    });
    if (
      result.errors.some((error) => error.includes("pass --force")) &&
      canPrompt() &&
      !parsed.options.has("--force") &&
      !parsed.options.has("--no-input")
    ) {
      const confirmed = await promptConfirm(
        `${TRUST_ENV} already points to another path. Replace it with ${result.home}?`,
        false,
      );
      if (confirmed) {
        result = setupAgentFeedHome({
          home: optionString(parsed.options, "--home"),
          target: parsePath(parsed.path),
          shell: optionString(parsed.options, "--shell"),
          dryRun,
          force: true,
        });
      }
    }
    printWritePlan(result.actions);
    if (result.errors.length > 0) {
      printErrorPanel("Environment setup blocked", result.errors);
      return 3;
    }
    printActionResult({
      title: "Agent Feed Environment",
      message: dryRun ? "Environment setup preview complete" : "Environment configured",
      kind: "success",
      detail: `${TRUST_ENV}: ${result.home}`,
    });
    return 0;
  }
  if (subcommand === "uninstall") {
    const dryRun = parsed.options.has("--dry-run");
    let yes = parsed.options.has("-y") || parsed.options.has("--yes");
    const plan = envUninstallPlan({
      home: optionString(parsed.options, "--home"),
      shell: optionString(parsed.options, "--shell"),
      dryRun,
      removeHome: parsed.options.has("--remove-home"),
    });
    printWritePlan(plan.actions);
    if (plan.errors.length > 0) {
      printErrorPanel("Environment uninstall blocked", plan.errors);
      return 3;
    }
    if (!hasDeletions(plan.actions)) {
      printInfo("No Agent Feed environment changes were found.");
      return 0;
    }
    if (dryRun) {
      printNextStep("Rerun with `-y` to apply the environment uninstall plan.");
      return 0;
    }
    if (!yes && canPrompt() && !parsed.options.has("--no-input")) {
      yes = await promptConfirm("Apply the environment uninstall plan shown above?", false);
    }
    if (!yes) {
      printErrorPanel("Environment uninstall blocked", ["confirmation is required; pass `-y` to apply the cleanup plan"]);
      return 3;
    }
    const applied = applyEnvUninstallPlan(plan.actions, {
      shell: optionString(parsed.options, "--shell"),
    });
    printWritePlan(applied);
    printActionResult({
      title: "Agent Feed Environment",
      message: "Environment uninstall complete",
      kind: "success",
    });
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

async function resolveInitProfile(
  raw: string | undefined,
  options: { noInput: boolean },
): Promise<VerificationProfile | undefined> {
  if (raw && raw.trim()) {
    return parseProfile(raw, "python");
  }
  if (options.noInput) {
    printErrorPanel("Init blocked", [
      "choose a project verification profile explicitly before init writes files",
      "run: `agent-feed init --profile <python,node,custom,none>`",
    ]);
    return undefined;
  }
  if (canPrompt()) {
    return promptVerificationProfile("Select project verification profile", "python");
  }
  return "python";
}

async function ensureTrustHomeForInit(
  target: string,
  options: { envHome?: string; dryRun: boolean; noInput: boolean },
): Promise<{ ok: boolean; actions: WriteAction[]; errors: string[] }> {
  const config = trustConfigPath();
  if (config.errors.length === 0) {
    return { ok: true, actions: [], errors: [] };
  }
  const missingEnv = config.errors.some((error) => error.includes(`${TRUST_ENV} is required`));
  if (!missingEnv) {
    return { ok: true, actions: [], errors: [] };
  }

  const recommended = options.envHome ?? suggestedAgentFeedHome(target);
  if (!options.envHome && !options.dryRun && (options.noInput || !canPrompt())) {
    return {
      ok: false,
      actions: [],
      errors: [
        `${TRUST_ENV} is required before init can record AI asset trust.`,
        `Run: \`agent-feed env setup ${target}\``,
        "Or rerun init with `--env-home PATH`.",
      ],
    };
  }

  if (!options.envHome && !options.dryRun && canPrompt() && !options.noInput) {
    printActionResult({
      title: "Agent Feed Environment",
      message: `${TRUST_ENV} is not configured yet`,
      kind: "warning",
      detail: `Agent Feed stores trusted AI asset hashes outside the repository.\nRecommended home: ${recommended}`,
    });
    const confirmed = await promptConfirm(`Configure ${TRUST_ENV} at ${recommended} now?`, true);
    if (!confirmed) {
      return {
        ok: false,
        actions: [],
        errors: [
          `${TRUST_ENV} is required before init can continue.`,
          `Run: \`agent-feed env setup ${target}\``,
        ],
      };
    }
  }

  let result = setupAgentFeedHome({
    home: recommended,
    target,
    dryRun: options.dryRun,
    force: false,
  });

  if (
    result.errors.some((error) => error.includes("pass --force")) &&
    canPrompt() &&
    !options.noInput
  ) {
    const confirmed = await promptConfirm(
      `${TRUST_ENV} already points to another path. Replace it with ${result.home}?`,
      false,
    );
    if (confirmed) {
      result = setupAgentFeedHome({
        home: recommended,
        target,
        dryRun: options.dryRun,
        force: true,
      });
    }
  }

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
            `Run: \`agent-feed env setup ${target}${options.envHome ? ` --home ${recommended}` : ""}\``,
            "If shell detection failed, add `--shell zsh`, `bash`, `fish`, or `powershell`.",
          ],
  };
}

async function ensureTrustHomeForUpgrade(
  target: string,
  options: { noInput: boolean },
): Promise<{ ok: boolean; actions: WriteAction[]; errors: string[] }> {
  const config = trustConfigPath();
  if (config.errors.length === 0) {
    return { ok: true, actions: [], errors: [] };
  }
  const missingEnv = config.errors.some((error) => error.includes(`${TRUST_ENV} is required`));
  if (!missingEnv || options.noInput || !canPrompt()) {
    return { ok: true, actions: [], errors: [] };
  }

  const recommended = suggestedAgentFeedHome(target);
  printActionResult({
    title: "Environment Setup Required",
    message: "Agent Feed needs an external user config home",
    kind: "warning",
    detail: `Recommended: ${recommended}`,
  });
  const confirmed = await promptConfirm(`Set up ${TRUST_ENV} now and continue?`, true);
  if (!confirmed) {
    return { ok: true, actions: [], errors: [] };
  }
  let result = setupAgentFeedHome({
    home: recommended,
    target,
    dryRun: false,
    force: false,
  });
  if (result.errors.some((error) => error.includes("pass --force"))) {
    const replace = await promptConfirm(
      `${TRUST_ENV} already points to another path. Replace it with ${result.home}?`,
      false,
    );
    if (replace) {
      result = setupAgentFeedHome({
        home: recommended,
        target,
        dryRun: false,
        force: true,
      });
    }
  }
  if (result.actions.length > 0) {
    printWritePlan(result.actions);
  }
  if (result.errors.length > 0) {
    return {
      ok: false,
      actions: result.actions,
      errors: [
        ...result.errors,
        `Run: \`agent-feed env setup ${target}\``,
        "If shell detection failed, add `--shell zsh`, `bash`, `fish`, or `powershell`.",
      ],
    };
  }
  printActionResult({
    title: "Environment Setup",
    message: "Environment configured",
    kind: "success",
    detail: "The user-level Agent Feed home and shell binding are ready for this session.",
  });
  return { ok: true, actions: result.actions, errors: [] };
}

function indexSkillsCommand(target: string, args: ParsedArgs): number {
  const dryRun = args.options.has("--dry-run");
  const acceptChanged = args.options.has("-y") || args.options.has("--yes");
  const preflight = configPreflightErrors(target);
  if (preflight.length > 0) {
    printErrorPanel("Skill indexing blocked", preflight);
    return 3;
  }
  const actions = indexSkillMetadata(target, dryRun);
  const trust = syncAssetTrust(target, {
    dryRun,
    acceptChanged,
    projectName: inferProjectName(target),
    pruneMissing: true,
  });
  printWritePlan([...actions.actions, ...trust.actions], { showDiffs: true });
  if (actions.errors.length > 0 || trust.errors.length > 0) {
    printErrorPanel("Skill indexing blocked", [...actions.errors, ...trust.errors]);
    return 3;
  }
  printActionResult({
    title: "Agent Feed",
    message: dryRun ? "Skill index preview complete" : "Skills indexed",
    kind: "success",
  });
  return 0;
}

async function skillHubCommand(target: string, args: ParsedArgs): Promise<number> {
  const keywordOption = optionString(args.options, "--keyword")?.trim();
  let keyword = keywordOption;
  const dryRun = args.options.has("--dry-run");
  const noInput = args.options.has("--no-input");
  const saveToken = !args.options.has("--no-save-token");
  const interactive = canPrompt() && !noInput;
  const keywordFromPrompt = !keyword && interactive;
  if (!keyword && !interactive) {
    printErrorPanel("Skill hub search blocked", ["pass `--keyword` before searching curated skill hubs"]);
    return 3;
  }
  if (!existsSync(join(target, ".agents", "skills"))) {
    printErrorPanel("Skill hub install blocked", ["missing `.agents/skills`; run `agent-feed init` before installing skills"]);
    return 3;
  }
  const tokenState = preferredGithubToken(target);
  let activeToken = tokenState.token;
  for (const warning of tokenState.warnings) {
    printWarning(warning);
  }

  let selected: RemoteSkill[] | undefined;
  let skills: RemoteSkill[];
  while (true) {
    if (!keyword) {
      const value = await promptSkillKeyword();
      if (value === undefined || !value.trim()) {
        printActionResult({
          title: "Skill Hub",
          message: "Canceled",
          kind: "warning",
          detail: "No skills were installed.",
        });
        return 0;
      }
      keyword = value.trim();
    }

    try {
      skills = await runWithSpinner("Searching curated skill hubs", () =>
        searchRemoteSkills(keyword!, { token: activeToken }),
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const retry = await retrySkillHubWithToken({
        keyword,
        error: message,
        noInput,
        saveToken,
        target,
      });
      if (!retry) {
        printErrorPanel("Skill hub search blocked", [skillHubFailureHelp(message)]);
        return 3;
      }
      if (retry === "blocked") {
        return 3;
      }
      skills = retry.skills;
      activeToken = retry.token;
    }
    if (skills.length === 0) {
      printActionResult({
        title: "Skill Hub",
        message: "No curated skills matched that keyword",
        kind: "warning",
        detail: "Try another keyword or check the curated hubs below.",
      });
      printInfo("Hubs searched:");
      for (const hub of CURATED_HUBS) {
        printInfo(`- ${hub.name}: ${hub.url}`);
      }
      if (keywordFromPrompt) {
        keyword = undefined;
        printInfo("Try another keyword, or press Esc to cancel.");
        continue;
      }
      return 0;
    }

    selected = noInput
      ? skills
      : await promptSkillSelection(skills, {
          onPreview: async (skill) => {
            try {
              const remotePackage = await runWithSpinner(`Loading preview for ${skill.name}`, () =>
                fetchRemoteSkill(skill, { token: activeToken }),
              );
              printSkillPreview(remotePackage);
            } catch (error) {
              printErrorPanel("Skill preview blocked", [
                skillHubFailureHelp(error instanceof Error ? error.message : String(error)),
              ]);
            }
          },
        });
    if (selected === undefined) {
      if (keywordFromPrompt) {
        keyword = undefined;
        printInfo("Returned to keyword search.");
        continue;
      }
      printActionResult({
        title: "Skill Hub",
        message: "Canceled",
        kind: "warning",
        detail: "No skills were installed.",
      });
      return 0;
    }
    break;
  }

  if (selected.length === 0) {
    printErrorPanel("Skill hub install blocked", ["select at least one skill"]);
    return 3;
  }

  const actions: WriteAction[] = [];
  const errors: string[] = [];
  for (const skill of selected) {
    try {
      const remotePackage = await runWithSpinner(`Fetching ${skill.name}`, () =>
        fetchRemoteSkill(skill, { token: activeToken }),
      );
      if (dryRun) {
        printInfo(previewSkillTree(remotePackage));
      }
      const installed = installRemoteSkillPackage(target, remotePackage, dryRun);
      actions.push(...installed.actions);
      errors.push(...installed.errors);
    } catch (error) {
      errors.push(error instanceof Error ? error.message : String(error));
    }
  }
  printWritePlan(actions);
  if (errors.length > 0) {
    printErrorPanel("Skill hub install blocked", errors);
    return 3;
  }
  if (dryRun) {
    printNextStep(`Run \`agent-feed skill-hub ${target} --keyword ${keyword} --no-input\` to install the selected skills.`);
    return 0;
  }
  const indexed = indexSkillMetadata(target, false);
  const trust = syncAssetTrust(target, {
    dryRun: false,
    acceptChanged: true,
    projectName: inferProjectName(target),
    pruneMissing: true,
  });
  printWritePlan([...indexed.actions, ...trust.actions], { showDiffs: true });
  if (indexed.errors.length > 0 || trust.errors.length > 0) {
    printErrorPanel("Skill indexing blocked", [...indexed.errors, ...trust.errors]);
    return 3;
  }
  printActionResult({
    title: "Agent Feed",
    message: "Selected skills installed",
    kind: "success",
  });
  return 0;
}

async function runWithSpinner<T>(text: string, fn: () => Promise<T>): Promise<T> {
  if (!canPrompt()) {
    return fn();
  }
  const spinner = ora({ text, color: "cyan" }).start();
  try {
    const result = await fn();
    spinner.succeed(text);
    return result;
  } catch (error) {
    spinner.fail(text);
    throw error;
  }
}

function printSkillPreview(remotePackage: RemoteSkillPackage): void {
  printPanel(
    "Skill Preview",
    [
      `Source: ${remotePackage.skill.hub.name}  ${remotePackage.skill.hub.url}`,
      `Skill:  ${remotePackage.skill.name}  ${remotePackage.skill.url}`,
      "",
      "Files to add:",
      "",
      previewSkillTree(remotePackage),
      "",
      "Imported skills are installed as `trust: custom`. Agent Feed does not execute remote scripts during install.",
    ].join("\n"),
    { kind: "warning" },
  );
}

async function retrySkillHubWithToken(options: {
  keyword: string;
  error: string;
  noInput: boolean;
  saveToken: boolean;
  target: string;
}): Promise<{ skills: RemoteSkill[]; token: string } | "blocked" | undefined> {
  if (options.noInput || !canPrompt() || !skillHubErrorCanUseToken(options.error)) {
    return undefined;
  }
  printActionResult({
    title: "Skill Hub",
    message: "GitHub did not allow the anonymous skill-hub request",
    kind: "warning",
    detail: skillHubFailureHelp(options.error),
  });
  const token = await promptSecret("GitHub token");
  if (!token) {
    return undefined;
  }
  if (options.saveToken) {
    const saved = saveGithubToken(token, options.target);
    if (saved.actions.length > 0) {
      printWritePlan(saved.actions);
    }
    if (saved.errors.length > 0) {
      printErrorPanel("GitHub token not saved", saved.errors);
      printInfo("Continuing with the token for this command only.");
    }
  }
  try {
    const skills = await runWithSpinner("Searching curated skill hubs", () =>
      searchRemoteSkills(options.keyword, { token }),
    );
    return { skills, token };
  } catch (error) {
    printErrorPanel("Skill hub search blocked", [
      skillHubFailureHelp(error instanceof Error ? error.message : String(error)),
    ]);
    return "blocked";
  }
}

function skillHubErrorCanUseToken(error: string): boolean {
  const lowered = error.toLowerCase();
  return ["rate limit", "http 401", "http 403", "token"].some((needle) => lowered.includes(needle));
}

async function main(argv: string[]): Promise<number> {
  const [first, ...rest] = argv;
  let { command, rest: commandRest } = normalizeCommandAlias(first, [...rest]);

  if (!command) {
    if (canPrompt()) {
      printWelcome();
      command = await promptMainAction();
      if (command === "env") {
        commandRest = ["setup"];
      }
    } else {
      printHelp();
      return 0;
    }
  }

  if (command === "--help" || command === "-h") {
    printHelp();
    return 0;
  }
  if (command === "--version" || command === "-v" || command === "version") {
    printVersion();
    return 0;
  }

  try {
    if (commandRest.includes("--help") || commandRest.includes("-h")) {
      printCommandHelp(command);
      return command in {
        init: true,
        sync: true,
        preview: true,
        upgrade: true,
        uninstall: true,
        check: true,
        status: true,
        config: true,
        env: true,
        "index-skills": true,
        "skill-hub": true,
      }
        ? 0
        : 1;
    }
    const parsed = parseArgs(commandRest);
    const target = parsePath(parsed.path);
    if (command === "config") {
      return await configCommand(commandRest);
    }
    if (command === "env") {
      return await envCommand(commandRest);
    }
    if (command === "index-skills") {
      return indexSkillsCommand(target, parsed);
    }
    if (command === "skill-hub") {
      return await skillHubCommand(target, parsed);
    }
    if (command === "init") {
      return await initCommand(target, parsed);
    }
    if (command === "sync") {
      return await syncCommand(target, parsed);
    }
    if (command === "preview") {
      return previewCommand(target, parsed);
    }
    if (command === "upgrade") {
      return await upgradeCommand(target, parsed);
    }
    if (command === "uninstall") {
      return uninstallCommand(target, parsed);
    }
    if (command === "check") {
      return await checkCommand(target, parsed);
    }
    if (command === "status") {
      return await statusCommand(target, parsed);
    }
    printHelp();
    return 1;
  } catch (error) {
    if (isPromptCanceled(error)) {
      printInfo("agent-feed: canceled");
      return 0;
    }
    printErrorPanel("Agent Feed", [error instanceof Error ? error.message : String(error)]);
    if (command === "env" || command === "init") {
      printRecommendedCommand("Need environment setup?", "agent-feed env setup");
    }
    return 3;
  }
}

process.exit(await main(process.argv.slice(2)));
