import {
  chmodSync,
  cpSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { VERSION } from "./version.js";

const CURRENT_DIR = dirname(fileURLToPath(import.meta.url));
const TEMPLATE_ROOT = join(CURRENT_DIR, "..", "templates", "standard");

export type VerificationProfile = "python" | "node" | "custom" | "none";

export type WriteAction = {
  path: string;
  action: string;
  detail?: string;
  diff?: string;
};

export type PlannedFile = {
  relPath: string;
  path: string;
  content: string;
};

export type Metadata = Record<string, unknown>;

export function walkFiles(root: string): string[] {
  const results: string[] = [];
  for (const entry of readdirSync(root)) {
    if (entry === ".DS_Store" || entry === "__pycache__") {
      continue;
    }
    const next = join(root, entry);
    const stats = statSync(next);
    if (stats.isDirectory()) {
      results.push(...walkFiles(next));
    } else if (stats.isFile()) {
      results.push(next);
    }
  }
  return results;
}

function renderTemplate(content: string, projectName: string, profile: VerificationProfile): string {
  return content
    .replaceAll("{{PROJECT_NAME}}", projectName)
    .replaceAll("{{AGENT_FEED_VERSION}}", VERSION)
    .replaceAll("{{VERIFICATION_PROFILE}}", profile);
}

export function parseProfile(raw: string | undefined, fallback: VerificationProfile): VerificationProfile {
  const normalized = (raw ?? fallback).trim().toLowerCase();
  if (
    normalized === "python" ||
    normalized === "node" ||
    normalized === "custom" ||
    normalized === "none"
  ) {
    return normalized;
  }
  throw new Error("verification profile must be one of python, node, custom, none");
}

export function isInstalled(root: string): boolean {
  return existsSync(join(root, "AGENTS.md")) && existsSync(join(root, ".agents"));
}

export function readMetadata(root: string): Metadata {
  const path = join(root, ".agents", "agent-feed.json");
  if (!existsSync(path)) {
    return {};
  }
  try {
    const parsed = JSON.parse(readFileSync(path, "utf8")) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as Metadata)
      : {};
  } catch {
    return {};
  }
}

export function inferProjectName(root: string): string {
  const metadata = readMetadata(root);
  const projectName = metadata.project_name;
  if (typeof projectName === "string" && projectName.trim()) {
    return projectName.trim();
  }
  return root.split(/[\\/]/).filter(Boolean).at(-1) ?? "project";
}

export function inferProfile(root: string): VerificationProfile {
  const profile = readMetadata(root).verification_profile;
  return parseProfile(typeof profile === "string" ? profile : undefined, "python");
}

function defaultSettings(): Record<string, unknown> {
  return {
    session_state: {
      max_carry_forwards: 7,
    },
    skills: {
      default_import_source: "unknow",
      default_import_trust: "custom",
    },
    claude: {
      required_snippets: ["@AGENTS.md", ".claude/skills", ".agents/"],
    },
  };
}

function mergeSettings(current: unknown): Record<string, unknown> {
  const merged = defaultSettings();
  if (!current || typeof current !== "object" || Array.isArray(current)) {
    return merged;
  }
  const settings = current as Record<string, unknown>;
  const sessionState = settings.session_state;
  if (sessionState && typeof sessionState === "object" && !Array.isArray(sessionState)) {
    const maxCarry = (sessionState as Record<string, unknown>).max_carry_forwards;
    if (typeof maxCarry === "number" && Number.isInteger(maxCarry) && maxCarry >= 1) {
      (merged.session_state as Record<string, unknown>).max_carry_forwards = maxCarry;
    }
  }
  const skills = settings.skills;
  if (skills && typeof skills === "object" && !Array.isArray(skills)) {
    const rawSkills = skills as Record<string, unknown>;
    if (typeof rawSkills.default_import_source === "string" && rawSkills.default_import_source.trim()) {
      (merged.skills as Record<string, unknown>).default_import_source =
        rawSkills.default_import_source.trim();
    }
    if (
      rawSkills.default_import_trust === "custom" ||
      rawSkills.default_import_trust === "reviewed"
    ) {
      (merged.skills as Record<string, unknown>).default_import_trust =
        rawSkills.default_import_trust;
    }
  }
  const claude = settings.claude;
  if (claude && typeof claude === "object" && !Array.isArray(claude)) {
    const snippets = (claude as Record<string, unknown>).required_snippets;
    if (
      Array.isArray(snippets) &&
      snippets.some((item) => typeof item === "string" && item.length > 0)
    ) {
      (merged.claude as Record<string, unknown>).required_snippets = snippets.filter(
        (item): item is string => typeof item === "string" && item.length > 0,
      );
    }
  }
  return merged;
}

export function renderMetadata(root: string, projectName: string, profile: VerificationProfile): string {
  const current = readMetadata(root);
  return `${JSON.stringify(
    {
      schema_version: 1,
      agent_feed_version: VERSION,
      template: "standard",
      project_name: projectName,
      verification_profile: profile,
      settings: mergeSettings(current.settings),
      managed_paths: [
        "AGENTS.md",
        ".agents/README.md",
        ".agents/agent-feed.json",
        ".agents/rules/",
        ".agents/skills/",
        ".agents/scripts/",
        ".agents/agents/README.md",
        ".agents/session-state/README.md",
        ".agents/session-state/schema.json",
        ".agents/session-state/.gitignore",
      ],
      user_maintained_paths: [".agents/project/", ".agents/domain/"],
    },
    null,
    2,
  )}\n`;
}

export function renderSessionSchema(root: string): string {
  const maxCarry =
    ((mergeSettings(readMetadata(root).settings).session_state as Record<string, unknown>)
      .max_carry_forwards as number | undefined) ?? 7;
  return `${JSON.stringify(
    {
      $schema: "https://json-schema.org/draft/2020-12/schema",
      title: "AI Development Session Handoff",
      type: "object",
      required: ["schema_version", "session", "current_task", "carry_forwards"],
      additionalProperties: false,
      properties: {
        schema_version: { type: "integer", const: 1 },
        session: {
          type: "object",
          required: ["id", "label", "updated_at"],
          additionalProperties: false,
          properties: {
            id: { type: "string", minLength: 1 },
            label: { type: "string", minLength: 1 },
            updated_at: { type: "string", minLength: 1 },
            thread_id: {
              type: "string",
              description: "Optional AI-client thread id when the environment exposes it.",
            },
            title_history: {
              type: "array",
              items: { type: "string" },
              description: "Optional known conversation titles or aliases.",
            },
          },
        },
        current_task: {
          type: "object",
          required: ["goal", "current_step", "stop_condition", "next_action"],
          additionalProperties: false,
          properties: {
            goal: { type: "string", minLength: 1 },
            current_step: { type: "string", minLength: 1 },
            stop_condition: { type: "string", minLength: 1 },
            next_action: { type: "string", minLength: 1 },
          },
        },
        carry_forwards: {
          type: "array",
          maxItems: maxCarry,
          items: {
            type: "object",
            required: ["id", "type", "content", "why_keep", "expires_when", "updated_at"],
            additionalProperties: false,
            properties: {
              id: { type: "string", minLength: 1 },
              type: { type: "string", enum: ["decision", "constraint", "blocker", "handoff"] },
              content: { type: "string", minLength: 1 },
              why_keep: { type: "string", minLength: 1 },
              expires_when: { type: "string", minLength: 1 },
              updated_at: { type: "string", minLength: 1 },
            },
          },
        },
      },
    },
    null,
    2,
  )}\n`;
}

export function canonicalPlan(
  targetRoot: string,
  projectName: string,
  profile: VerificationProfile,
): PlannedFile[] {
  return walkFiles(TEMPLATE_ROOT).map((sourcePath) => {
    const rel = toPosixPath(relative(TEMPLATE_ROOT, sourcePath));
    const sourceContent = readFileSync(sourcePath, "utf8");
    const content =
      rel === ".agents/agent-feed.json"
        ? renderMetadata(targetRoot, projectName, profile)
        : rel === ".agents/session-state/schema.json"
          ? renderSessionSchema(targetRoot)
          : renderTemplate(sourceContent, projectName, profile);
    return {
      relPath: rel,
      path: join(targetRoot, rel),
      content,
    };
  });
}

export function planTemplateWrites(
  targetRoot: string,
  projectName: string,
  profile: VerificationProfile,
): WriteAction[] {
  return canonicalPlan(targetRoot, projectName, profile).map((item) => ({
    path: item.path,
    action: existsSync(item.path) ? "would skip" : "would create",
  }));
}

export function applyTemplates(
  targetRoot: string,
  projectName: string,
  profile: VerificationProfile,
): WriteAction[] {
  const actions: WriteAction[] = [];
  for (const item of canonicalPlan(targetRoot, projectName, profile)) {
    if (existsSync(item.path)) {
      actions.push({ path: item.path, action: "skip", detail: "already exists" });
      continue;
    }
    writeFile(item.path, item.content);
    actions.push({ path: item.path, action: "create" });
  }
  return actions;
}

export function upgradePlan(
  targetRoot: string,
  projectName: string,
  profile: VerificationProfile,
  dryRun: boolean,
): { actions: WriteAction[]; errors: string[] } {
  if (!isInstalled(targetRoot)) {
    return { actions: [], errors: ["missing Agent Feed installation; run agent-feed init first"] };
  }

  const actions: WriteAction[] = [];
  const errors: string[] = [];
  for (const item of canonicalPlan(targetRoot, projectName, profile)) {
    const current = existsSync(item.path) ? readFileSync(item.path, "utf8") : undefined;
    if (current === item.content) {
      continue;
    }
    if (current !== undefined && isUserMaintainedPath(item.relPath)) {
      continue;
    }
    if (current !== undefined && item.relPath === ".agents/skills/README.md") {
      actions.push({
        path: item.path,
        action: "skip",
        detail: "skill index may include imported skills; regenerate with index-skills",
      });
      continue;
    }
    const action = current === undefined ? "create" : "update";
    const diff = current === undefined ? "" : unifiedDiff(item.relPath, current, item.content);
    actions.push({ path: item.path, action: dryRun ? `would ${action}` : action, diff });
    if (!dryRun) {
      writeFile(item.path, item.content);
    }
  }
  if (actions.length === 0) {
    actions.push({
      path: targetRoot,
      action: "skip",
      detail: `canonical assets already match agent-feed ${VERSION}`,
    });
  }
  return { actions, errors };
}

export function isUserMaintainedPath(relPath: string): boolean {
  return relPath.startsWith(".agents/project/") || relPath.startsWith(".agents/domain/");
}

function toPosixPath(path: string): string {
  return path.replaceAll("\\", "/");
}

export function writeFile(path: string, content: string): void {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content, "utf8");
  if (path.endsWith(".sh")) {
    chmodSync(path, 0o755);
  }
}

export function unifiedDiff(relPath: string, current: string, expected: string): string {
  const currentLines = current.split(/\r?\n/);
  const expectedLines = expected.split(/\r?\n/);
  const lines = [`--- ${relPath} (current)`, `+++ ${relPath} (template ${VERSION})`];
  const max = Math.max(currentLines.length, expectedLines.length);
  for (let index = 0; index < max; index += 1) {
    const before = currentLines[index];
    const after = expectedLines[index];
    if (before === after) {
      continue;
    }
    if (before !== undefined) {
      lines.push(`-${before}`);
    }
    if (after !== undefined) {
      lines.push(`+${after}`);
    }
  }
  return lines.join("\n");
}

export function copyTemplateAssets(distRoot: string): void {
  const target = join(distRoot, "templates", "standard");
  mkdirSync(dirname(target), { recursive: true });
  cpSync(join(CURRENT_DIR, "..", "..", "src", "templates", "standard"), target, {
    recursive: true,
  });
}
