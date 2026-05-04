import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";

import { checkClaude, checkCodex, checkCursor, installedClients } from "./adapters.js";
import { checkConfig, validateConfigData } from "./config.js";
import { readFrontmatter, skillIndexErrors } from "./skill-index.js";
import { assetTrustErrors } from "./trust.js";

export const ALL_CHECKS = [
  "structure",
  "config",
  "skills",
  "references",
  "session",
  "scripts",
  "codex",
  "claude",
  "cursor",
] as const;

export type CheckName = (typeof ALL_CHECKS)[number];

export type CheckReport = {
  target: string;
  checks: CheckName[];
  ok: boolean;
  errors: string[];
  warnings: string[];
};

export type ProjectStatus = {
  target: string;
  canonical_installed: boolean;
  codex_ready: boolean;
  claude_ready: boolean;
  cursor_ready: boolean;
  legacy_codex_mirror: boolean;
  errors: string[];
  warnings: string[];
};

const REQUIRED_PATHS = [
  "AGENTS.md",
  ".agents/agent-feed.json",
  ".agents/README.md",
  ".agents/rules/outcome-boundary.md",
  ".agents/rules/decision-gates.md",
  ".agents/rules/context-loading.md",
  ".agents/rules/session-state.md",
  ".agents/rules/testing-gates.md",
  ".agents/rules/development-workflow.md",
  ".agents/rules/review-gates.md",
  ".agents/project/README.md",
  ".agents/project/verification-commands.sh",
  ".agents/domain/README.md",
  ".agents/skills",
  ".agents/skills/README.md",
  ".agents/scripts/check-agent-assets.sh",
  ".agents/scripts/check-agent-trust.sh",
  ".agents/scripts/index-skills.sh",
  ".agents/scripts/sync-agent-assets.sh",
  ".agents/scripts/verify-agent-dev.sh",
] as const;

const SKILL_NAME_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const AGENTS_PATH_PATTERN = /\.agents\/[A-Za-z0-9_.*/<>-]+/g;
const SESSION_CARRY_FORWARD_TYPES = new Set(["decision", "constraint", "blocker", "handoff"]);
const SESSION_EXPIRY_PATTERN =
  /\b\d{4}-\d{2}-\d{2}(?:[T ][0-9]{2}:[0-9]{2}(?::[0-9]{2})?(?:Z|[+-][0-9]{2}:?[0-9]{2})?)?\b/;

export function parseChecks(raw: string | undefined, fallback: CheckName[]): CheckName[] {
  if (!raw || !raw.trim()) {
    return fallback;
  }
  const values = raw
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
  const allowed = new Set<string>(ALL_CHECKS);
  const unknown = [...new Set(values.filter((value) => value !== "all" && !allowed.has(value)))];
  if (unknown.length > 0) {
    throw new Error(`unknown checks: ${unknown.join(", ")}. Allowed values: ${[...ALL_CHECKS, "all"].join(", ")}.`);
  }
  if (values.includes("all")) {
    if (new Set(values).size > 1) {
      throw new Error("checks cannot combine all with other values");
    }
    return [...ALL_CHECKS];
  }
  return [...new Set(values)] as CheckName[];
}

export function runChecks(root: string, checks: CheckName[]): CheckReport {
  const errors: string[] = [];
  const warnings: string[] = [];
  for (const check of checks) {
    if (check === "structure") {
      errors.push(...validateStructure(root));
    } else if (check === "config") {
      const report = checkConfig(root);
      errors.push(...report.errors);
      warnings.push(...report.warnings);
    } else if (check === "skills") {
      const report = validateSkillsReport(root, true);
      errors.push(...report.errors);
      warnings.push(...report.warnings);
    } else if (check === "references") {
      errors.push(...validateReferencesAndIndexes(root));
    } else if (check === "session") {
      const report = validateSessionStateReport(root);
      errors.push(...report.errors);
      warnings.push(...report.warnings);
    } else if (check === "scripts") {
      errors.push(...validateScripts(root));
    } else {
      const report = checkConfiguredAdapter(root, check);
      errors.push(...report.errors);
      warnings.push(...report.warnings);
    }
  }
  return { target: root, checks, ok: errors.length === 0, errors, warnings };
}

export function collectStatus(root: string): ProjectStatus {
  const canonicalErrors = validateStructure(root);
  const trustErrors = assetTrustErrors(root);
  const skills = validateSkillsReport(root, false);
  const codex = checkConfiguredAdapter(root, "codex");
  const configured = new Set(installedClients(root));
  const claude = configured.has("claude") ? checkConfiguredAdapter(root, "claude") : emptyReport();
  const cursor = configured.has("cursor") ? checkConfiguredAdapter(root, "cursor") : emptyReport();
  return {
    target: root,
    canonical_installed: canonicalErrors.length === 0 && trustErrors.length === 0,
    codex_ready: codex.errors.length === 0,
    claude_ready: configured.has("claude") && claude.errors.length === 0,
    cursor_ready: configured.has("cursor") && cursor.errors.length === 0,
    legacy_codex_mirror: existsSync(join(root, ".codex", "skills")),
    errors: [
      ...canonicalErrors,
      ...trustErrors,
      ...skills.errors,
      ...codex.errors,
      ...claude.errors,
      ...cursor.errors,
    ],
    warnings: [
      ...skills.warnings,
      ...codex.warnings,
      ...claude.warnings,
      ...cursor.warnings,
    ],
  };
}

function validateStructure(root: string): string[] {
  const errors = REQUIRED_PATHS.filter((relPath) => !existsSync(join(root, relPath))).map(
    (relPath) => `missing required path: ${relPath}`,
  );
  errors.push(...validateMetadata(root));
  return errors;
}

function validateMetadata(root: string): string[] {
  const path = join(root, ".agents", "agent-feed.json");
  if (!existsSync(path)) {
    return [];
  }
  let data: unknown;
  try {
    data = JSON.parse(readFileSync(path, "utf8")) as unknown;
  } catch (error) {
    return [`.agents/agent-feed.json invalid JSON: ${String(error)}`];
  }
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    return [".agents/agent-feed.json must be a JSON object"];
  }
  return validateConfigData(data as Record<string, unknown>);
}

function validateScripts(root: string): string[] {
  const errors: string[] = [];
  for (const relPath of [
    ".agents/scripts/check-agent-assets.sh",
    ".agents/scripts/check-agent-trust.sh",
    ".agents/scripts/index-skills.sh",
    ".agents/scripts/sync-agent-assets.sh",
    ".agents/scripts/verify-agent-dev.sh",
  ]) {
    const path = join(root, relPath);
    if (!existsSync(path)) {
      errors.push(`missing script: ${relPath}`);
    } else if (process.platform !== "win32" && (statSync(path).mode & 0o111) === 0) {
      errors.push(`script is not executable: ${relPath}`);
    }
  }
  errors.push(...assetTrustErrors(root, new Set(["script"])));
  return errors;
}

function validateSkillsReport(
  root: string,
  includeTrust: boolean,
): { errors: string[]; warnings: string[] } {
  const errors: string[] = [];
  const warnings: string[] = [];
  const skillRoot = join(root, ".agents", "skills");
  if (!existsSync(skillRoot)) {
    return { errors: ["missing .agents/skills"], warnings };
  }
  for (const skillFile of skillFiles(root)) {
    const relPath = toPosix(relative(root, skillFile));
    const skillName = relPath.split("/").at(-2) ?? "skill";
    const frontmatter = readFrontmatter(readFileSync(skillFile, "utf8"));
    const frontmatterName = frontmatter.name ?? "";
    if (frontmatterName !== skillName) {
      errors.push(`${relPath}: frontmatter name must match directory name (${JSON.stringify(frontmatterName)} != ${JSON.stringify(skillName)})`);
    }
    if (!SKILL_NAME_PATTERN.test(skillName)) {
      errors.push(`${relPath}: skill name must be lowercase kebab-case`);
    }
    if (skillName.split("-").length > 3) {
      errors.push(`${relPath}: skill name must be at most three words`);
    }
    for (const key of ["description", "source", "trust"] as const) {
      if (!frontmatter[key]) {
        errors.push(`${relPath}: frontmatter missing ${key}`);
      }
    }
    if (frontmatter.trust && !["core", "reviewed", "custom"].includes(frontmatter.trust)) {
      errors.push(`${relPath}: trust must be one of core, reviewed, custom`);
    }
  }
  if (includeTrust) {
    errors.push(...assetTrustErrors(root, new Set(["skill"])));
  }
  errors.push(...skillIndexErrors(root));
  return { errors, warnings };
}

function validateReferencesAndIndexes(root: string): string[] {
  const errors: string[] = [];
  const skipParts = new Set([".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv", "build", "dist", "node_modules", "__pycache__"]);
  const optionalPaths = new Set([".agents/session-state/current.json"]);
  for (const markdownFile of walkMarkdownFiles(root)) {
    const relPath = toPosix(relative(root, markdownFile));
    if (relPath.split("/").some((part) => skipParts.has(part))) {
      continue;
    }
    const text = readFileSync(markdownFile, "utf8");
    for (const match of text.matchAll(AGENTS_PATH_PATTERN)) {
      const pathText = match[0].replace(/[.,):]+$/, "");
      if (/[<>*]/.test(pathText) || pathText.includes("{{") || pathText.includes("YYYYMMDD")) {
        continue;
      }
      if (optionalPaths.has(pathText)) {
        continue;
      }
      if (!existsSync(join(root, pathText))) {
        errors.push(`${relPath}: missing referenced path ${pathText}`);
      }
    }
  }

  const agentsReadme = join(root, ".agents", "README.md");
  if (existsSync(agentsReadme)) {
    const text = readFileSync(agentsReadme, "utf8");
    for (const ruleFile of childFiles(join(root, ".agents", "rules"), ".md")) {
      const name = ruleFile.split("/").at(-1) ?? "";
      if (name && !text.includes(name)) {
        errors.push(`.agents/README.md does not list rule ${name}`);
      }
    }
  }

  const projectReadme = join(root, ".agents", "project", "README.md");
  if (existsSync(projectReadme)) {
    const text = readFileSync(projectReadme, "utf8");
    for (const heading of ["## Boundary", "## Maintenance Contract", "## Current Project Constraints"]) {
      if (!text.includes(heading)) {
        errors.push(`.agents/project/README.md missing required heading ${heading}`);
      }
    }
    for (const projectFile of childFiles(join(root, ".agents", "project"), ".md")) {
      const name = projectFile.split("/").at(-1) ?? "";
      if (name !== "README.md" && !text.includes(name)) {
        errors.push(`.agents/project/README.md does not list ${name}`);
      }
    }
  }

  const agentsMd = join(root, "AGENTS.md");
  if (existsSync(agentsMd)) {
    const text = readFileSync(agentsMd, "utf8");
    for (const requiredRule of [
      ".agents/rules/outcome-boundary.md",
      ".agents/rules/decision-gates.md",
      ".agents/rules/context-loading.md",
      ".agents/rules/session-state.md",
      ".agents/rules/testing-gates.md",
    ]) {
      if (!text.includes(requiredRule)) {
        errors.push(`AGENTS.md does not reference required rule ${requiredRule}`);
      }
    }
  }
  return errors;
}

function validateSessionStateReport(root: string): { errors: string[]; warnings: string[] } {
  const errors: string[] = [];
  const warnings: string[] = [];
  const stateRoot = join(root, ".agents", "session-state");
  if (!existsSync(stateRoot)) {
    return { errors, warnings };
  }
  for (const path of childFiles(stateRoot, ".json")) {
    if (path.endsWith("/schema.json")) {
      continue;
    }
    let data: unknown;
    try {
      data = JSON.parse(readFileSync(path, "utf8")) as unknown;
    } catch (error) {
      errors.push(`${toPosix(relative(root, path))}: invalid JSON: ${String(error)}`);
      continue;
    }
    if (path.endsWith("/current.json")) {
      validateCurrentSessionRegistry(root, path, data, errors);
    } else {
      validateSessionState(root, path, data, errors, warnings);
    }
  }
  return { errors, warnings };
}

function validateSessionState(root: string, path: string, data: unknown, errors: string[], warnings: string[]): void {
  const relPath = toPosix(relative(root, path));
  const obj = requireObject(relPath, data, errors);
  if (!obj) {
    return;
  }
  requireKeys(relPath, obj, ["schema_version", "session", "current_task", "carry_forwards"], errors);
  if (obj.schema_version !== 1) {
    errors.push(`${relPath}: schema_version must be 1`);
  }

  const session = requireNestedObject(relPath, obj, "session", errors);
  if (session) {
    requireKeys(relPath, session, ["id", "label", "updated_at"], errors, "session");
    requireNonEmptyString(relPath, session, "id", errors, "session");
    requireNonEmptyString(relPath, session, "label", errors, "session");
    requireNonEmptyString(relPath, session, "updated_at", errors, "session");
    if ("thread_id" in session && typeof session.thread_id !== "string") {
      errors.push(`${relPath}: session.thread_id must be a string`);
    }
    if ("title_history" in session) {
      requireStringList(relPath, session, "title_history", errors, "session");
    }
  }

  const currentTask = requireNestedObject(relPath, obj, "current_task", errors);
  if (currentTask) {
    for (const key of ["goal", "current_step", "stop_condition", "next_action"]) {
      requireNonEmptyString(relPath, currentTask, key, errors, "current_task");
    }
  }

  const carryForwards = obj.carry_forwards;
  if (!Array.isArray(carryForwards)) {
    errors.push(`${relPath}: carry_forwards must be a list`);
    return;
  }
  const maxCarry = sessionMaxCarryForwards(root);
  if (carryForwards.length > maxCarry) {
    errors.push(`${relPath}: carry_forwards must contain at most ${maxCarry} items`);
  }
  const ids = new Set<string>();
  carryForwards.forEach((item, index) => {
    const prefix = `carry_forwards[${index}]`;
    if (!item || typeof item !== "object" || Array.isArray(item)) {
      errors.push(`${relPath}: ${prefix} must be an object`);
      return;
    }
    const entry = item as Record<string, unknown>;
    requireKeys(relPath, entry, ["id", "type", "content", "why_keep", "expires_when", "updated_at"], errors, prefix);
    for (const key of ["id", "type", "content", "why_keep", "expires_when", "updated_at"]) {
      requireNonEmptyString(relPath, entry, key, errors, prefix);
    }
    const itemType = entry.type;
    if (typeof itemType === "string" && !SESSION_CARRY_FORWARD_TYPES.has(itemType)) {
      errors.push(`${relPath}: ${prefix}.type must be one of: decision, constraint, blocker, handoff`);
    }
    if (typeof entry.id === "string") {
      if (ids.has(entry.id)) {
        errors.push(`${relPath}: duplicate carry_forwards id ${entry.id}`);
      }
      ids.add(entry.id);
    }
    if (typeof entry.expires_when === "string" && sessionExpiryIsPast(entry.expires_when)) {
      const label = typeof entry.id === "string" && entry.id ? entry.id : String(index);
      warnings.push(
        `${relPath}: carry_forwards[${index}] ${JSON.stringify(label)} appears expired by expires_when (${entry.expires_when}); clean it or promote it before final handoff`,
      );
    }
  });
}

function validateCurrentSessionRegistry(root: string, path: string, data: unknown, errors: string[]): void {
  const relPath = toPosix(relative(root, path));
  const obj = requireObject(relPath, data, errors);
  if (!obj) {
    return;
  }
  requireKeys(relPath, obj, ["schema_version", "updated_at", "sessions"], errors);
  if (obj.schema_version !== 1) {
    errors.push(`${relPath}: schema_version must be 1`);
  }
  requireNonEmptyString(relPath, obj, "updated_at", errors);

  const activeSessionFile = typeof obj.active_session_file === "string" ? obj.active_session_file : undefined;
  if ("active_session_file" in obj && !activeSessionFile) {
    errors.push(`${relPath}: active_session_file must be a non-empty string`);
  } else if (activeSessionFile && !existsSync(resolve(root, activeSessionFile))) {
    errors.push(`${relPath}: active_session_file does not exist: ${activeSessionFile}`);
  }

  if (!Array.isArray(obj.sessions)) {
    errors.push(`${relPath}: sessions must be a list`);
    return;
  }
  const sessionFiles = new Set<string>();
  obj.sessions.forEach((item, index) => {
    const prefix = `sessions[${index}]`;
    if (!item || typeof item !== "object" || Array.isArray(item)) {
      errors.push(`${relPath}: ${prefix} must be an object`);
      return;
    }
    const entry = item as Record<string, unknown>;
    requireKeys(relPath, entry, ["file", "label", "updated_at"], errors, prefix);
    for (const key of ["file", "label", "updated_at"]) {
      requireNonEmptyString(relPath, entry, key, errors, prefix);
    }
    if (typeof entry.file === "string") {
      if (!existsSync(resolve(root, entry.file))) {
        errors.push(`${relPath}: ${prefix}.file does not exist: ${entry.file}`);
      }
      if (sessionFiles.has(entry.file)) {
        errors.push(`${relPath}: duplicate ${prefix}.file ${entry.file}`);
      }
      sessionFiles.add(entry.file);
    }
  });
  if (activeSessionFile && !sessionFiles.has(activeSessionFile)) {
    errors.push(`${relPath}: active_session_file is not listed in sessions`);
  }
}

function sessionExpiryIsPast(value: string): boolean {
  const match = value.match(SESSION_EXPIRY_PATTERN);
  if (!match) {
    return false;
  }
  const token = match[0].replace(" ", "T");
  if (token.length === 10) {
    const expiryDate = new Date(`${token}T00:00:00`);
    const now = new Date();
    return expiryDate.toISOString().slice(0, 10) < now.toISOString().slice(0, 10);
  }
  const expiry = new Date(token.replace("Z", "+00:00"));
  if (Number.isNaN(expiry.getTime())) {
    return false;
  }
  return expiry.getTime() < Date.now();
}

function sessionMaxCarryForwards(root: string): number {
  const metadataPath = join(root, ".agents", "agent-feed.json");
  if (!existsSync(metadataPath)) {
    return 7;
  }
  try {
    const data = JSON.parse(readFileSync(metadataPath, "utf8")) as Record<string, unknown>;
    const settings = data.settings;
    if (!settings || typeof settings !== "object" || Array.isArray(settings)) {
      return 7;
    }
    const sessionState = (settings as Record<string, unknown>).session_state;
    if (!sessionState || typeof sessionState !== "object" || Array.isArray(sessionState)) {
      return 7;
    }
    const maxCarry = (sessionState as Record<string, unknown>).max_carry_forwards;
    return typeof maxCarry === "number" && Number.isInteger(maxCarry) && maxCarry >= 1 ? maxCarry : 7;
  } catch {
    return 7;
  }
}

function checkConfiguredAdapter(root: string, check: "codex" | "claude" | "cursor"): { errors: string[]; warnings: string[] } {
  if (check === "codex") {
    return checkCodex(root);
  }
  if (check === "claude") {
    return checkClaude(root);
  }
  return checkCursor(root);
}

function emptyReport(): { errors: string[]; warnings: string[] } {
  return { errors: [], warnings: [] };
}

function requireObject(path: string, data: unknown, errors: string[]): Record<string, unknown> | undefined {
  if (data && typeof data === "object" && !Array.isArray(data)) {
    return data as Record<string, unknown>;
  }
  errors.push(`${path}: root must be a JSON object`);
  return undefined;
}

function requireNestedObject(
  path: string,
  obj: Record<string, unknown>,
  key: string,
  errors: string[],
): Record<string, unknown> | undefined {
  const value = obj[key];
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  errors.push(`${path}: ${key} must be an object`);
  return undefined;
}

function requireKeys(
  path: string,
  obj: Record<string, unknown>,
  keys: string[],
  errors: string[],
  prefix = "",
): void {
  for (const key of keys) {
    if (!(key in obj)) {
      errors.push(`${path}: missing ${prefix ? `${prefix}.` : ""}${key}`);
    }
  }
}

function requireNonEmptyString(
  path: string,
  obj: Record<string, unknown>,
  key: string,
  errors: string[],
  prefix = "",
): void {
  const value = obj[key];
  if (typeof value !== "string" || !value) {
    errors.push(`${path}: ${prefix ? `${prefix}.` : ""}${key} must be a non-empty string`);
  }
}

function requireStringList(
  path: string,
  obj: Record<string, unknown>,
  key: string,
  errors: string[],
  prefix = "",
): void {
  const value = obj[key];
  if (!Array.isArray(value) || !value.every((item) => typeof item === "string")) {
    errors.push(`${path}: ${prefix ? `${prefix}.` : ""}${key} must be a list of strings`);
  }
}

function skillFiles(root: string): string[] {
  const skillRoot = join(root, ".agents", "skills");
  return childDirs(skillRoot).map((dir) => join(dir, "SKILL.md")).filter((path) => existsSync(path));
}

function walkMarkdownFiles(root: string): string[] {
  return walkFiles(root).filter((path) => path.endsWith(".md"));
}

function walkFiles(root: string): string[] {
  const results: string[] = [];
  if (!existsSync(root)) {
    return results;
  }
  for (const entry of childEntries(root)) {
    results.push(entry);
    if (statSync(entry).isDirectory()) {
      results.push(...walkFiles(entry));
    }
  }
  return results;
}

function childEntries(root: string): string[] {
  if (!existsSync(root)) {
    return [];
  }
  return readdirSync(root)
    .filter((entry) => entry !== ".DS_Store" && entry !== "__pycache__")
    .map((entry) => join(root, entry));
}

function childDirs(root: string): string[] {
  return childEntries(root).filter((path) => statSync(path).isDirectory()).sort();
}

function childFiles(root: string, suffix: string): string[] {
  if (!existsSync(root)) {
    return [];
  }
  return walkFiles(root).filter((path) => path.endsWith(suffix)).sort();
}

function toPosix(path: string): string {
  return path.replaceAll("\\", "/");
}
