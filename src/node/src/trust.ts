import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { chmodSync, existsSync, mkdirSync, readFileSync, statSync, unlinkSync, writeFileSync } from "node:fs";
import { homedir, platform } from "node:os";
import { dirname, join, relative, resolve } from "node:path";

import { readFrontmatter } from "./skill-index.js";
import { TEMPLATE_ROOT, type WriteAction, unifiedDiff, walkFiles } from "./template.js";
import { VERSION } from "./version.js";

export const TRUST_ENV = "AGENT_FEED_HOME";
export const CONFIG_FILE = "config.json";
export const LEGACY_CONFIG_FILE = "agent-feed.json";
const MANAGED_SCRIPT_PATHS = [
  ".agents/scripts/check-agent-assets.sh",
  ".agents/scripts/check-agent-trust.sh",
  ".agents/scripts/index-skills.sh",
  ".agents/scripts/sync-agent-assets.sh",
  ".agents/scripts/verify-agent-dev.sh",
];

export type TrustState = Record<string, unknown>;

type TrustAsset = {
  kind: string;
  name: string;
  path: string;
  source: string;
  trust: string;
  sha256: string;
};

export function trustConfigPath(): { path?: string; errors: string[] } {
  const raw = (process.env[TRUST_ENV] ?? "").trim();
  if (!raw) {
    return { errors: [agentFeedHomeRequiredMessage()] };
  }
  return { path: join(resolve(raw), CONFIG_FILE), errors: [] };
}

export function agentFeedHomeRequiredMessage(): string {
  return `${TRUST_ENV} is required before Agent Feed can verify trusted AI assets. Run agent-feed env setup, or set ${TRUST_ENV} to a user-level directory such as ${recommendedHome()}.`;
}

export function recommendedHome(): string {
  if (platform() === "win32" && process.env.APPDATA) {
    return join(process.env.APPDATA, "agent-feed");
  }
  return join(homedir(), ".agent-feed");
}

export function trustPreflightErrors(root: string): string[] {
  const config = trustConfigPath();
  if (config.errors.length > 0) {
    return config.errors;
  }
  if (!config.path) {
    return [];
  }
  const local = projectLocalConfigErrors(root, config.path);
  if (local.length > 0) {
    return local;
  }
  const legacy = legacyConfigPath(config.path);
  if (!existsSync(config.path) && !existsSync(legacy)) {
    return [];
  }
  return validateUserConfigShape(config.path);
}

export function projectLocalConfigErrors(root: string, configPath: string): string[] {
  const rootPath = resolve(root);
  const config = resolve(configPath);
  if (config === rootPath || config.startsWith(`${rootPath}/`) || config.startsWith(`${rootPath}\\`)) {
    return [
      `${TRUST_ENV} points inside the current project (${rootPath}). Use an external Agent Feed home so trusted AI asset hashes are not stored in the repository.`,
    ];
  }
  return [];
}

export function validateUserConfigShape(configPath: string): string[] {
  const loaded = readExistingOrLegacyConfig(configPath);
  if (loaded.errors.length > 0) {
    return loaded.errors;
  }
  const state = loaded.state;
  const settings = state.settings;
  if (settings !== undefined && (!settings || typeof settings !== "object" || Array.isArray(settings))) {
    return [`${configPath} settings must be a JSON object`];
  }
  if (settings && typeof settings === "object" && !Array.isArray(settings)) {
    const token = (settings as Record<string, unknown>).github_token;
    if (token !== undefined && typeof token !== "string") {
      return [`${configPath} settings.github_token must be a string when present`];
    }
  }
  const projects = state.projects;
  if (!projects || typeof projects !== "object" || Array.isArray(projects)) {
    return [`${configPath} projects must be a JSON object`];
  }
  return [];
}

export function missingProjectEntries(): { configPath?: string; roots: string[]; errors: string[] } {
  const config = trustConfigPath();
  if (config.errors.length > 0 || !config.path) {
    return { roots: [], errors: [] };
  }
  const loaded = readExistingOrLegacyConfig(config.path);
  if (loaded.errors.length > 0) {
    return { configPath: config.path, roots: [], errors: loaded.errors };
  }
  const projects = loaded.state.projects;
  if (!projects || typeof projects !== "object" || Array.isArray(projects)) {
    return { configPath: config.path, roots: [], errors: [`${config.path} projects must be a JSON object`] };
  }
  const roots = Object.entries(projects)
    .filter(([key, value]) => typeof key === "string" && value && typeof value === "object" && !existsSync(key))
    .map(([key]) => key)
    .sort();
  return { configPath: config.path, roots, errors: [] };
}

export function cleanupMissingProjectEntries(dryRun: boolean): { actions: WriteAction[]; errors: string[] } {
  const stale = missingProjectEntries();
  if (stale.errors.length > 0) {
    return { actions: [], errors: stale.errors };
  }
  if (!stale.configPath || stale.roots.length === 0) {
    return { actions: [], errors: [] };
  }
  const detail = `remove ${stale.roots.length} stale project ${stale.roots.length === 1 ? "entry" : "entries"}`;
  if (dryRun) {
    return { actions: [{ path: stale.configPath, action: "would update", detail }], errors: [] };
  }
  const loaded = readExistingOrLegacyConfig(stale.configPath);
  if (loaded.errors.length > 0) {
    return { actions: [], errors: loaded.errors };
  }
  const projects = loaded.state.projects as Record<string, unknown>;
  for (const root of stale.roots) {
    delete projects[root];
  }
  loaded.state.schema_version = 1;
  loaded.state.agent_feed_version = VERSION;
  writeUserConfig(stale.configPath, loaded.state);
  return { actions: [{ path: stale.configPath, action: "update", detail }], errors: [] };
}

export function syncAssetTrust(
  root: string,
  options: { dryRun: boolean; acceptChanged: boolean; pruneMissing?: boolean; projectName?: string },
): { actions: WriteAction[]; errors: string[] } {
  const config = trustConfigPath();
  if (config.errors.length > 0 || !config.path) {
    return { actions: [], errors: config.errors };
  }
  const local = projectLocalConfigErrors(root, config.path);
  if (local.length > 0) {
    return { actions: [], errors: local };
  }
  const loaded = readExistingOrLegacyConfig(config.path);
  if (loaded.errors.length > 0) {
    return { actions: [], errors: loaded.errors };
  }
  const state = loaded.state;
  if (!state.projects || typeof state.projects !== "object" || Array.isArray(state.projects)) {
    state.projects = {};
  }
  const projects = state.projects as Record<string, unknown>;
  const key = resolve(root);
  let project = projects[key];
  if (!project || typeof project !== "object" || Array.isArray(project)) {
    project = { project_root: key, project_name: options.projectName ?? key.split(/[\\/]/).at(-1), assets: {} };
    projects[key] = project;
  }
  const projectRecord = project as Record<string, unknown>;
  projectRecord.project_root = key;
  if (options.projectName) {
    projectRecord.project_name = options.projectName;
  }
  projectRecord.agent_feed_version = VERSION;
  if (!projectRecord.assets || typeof projectRecord.assets !== "object" || Array.isArray(projectRecord.assets)) {
    projectRecord.assets = {};
  }
  const entries = projectRecord.assets as Record<string, unknown>;

  let changed = !existsSync(config.path) || loaded.usedLegacy;
  const currentPaths = new Set<string>();
  const errors: string[] = [];
  for (const asset of currentAssets(root)) {
    currentPaths.add(asset.path);
    let entry = entries[asset.path];
    if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
      entries[asset.path] = assetEntry(asset);
      changed = true;
      continue;
    }
    const record = entry as Record<string, unknown>;
    const allowed = record.allowed_sha256;
    if (!Array.isArray(allowed)) {
      return { actions: [], errors: [`${config.path} entry ${asset.path} allowed_sha256 must be a list`] };
    }
    if (!allowed.includes(asset.sha256)) {
      if (!options.acceptChanged) {
        errors.push(`${asset.path}: trusted hash changed. Inspect with agent-feed preview before accepting.`);
        continue;
      }
      allowed.push(asset.sha256);
      changed = true;
    }
    for (const [keyName, value] of Object.entries(assetEntry(asset))) {
      if (keyName === "allowed_sha256") {
        continue;
      }
      if (record[keyName] !== value) {
        record[keyName] = value;
        changed = true;
      }
    }
  }
  if (options.pruneMissing !== false) {
    for (const relPath of Object.keys(entries)) {
      if (!currentPaths.has(relPath)) {
        delete entries[relPath];
        changed = true;
      }
    }
  }
  state.schema_version = 1;
  state.agent_feed_version = VERSION;
  if (errors.length > 0) {
    return { actions: [], errors };
  }
  if (!changed && existsSync(config.path)) {
    return { actions: [{ path: config.path, action: "skip", detail: "external trust is current" }], errors: [] };
  }
  const action = existsSync(config.path) ? "update" : "create";
  if (options.dryRun) {
    return {
      actions: [{ path: config.path, action: `would ${action}`, detail: "external Agent Feed trust config" }],
      errors: [],
    };
  }
  writeUserConfig(config.path, state);
  return {
    actions: [{ path: config.path, action, detail: "recorded trusted AI asset hashes outside the project" }],
    errors: [],
  };
}

export function assetTrustErrors(root: string, kinds?: Set<string>): string[] {
  const report = checkAssetTrust(root, kinds);
  if (report.errors.length > 0) {
    return report.errors;
  }
  if (report.missingState) {
    return [
      `missing external Agent Feed trust state for ${root}; expected ${report.configPath ?? TRUST_ENV}. Review current AI assets, then run: agent-feed index-skills -y`,
    ];
  }
  return report.issues.map(
    (issue) =>
      `${issue.path}: ${issue.reason}. Highest-priority Agent Feed rule requires stopping before this asset is used. Inspect with agent-feed preview; if intentional, accept with agent-feed index-skills -y.`,
  );
}

export function trustPreviewActions(root: string): WriteAction[] {
  const report = checkAssetTrust(root);
  if (report.errors.length > 0) {
    return report.errors.map((error) => ({
      path: root,
      action: "blocked",
      detail: error,
    }));
  }
  if (report.missingState) {
    return [
      {
        path: report.configPath ?? root,
        action: "review",
        detail: "missing external trust state; run agent-feed index-skills -y after review",
      },
    ];
  }
  return report.issues.map((issue) => ({
    path: join(root, issue.path),
    action: "review",
    detail: "Agent Feed asset changed; highest-priority rule requires stopping",
    diff: assetDiff(root, issue.path) || `${issue.path}: current content does not match trusted Agent Feed state.`,
  }));
}

export function checkAssetTrust(
  root: string,
  kinds?: Set<string>,
): { configPath?: string; missingState: boolean; issues: Array<{ path: string; reason: string }>; errors: string[] } {
  const config = trustConfigPath();
  if (config.errors.length > 0 || !config.path) {
    return { configPath: config.path, missingState: false, issues: [], errors: config.errors };
  }
  const local = projectLocalConfigErrors(root, config.path);
  if (local.length > 0) {
    return { configPath: config.path, missingState: false, issues: [], errors: local };
  }
  const legacy = legacyConfigPath(config.path);
  if (!existsSync(config.path) && !existsSync(legacy)) {
    return { configPath: config.path, missingState: true, issues: [], errors: [] };
  }
  const shape = validateUserConfigShape(config.path);
  if (shape.length > 0) {
    return { configPath: config.path, missingState: false, issues: [], errors: shape };
  }
  const loaded = readExistingOrLegacyConfig(config.path);
  if (loaded.errors.length > 0) {
    return { configPath: config.path, missingState: false, issues: [], errors: loaded.errors };
  }
  const projects = loaded.state.projects as Record<string, unknown>;
  const project = projects[resolve(root)];
  if (!project || typeof project !== "object" || Array.isArray(project)) {
    return { configPath: config.path, missingState: true, issues: [], errors: [] };
  }
  const assets = (project as Record<string, unknown>).assets;
  if (!assets || typeof assets !== "object" || Array.isArray(assets)) {
    return { configPath: config.path, missingState: false, issues: [], errors: [`${config.path} project entry assets must be a JSON object`] };
  }
  const entries = assets as Record<string, unknown>;
  const issues: Array<{ path: string; reason: string }> = [];
  for (const asset of currentAssets(root)) {
    if (kinds && !kinds.has(asset.kind)) {
      continue;
    }
    const entry = entries[asset.path];
    if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
      issues.push({ path: asset.path, reason: "missing trust entry" });
      continue;
    }
    const allowed = (entry as Record<string, unknown>).allowed_sha256;
    if (!Array.isArray(allowed) || !allowed.includes(asset.sha256)) {
      issues.push({ path: asset.path, reason: "trusted hash mismatch" });
    }
  }
  return { configPath: config.path, missingState: false, issues, errors: [] };
}

function assetDiff(root: string, relPath: string): string {
  const gitDiff = gitCommand(root, ["diff", "--", relPath]);
  if (gitDiff) {
    return gitDiff;
  }
  const stagedDiff = gitCommand(root, ["diff", "--cached", "--", relPath]);
  if (stagedDiff) {
    return stagedDiff;
  }

  const currentFile = join(root, relPath);
  const templateFile = join(TEMPLATE_ROOT, relPath);
  if (existsSync(currentFile) && existsSync(templateFile)) {
    return unifiedDiff(
      relPath,
      readFileSync(currentFile, "utf8"),
      readFileSync(templateFile, "utf8"),
    );
  }
  return "";
}

function gitCommand(root: string, args: string[]): string {
  try {
    return execFileSync("git", ["-C", root, ...args], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return "";
  }
}

export function readExistingOrLegacyConfig(configPath: string): { state: TrustState; errors: string[]; usedLegacy: boolean } {
  const legacy = legacyConfigPath(configPath);
  if (existsSync(configPath)) {
    return readTrustConfig(configPath, false);
  }
  if (existsSync(legacy)) {
    return readTrustConfig(legacy, true);
  }
  return { state: defaultTrustConfig(), errors: [], usedLegacy: false };
}

function readTrustConfig(path: string, usedLegacy: boolean): { state: TrustState; errors: string[]; usedLegacy: boolean } {
  try {
    const parsed = JSON.parse(readFileSync(path, "utf8")) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return { state: defaultTrustConfig(), errors: [`${path} must be a JSON object`], usedLegacy };
    }
    return { state: parsed as TrustState, errors: [], usedLegacy };
  } catch (error) {
    return { state: defaultTrustConfig(), errors: [`${path} invalid JSON: ${String(error)}`], usedLegacy };
  }
}

export function writeUserConfig(path: string, state: TrustState): void {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, `${JSON.stringify(state, null, 2)}\n`, "utf8");
  const legacy = legacyConfigPath(path);
  if (legacy !== path && existsSync(legacy)) {
    unlinkSync(legacy);
  }
  if (platform() !== "win32") {
    chmodSync(path, 0o600);
  }
}

export function legacyConfigPath(path: string): string {
  return join(dirname(path), LEGACY_CONFIG_FILE);
}

export function defaultTrustConfig(): TrustState {
  return {
    schema_version: 1,
    agent_feed_version: VERSION,
    settings: {
      github_token: "",
    },
    projects: {},
  };
}

function currentAssets(root: string): TrustAsset[] {
  const assets: TrustAsset[] = [];
  const skillRoot = join(root, ".agents", "skills");
  if (existsSync(skillRoot)) {
    for (const skillFile of walkFiles(skillRoot).filter((path) => path.endsWith(`${join("", "SKILL.md")}`))) {
      const relPath = toPosix(relative(root, skillFile));
      const frontmatter = readFrontmatter(readFileSync(skillFile, "utf8"));
      assets.push({
        kind: "skill",
        name: frontmatter.name ?? skillFile.split(/[\\/]/).at(-2) ?? "skill",
        path: relPath,
        source: frontmatter.source ?? "unknow",
        trust: frontmatter.trust ?? "custom",
        sha256: sha256File(skillFile),
      });
    }
  }
  for (const relPath of MANAGED_SCRIPT_PATHS) {
    const path = join(root, relPath);
    if (existsSync(path) && statSync(path).isFile()) {
      assets.push({
        kind: "script",
        name: relPath.split("/").at(-1)?.replace(/\.sh$/, "") ?? relPath,
        path: relPath,
        source: "agent-feed",
        trust: "core",
        sha256: sha256File(path),
      });
    }
  }
  return assets;
}

function assetEntry(asset: TrustAsset): Record<string, unknown> {
  return {
    kind: asset.kind,
    name: asset.name,
    source: asset.source,
    trust: asset.trust,
    allowed_sha256: [asset.sha256],
  };
}

function sha256File(path: string): string {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function toPosix(path: string): string {
  return path.replaceAll("\\", "/");
}
