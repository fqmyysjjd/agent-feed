import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { installedClients, syncClients } from "./adapters.js";
import { indexSkillMetadata } from "./skill-index.js";
import {
  inferProfile,
  inferProjectName,
  isInstalled,
  parseProfile,
  readMetadata,
  renderMetadata,
  renderSessionSchema,
  type WriteAction,
  unifiedDiff,
} from "./template.js";
import {
  cleanupMissingProjectEntries,
  missingProjectEntries,
  projectLocalConfigErrors,
  syncAssetTrust,
  trustConfigPath,
  trustPreflightErrors,
  validateUserConfigShape,
} from "./trust.js";

const METADATA_PATH = ".agents/agent-feed.json";

export type ConfigCheckReport = {
  errors: string[];
  warnings: string[];
};

export function getConfigValue(root: string, key?: string): { value: unknown; errors: string[] } {
  const read = readConfig(root);
  if (read.errors.length > 0) {
    return { value: undefined, errors: read.errors };
  }
  if (!key || !key.trim()) {
    return { value: read.data, errors: [] };
  }
  let current: unknown = read.data;
  for (const part of normalizeConfigKey(key)) {
    if (!current || typeof current !== "object" || Array.isArray(current) || !(part in current)) {
      return { value: undefined, errors: [`${METADATA_PATH} has no config key ${JSON.stringify(key)}`] };
    }
    current = (current as Record<string, unknown>)[part];
  }
  return { value: current, errors: [] };
}

export function setConfigValue(
  root: string,
  key: string,
  rawValue: string,
  dryRun: boolean,
): { actions: WriteAction[]; errors: string[] } {
  const read = readConfig(root);
  if (read.errors.length > 0) {
    return { actions: [], errors: read.errors };
  }
  const path = normalizeConfigKey(key);
  const mutable = validateMutableKey(path);
  if (mutable.length > 0) {
    return { actions: [], errors: mutable };
  }
  const value = parseConfigValue(rawValue);
  const valueErrors = validateConfigValue(path, value);
  if (valueErrors.length > 0) {
    return { actions: [], errors: valueErrors };
  }
  const next = JSON.parse(JSON.stringify(read.data)) as Record<string, unknown>;
  assignPath(next, path, value);
  const shape = validateConfigData(next);
  if (shape.length > 0) {
    return { actions: [], errors: shape };
  }
  const file = join(root, METADATA_PATH);
  const current = readFileSync(file, "utf8");
  const expected = `${JSON.stringify(next, null, 2)}\n`;
  if (current === expected) {
    return { actions: [{ path: file, action: "skip", detail: "config is current" }], errors: [] };
  }
  const action = dryRun ? "would update" : "update";
  const diff = unifiedDiff(METADATA_PATH, current, expected);
  if (!dryRun) {
    writeFileSync(file, expected, "utf8");
  }
  return { actions: [{ path: file, action, diff }], errors: [] };
}

export function applyConfigEffects(root: string, dryRun: boolean): { actions: WriteAction[]; errors: string[] } {
  if (!isInstalled(root)) {
    return { actions: [], errors: ["missing Agent Feed installation; run agent-feed init first"] };
  }
  const projectName = inferProjectName(root);
  const profile = inferProfile(root);
  const actions: WriteAction[] = [];
  const errors: string[] = [];

  const metadataFile = join(root, METADATA_PATH);
  const metadataCurrent = readFileSync(metadataFile, "utf8");
  const metadataExpected = renderMetadata(root, projectName, profile);
  if (metadataCurrent !== metadataExpected) {
    actions.push({
      path: metadataFile,
      action: dryRun ? "would update" : "update",
      diff: unifiedDiff(METADATA_PATH, metadataCurrent, metadataExpected),
    });
    if (!dryRun) {
      writeFileSync(metadataFile, metadataExpected, "utf8");
    }
  }

  const schemaFile = join(root, ".agents", "session-state", "schema.json");
  const schemaCurrent = existsSync(schemaFile) ? readFileSync(schemaFile, "utf8") : "";
  const schemaExpected = renderSessionSchema(root);
  if (schemaCurrent !== schemaExpected) {
    actions.push({
      path: schemaFile,
      action: dryRun ? `would ${existsSync(schemaFile) ? "update" : "create"}` : existsSync(schemaFile) ? "update" : "create",
      diff: existsSync(schemaFile) ? unifiedDiff(".agents/session-state/schema.json", schemaCurrent, schemaExpected) : "",
    });
    if (!dryRun) {
      writeFileSync(schemaFile, schemaExpected, "utf8");
    }
  }

  const skills = indexSkillMetadata(root, dryRun);
  actions.push(...skills.actions);
  errors.push(...skills.errors);

  const adapters = syncClients(root, installedClients(root), dryRun);
  actions.push(...adapters.actions);
  errors.push(...adapters.errors);

  const trust = syncAssetTrust(root, {
    dryRun,
    acceptChanged: true,
    projectName,
    pruneMissing: true,
  });
  actions.push(...trust.actions);
  errors.push(...trust.errors);
  return { actions, errors };
}

export function checkConfig(root: string): ConfigCheckReport {
  const errors: string[] = [];
  const warnings: string[] = [];
  const read = readConfig(root);
  if (read.errors.length > 0) {
    errors.push(...read.errors);
  } else {
    errors.push(...validateConfigData(read.data));
  }
  const config = trustConfigPath();
  if (config.errors.length > 0) {
    errors.push(...config.errors);
  } else if (config.path) {
    errors.push(...projectLocalConfigErrors(root, config.path));
    if (existsSync(config.path) || existsSync(config.path.replace(/config\.json$/, "agent-feed.json"))) {
      errors.push(...validateUserConfigShape(config.path));
    } else {
      errors.push(`missing user-level Agent Feed config: ${config.path}. Run agent-feed env setup.`);
    }
  }
  const stale = missingProjectEntries();
  errors.push(...stale.errors);
  if (stale.configPath) {
    for (const staleRoot of stale.roots) {
      warnings.push(`${stale.configPath}: stale project entry points to missing directory ${staleRoot}`);
    }
  }
  return { errors, warnings };
}

export function pruneConfig(dryRun: boolean): { actions: WriteAction[]; errors: string[] } {
  return cleanupMissingProjectEntries(dryRun);
}

export function configPreflightErrors(root: string): string[] {
  return trustPreflightErrors(root);
}

function readConfig(root: string): { data: Record<string, unknown>; errors: string[] } {
  if (!isInstalled(root)) {
    return { data: {}, errors: ["missing Agent Feed installation; run agent-feed init first"] };
  }
  const file = join(root, METADATA_PATH);
  if (!existsSync(file)) {
    return { data: {}, errors: [`missing ${METADATA_PATH}; run agent-feed upgrade first`] };
  }
  const data = readMetadata(root);
  if (!data || Object.keys(data).length === 0) {
    return { data: {}, errors: [`${METADATA_PATH} must be a JSON object`] };
  }
  return { data, errors: [] };
}

function normalizeConfigKey(key: string): string[] {
  const parts = key
    .trim()
    .split(".")
    .map((part) => part.trim())
    .filter(Boolean);
  return parts[0] === "setting" ? ["settings", ...parts.slice(1)] : parts;
}

function validateMutableKey(path: string[]): string[] {
  if (path.length === 0) {
    return ["config key is required"];
  }
  if ((path[0] === "project_name" || path[0] === "verification_profile") && path.length === 1) {
    return [];
  }
  if (path[0] === "settings" && path.length >= 2) {
    return [];
  }
  return ["config set supports project_name, verification_profile, and settings.* keys only"];
}

function parseConfigValue(raw: string): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    return raw.trim();
  }
}

function assignPath(data: Record<string, unknown>, path: string[], value: unknown): void {
  let current = data;
  for (const part of path.slice(0, -1)) {
    const existing = current[part];
    if (!existing || typeof existing !== "object" || Array.isArray(existing)) {
      current[part] = {};
    }
    current = current[part] as Record<string, unknown>;
  }
  current[path.at(-1) ?? ""] = value;
}

function validateConfigValue(path: string[], value: unknown): string[] {
  const dotted = path.join(".");
  if (dotted === "project_name") {
    return typeof value === "string" && value.trim() ? [] : ["project_name must be a non-empty string"];
  }
  if (dotted === "verification_profile") {
    try {
      parseProfile(typeof value === "string" ? value : undefined, "python");
      return [];
    } catch {
      return ["verification_profile must be one of python, node, custom, none"];
    }
  }
  return [];
}

export function validateConfigData(data: Record<string, unknown>): string[] {
  const errors = validateMetadataData(data);
  errors.push(...settingsErrors(data, METADATA_PATH));
  return errors;
}

function validateMetadataData(data: Record<string, unknown>): string[] {
  const errors: string[] = [];
  for (const key of [
    "schema_version",
    "agent_feed_version",
    "template",
    "project_name",
    "verification_profile",
  ]) {
    if (!(key in data)) {
      errors.push(`${METADATA_PATH} missing ${key}`);
    }
  }
  if (data.schema_version !== 1) {
    errors.push(`${METADATA_PATH} schema_version must be 1`);
  }
  if (data.template !== "standard") {
    errors.push(`${METADATA_PATH} template must be standard`);
  }
  if (
    typeof data.verification_profile === "string" &&
    !["python", "node", "custom", "none"].includes(data.verification_profile)
  ) {
    errors.push(`${METADATA_PATH} verification_profile must be one of python, node, custom, none`);
  }
  if (typeof data.project_name !== "string" || !data.project_name.trim()) {
    errors.push(`${METADATA_PATH} project_name must be a non-empty string`);
  }
  return errors;
}

function settingsErrors(data: Record<string, unknown>, label: string): string[] {
  const settings = data.settings;
  if (settings === undefined || settings === null) {
    return [];
  }
  if (typeof settings !== "object" || Array.isArray(settings)) {
    return [`${label} settings must be a JSON object`];
  }
  const errors: string[] = [];
  const raw = settings as Record<string, unknown>;
  const session = raw.session_state;
  if (session !== undefined) {
    if (!session || typeof session !== "object" || Array.isArray(session)) {
      errors.push(`${label} settings.session_state must be a JSON object`);
    } else {
      const maxCarry = (session as Record<string, unknown>).max_carry_forwards;
      if (maxCarry !== undefined && (!Number.isInteger(maxCarry) || Number(maxCarry) < 1)) {
        errors.push(`${label} settings.session_state.max_carry_forwards must be a positive integer`);
      }
    }
  }
  const skills = raw.skills;
  if (skills !== undefined) {
    if (!skills || typeof skills !== "object" || Array.isArray(skills)) {
      errors.push(`${label} settings.skills must be a JSON object`);
    } else {
      const skillSettings = skills as Record<string, unknown>;
      const source = skillSettings.default_import_source;
      if (source !== undefined && (typeof source !== "string" || !source.trim())) {
        errors.push(`${label} settings.skills.default_import_source must be a non-empty string`);
      }
      const trust = skillSettings.default_import_trust;
      if (trust !== undefined && trust !== "reviewed" && trust !== "custom") {
        errors.push(`${label} settings.skills.default_import_trust must be one of custom, reviewed`);
      }
    }
  }
  const claude = raw.claude;
  if (claude !== undefined) {
    if (!claude || typeof claude !== "object" || Array.isArray(claude)) {
      errors.push(`${label} settings.claude must be a JSON object`);
    } else {
      const snippets = (claude as Record<string, unknown>).required_snippets;
      if (
        snippets !== undefined &&
        (!Array.isArray(snippets) || snippets.length === 0 || !snippets.every((item) => typeof item === "string" && item))
      ) {
        errors.push(`${label} settings.claude.required_snippets must contain non-empty strings`);
      }
    }
  }
  return errors;
}
