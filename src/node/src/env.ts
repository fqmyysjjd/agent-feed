import { spawnSync } from "node:child_process";
import { cpSync, existsSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { homedir, platform } from "node:os";
import { dirname, join, resolve } from "node:path";

import { type WriteAction } from "./template.js";
import {
  CONFIG_FILE,
  TRUST_ENV,
  defaultTrustConfig,
  legacyConfigPath,
  readExistingOrLegacyConfig,
  recommendedHome,
  writeUserConfig,
} from "./trust.js";

const SHELL_AUTO = "auto";
const SUPPORTED_SHELLS = new Set(["zsh", "bash", "fish", "powershell"]);
const MANAGED_START = "# >>> agent-feed env >>>";
const MANAGED_END = "# <<< agent-feed env <<<";

export type EnvStatus = {
  configured: boolean;
  home?: string;
  configFile?: string;
  errors: string[];
  recommendation: string;
};

export type EnvSetupOptions = {
  home?: string;
  target?: string;
  shell?: string;
  dryRun: boolean;
  force: boolean;
};

export type EnvSetupResult = {
  home: string;
  configFile: string;
  shell: string;
  actions: WriteAction[];
  errors: string[];
};

export type EnvUninstallOptions = {
  home?: string;
  shell?: string;
  dryRun: boolean;
  removeHome: boolean;
};

export function currentAgentFeedHome(): string | undefined {
  const raw = (process.env[TRUST_ENV] ?? "").trim();
  return raw ? resolve(raw) : undefined;
}

export function suggestedAgentFeedHome(target?: string): string {
  const candidate = recommendedHome();
  if (!target) {
    return candidate;
  }
  const resolvedTarget = resolve(target);
  const resolvedCandidate = resolve(candidate);
  return isInside(resolvedCandidate, resolvedTarget) ? join(homedir(), ".agent-feed") : resolvedCandidate;
}

export function getEnvStatus(target?: string): EnvStatus {
  const recommendation = suggestedAgentFeedHome(target);
  const home = currentAgentFeedHome();
  if (!home) {
    return {
      configured: false,
      errors: [`${TRUST_ENV} is not set`],
      recommendation,
    };
  }

  const errors: string[] = [];
  const resolvedTarget = target ? resolve(target) : undefined;
  if (resolvedTarget && isInside(home, resolvedTarget)) {
    errors.push(`${TRUST_ENV} points inside the current project (${resolvedTarget})`);
  }
  if (!existsSync(home)) {
    errors.push(`${home} does not exist`);
  } else if (!statSync(home).isDirectory()) {
    errors.push(`${home} is not a directory`);
  }
  const configFile = join(home, CONFIG_FILE);
  if (existsSync(configFile) || existsSync(legacyConfigPath(configFile))) {
    errors.push(...validateEnvConfigShape(configFile));
  } else {
    errors.push(`${configFile} does not exist`);
  }
  return {
    configured: true,
    home,
    configFile,
    errors,
    recommendation,
  };
}

export function shellExportText(home: string, shell: string): string {
  if (shell === "fish") {
    return `set -gx ${TRUST_ENV} "${home}"`;
  }
  if (shell === "powershell") {
    return `[Environment]::SetEnvironmentVariable('${TRUST_ENV}', '${home}', 'User')`;
  }
  return `export ${TRUST_ENV}="${home}"`;
}

export function resolveShell(shell: string = SHELL_AUTO): { shell?: string; error?: string } {
  const candidate = shell.trim().toLowerCase();
  if (candidate !== SHELL_AUTO) {
    return SUPPORTED_SHELLS.has(candidate)
      ? { shell: candidate }
      : { error: `unsupported shell: ${shell}` };
  }
  if (platform() === "win32") {
    return { shell: "powershell" };
  }
  const raw = process.env.SHELL ?? "";
  const detected = raw.split("/").filter(Boolean).at(-1) ?? "";
  if (SUPPORTED_SHELLS.has(detected)) {
    return { shell: detected };
  }
  return { error: "could not detect shell; pass --shell zsh, bash, fish, or powershell" };
}

export function setupAgentFeedHome(options: EnvSetupOptions): EnvSetupResult {
  const target = options.target ? resolve(options.target) : undefined;
  const home = resolve(options.home ?? suggestedAgentFeedHome(target));
  const configFile = join(home, CONFIG_FILE);
  const shell = resolveShell(options.shell);
  if (!shell.shell) {
    return {
      home,
      configFile,
      shell: options.shell ?? SHELL_AUTO,
      actions: [],
      errors: [shell.error ?? "unsupported shell"],
    };
  }

  const errors = homeBoundaryErrors(home, target);
  const currentHome = currentAgentFeedHome();
  if (currentHome && currentHome !== home && !options.force) {
    errors.push(`${TRUST_ENV} is already set to ${currentHome}; pass --force to replace it`);
  }
  if (existsSync(configFile) || existsSync(legacyConfigPath(configFile))) {
    errors.push(...validateEnvConfigShape(configFile));
  }
  if (errors.length > 0) {
    return { home, configFile, shell: shell.shell, actions: [], errors };
  }

  const actions: WriteAction[] = [];
  const configAction = ensureConfigFile(configFile, options.dryRun);
  if (configAction) {
    actions.push(configAction);
  }

  if (shell.shell === "powershell" && platform() === "win32") {
    if (!options.dryRun) {
      const error = setWindowsUserEnv(home);
      if (error) {
        return { home, configFile, shell: shell.shell, actions, errors: [error] };
      }
    }
    actions.push({
      path: "HKCU/Environment/AGENT_FEED_HOME",
      action: options.dryRun ? "would update" : "update",
      detail: `set user environment variable to ${home}`,
    });
  } else if (shell.shell === "powershell") {
    actions.push({
      path: "PowerShell user environment",
      action: "skip",
      detail: shellExportText(home, shell.shell),
    });
  } else {
    const shellPath = shellConfigPath(shell.shell);
    if (!shellPath) {
      return {
        home,
        configFile,
        shell: shell.shell,
        actions,
        errors: [`unsupported shell: ${shell.shell}`],
      };
    }
    const shellAction = updateShellConfig(shellPath, managedEnvBlock(home, shell.shell), options.dryRun);
    if (shellAction) {
      actions.push(shellAction);
    }
  }

  if (!options.dryRun) {
    process.env[TRUST_ENV] = home;
  }

  return { home, configFile, shell: shell.shell, actions, errors: [] };
}

export function envUninstallPlan(options: EnvUninstallOptions): { actions: WriteAction[]; errors: string[] } {
  const shell = resolveShell(options.shell);
  const home = resolve(options.home ?? currentAgentFeedHome() ?? suggestedAgentFeedHome());
  if (!shell.shell) {
    return { actions: [], errors: [shell.error ?? "unsupported shell"] };
  }

  const actions: WriteAction[] = [];
  if (shell.shell === "powershell" && platform() === "win32") {
    actions.push({
      path: "HKCU/Environment/AGENT_FEED_HOME",
      action: options.dryRun ? "would update" : "update",
      detail: "remove user environment variable",
    });
  } else if (shell.shell === "powershell") {
    actions.push({
      path: "PowerShell user environment",
      action: "skip",
      detail: "run env print or remove AGENT_FEED_HOME manually on this platform",
    });
  } else {
    const shellPath = shellConfigPath(shell.shell);
    if (!shellPath) {
      return { actions: [], errors: [`unsupported shell: ${shell.shell}`] };
    }
    const shellAction = removeShellConfigBlock(shellPath, options.dryRun);
    if (shellAction) {
      actions.push(shellAction);
    }
  }

  if (options.removeHome) {
    if (existsSync(home)) {
      if (isAgentFeedHome(home)) {
        actions.push({
          path: home,
          action: options.dryRun ? "would delete" : "delete",
          detail: "Agent Feed user-level home",
        });
      } else {
        actions.push({
          path: home,
          action: "skip",
          detail: "not removed because this path does not look like an Agent Feed home",
        });
      }
    } else {
      actions.push({
        path: home,
        action: "skip",
        detail: "Agent Feed user-level home already absent",
      });
    }
  }
  return { actions, errors: [] };
}

export function applyEnvUninstallPlan(
  actions: WriteAction[],
  options: { shell?: string },
): WriteAction[] {
  const resolved = resolveShell(options.shell);
  const applied: WriteAction[] = [];
  for (const action of actions) {
    if (action.path === "HKCU/Environment/AGENT_FEED_HOME") {
      const error = removeWindowsUserEnv();
      if (error) {
        applied.push({
          path: action.path,
          action: "blocked",
          detail: error,
        });
        continue;
      }
      applied.push({
        path: action.path,
        action: "updated",
        detail: action.detail,
      });
      continue;
    }
    if (action.action === "delete" && existsSync(action.path)) {
      rmSync(action.path, { recursive: true, force: true });
      applied.push({ ...action, action: "deleted" });
      continue;
    }
    if (action.action === "update" && resolved.shell && resolved.shell !== "powershell" && existsSync(action.path)) {
      const current = readFileSync(action.path, "utf8");
      const next = removeManagedBlock(current);
      if (current === next) {
        applied.push({ path: action.path, action: "skip", detail: "shell config is current" });
      } else {
        const backup = backupFile(action.path);
        cpSync(action.path, backup);
        writeFileSync(action.path, next, "utf8");
        applied.push({
          path: action.path,
          action: "updated",
          detail: `removed ${TRUST_ENV}; backup: ${backup}`,
        });
      }
      continue;
    }
    if (action.action === "skip") {
      applied.push(action);
    }
  }
  if (resolved.shell === "powershell" && platform() === "win32") {
    delete process.env[TRUST_ENV];
  }
  return applied;
}

export function hasDeletions(actions: WriteAction[]): boolean {
  return actions.some((action) =>
    action.action.includes("update") || action.action.includes("delete"),
  );
}

function shellConfigPath(shell: string): string | undefined {
  const home = homedir();
  if (shell === "zsh") {
    const zdotdir = (process.env.ZDOTDIR ?? "").trim();
    return join(zdotdir ? resolve(zdotdir) : home, ".zshrc");
  }
  if (shell === "bash") {
    return join(home, ".bashrc");
  }
  if (shell === "fish") {
    return join(home, ".config", "fish", "config.fish");
  }
  return undefined;
}

function managedEnvBlock(home: string, shell: string): string {
  return `${MANAGED_START}\n${shellExportText(home, shell)}\n${MANAGED_END}\n`;
}

function homeBoundaryErrors(home: string, target?: string): string[] {
  if (!target) {
    return [];
  }
  return isInside(home, target) ? [`${TRUST_ENV} home points inside the current project (${target})`] : [];
}

function ensureConfigFile(configFile: string, dryRun: boolean): WriteAction | undefined {
  const legacyFile = legacyConfigPath(configFile);
  if (existsSync(configFile) || existsSync(legacyFile)) {
    const loaded = readExistingOrLegacyConfig(configFile);
    if (loaded.errors.length > 0) {
      return {
        path: configFile,
        action: "blocked",
        detail: "external Agent Feed config is invalid",
      };
    }
    if (loaded.usedLegacy) {
      if (!dryRun) {
        writeUserConfig(configFile, loaded.state);
      }
      return {
        path: configFile,
        action: dryRun ? "would update" : "update",
        detail: "migrate external Agent Feed config to config.json",
      };
    }
    return { path: configFile, action: "skip", detail: "external Agent Feed config exists" };
  }
  if (!dryRun) {
    writeUserConfig(configFile, defaultTrustConfig());
  }
  return { path: configFile, action: dryRun ? "would create" : "create", detail: "external Agent Feed config" };
}

function validateEnvConfigShape(configFile: string): string[] {
  const loaded = readExistingOrLegacyConfig(configFile);
  if (loaded.errors.length > 0) {
    return loaded.errors;
  }
  const settings = loaded.state.settings;
  if (settings !== undefined && (!settings || typeof settings !== "object" || Array.isArray(settings))) {
    return [`${configFile} settings must be a JSON object`];
  }
  if (settings && typeof settings === "object" && !Array.isArray(settings)) {
    const token = (settings as Record<string, unknown>).github_token;
    if (token !== undefined && typeof token !== "string") {
      return [`${configFile} settings.github_token must be a string when present`];
    }
  }
  const projects = loaded.state.projects;
  if (!projects || typeof projects !== "object" || Array.isArray(projects)) {
    return [`${configFile} projects must be a JSON object`];
  }
  return [];
}

function updateShellConfig(path: string, block: string, dryRun: boolean): WriteAction | undefined {
  const existed = existsSync(path);
  const current = existed ? readFileSync(path, "utf8") : "";
  const next = replaceOrAppendBlock(current, block);
  if (current === next) {
    return { path, action: "skip", detail: "shell config is current" };
  }
  if (!dryRun) {
    let detail = `set ${TRUST_ENV}`;
    if (existed) {
      const backup = backupFile(path);
      cpSync(path, backup);
      detail = `set ${TRUST_ENV}; backup: ${backup}`;
    }
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, next, "utf8");
    return { path, action: existed ? "update" : "create", detail };
  }
  return { path, action: existed ? "would update" : "would create", detail: `set ${TRUST_ENV}` };
}

function replaceOrAppendBlock(current: string, block: string): string {
  const start = current.indexOf(MANAGED_START);
  const endMarker = current.indexOf(MANAGED_END);
  if (start !== -1 && endMarker !== -1 && endMarker > start) {
    const end = endMarker + MANAGED_END.length;
    let suffix = current.slice(end);
    if (suffix.startsWith("\n")) {
      suffix = suffix.slice(1);
    }
    const prefix = current.slice(0, start).trimEnd();
    const pieces = [prefix, block.trimEnd(), suffix.trimStart()].filter(Boolean);
    return `${pieces.join("\n\n")}\n`;
  }
  const separator = current && !current.endsWith("\n\n") ? "\n\n" : "";
  return `${current}${separator}${block}`;
}

function removeShellConfigBlock(path: string, dryRun: boolean): WriteAction | undefined {
  if (!existsSync(path)) {
    return { path, action: "skip", detail: "shell config is absent" };
  }
  const current = readFileSync(path, "utf8");
  const next = removeManagedBlock(current);
  if (current === next) {
    return { path, action: "skip", detail: "agent-feed env block is absent" };
  }
  return {
    path,
    action: dryRun ? "would update" : "update",
    detail: `remove ${TRUST_ENV} managed block`,
  };
}

function removeManagedBlock(current: string): string {
  const start = current.indexOf(MANAGED_START);
  const endMarker = current.indexOf(MANAGED_END);
  if (start === -1 || endMarker === -1 || endMarker <= start) {
    return current;
  }
  const end = endMarker + MANAGED_END.length;
  let suffix = current.slice(end);
  if (suffix.startsWith("\n")) {
    suffix = suffix.slice(1);
  }
  const prefix = current.slice(0, start).trimEnd();
  const pieces = [prefix, suffix.trimStart()].filter(Boolean);
  return pieces.length > 0 ? `${pieces.join("\n\n")}\n` : "";
}

function backupFile(path: string): string {
  const stamp = new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 14);
  return `${path}.bak-agent-feed-${stamp}`;
}

function isAgentFeedHome(path: string): boolean {
  if (!existsSync(path) || !statSync(path).isDirectory()) {
    return false;
  }
  const configFile = join(path, CONFIG_FILE);
  const legacyFile = legacyConfigPath(configFile);
  if (!existsSync(configFile) && !existsSync(legacyFile)) {
    return false;
  }
  return validateEnvConfigShape(configFile).length === 0;
}

function isInside(candidate: string, root: string): boolean {
  const resolvedCandidate = resolve(candidate);
  const resolvedRoot = resolve(root);
  return (
    resolvedCandidate === resolvedRoot ||
    resolvedCandidate.startsWith(`${resolvedRoot}/`) ||
    resolvedCandidate.startsWith(`${resolvedRoot}\\`)
  );
}

function setWindowsUserEnv(home: string): string | undefined {
  return runPowerShellEnvCommand(
    `[Environment]::SetEnvironmentVariable('${powerShellSingleQuoted(TRUST_ENV)}', '${powerShellSingleQuoted(home)}', 'User')`,
  );
}

function removeWindowsUserEnv(): string | undefined {
  return runPowerShellEnvCommand(
    `[Environment]::SetEnvironmentVariable('${powerShellSingleQuoted(TRUST_ENV)}', $null, 'User')`,
  );
}

function runPowerShellEnvCommand(command: string): string | undefined {
  if (platform() !== "win32") {
    return undefined;
  }
  const result = spawnSync("powershell.exe", ["-NoProfile", "-Command", command], {
    encoding: "utf8",
  });
  if (result.status === 0) {
    return undefined;
  }
  const stderr = result.stderr.trim();
  const stdout = result.stdout.trim();
  return `failed to update Windows user environment: ${stderr || stdout || result.error?.message || "unknown error"}`;
}

function powerShellSingleQuoted(value: string): string {
  return value.replaceAll("'", "''");
}
