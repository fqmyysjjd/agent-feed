import {
  cpSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { dirname, join, relative } from "node:path";

import type { WriteAction } from "./template.js";

export type Client = "codex" | "claude" | "cursor";

export const ALL_CLIENTS: Client[] = ["codex", "claude", "cursor"];

const CURSOR_MARKER = "<!-- agent-feed:managed adapter=cursor version=1 -->";
const CLAUDE_MARKER = "<!-- agent-feed:managed adapter=claude version=1 -->";
const CLAUDE_REQUIRED_SNIPPETS = ["@AGENTS.md", ".claude/skills", ".agents/"];

export function parseClients(raw: string | undefined, useAll: boolean, fallback: Client[]): Client[] {
  if (useAll) {
    return ALL_CLIENTS;
  }
  if (!raw) {
    return fallback;
  }
  const values = raw
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
  if (values.includes("none")) {
    return [];
  }
  if (values.includes("all")) {
    return ALL_CLIENTS;
  }
  const clients: Client[] = [];
  for (const value of values) {
    if (value !== "codex" && value !== "claude" && value !== "cursor") {
      throw new Error("clients must be one of codex, claude, cursor, all, none");
    }
    clients.push(value);
  }
  return clients;
}

export function installedClients(root: string): Client[] {
  const clients: Client[] = ["codex"];
  if (existsSync(join(root, "CLAUDE.md")) || existsSync(join(root, ".claude", "skills"))) {
    clients.push("claude");
  }
  if (existsSync(join(root, ".cursor", "rules", "agent-feed.mdc"))) {
    clients.push("cursor");
  }
  return clients;
}

export function syncClients(
  root: string,
  clients: Client[],
  dryRun: boolean,
  assumeInitialized = false,
): { actions: WriteAction[]; errors: string[] } {
  if (clients.length === 0) {
    return { actions: [{ path: root, action: "skip", detail: "no clients selected" }], errors: [] };
  }
  if (!assumeInitialized && !existsSync(join(root, ".agents"))) {
    return { actions: [], errors: ["missing .agents; run agent-feed init first"] };
  }
  const actions: WriteAction[] = [];
  const errors: string[] = [];
  for (const client of clients) {
    if (client === "codex") {
      actions.push({
        path: root,
        action: "ok",
        detail: "Codex uses AGENTS.md and .agents/skills directly",
      });
    } else if (client === "claude") {
      const result = syncClaude(root, dryRun);
      actions.push(...result.actions);
      errors.push(...result.errors);
    } else if (client === "cursor") {
      const result = syncCursor(root, dryRun);
      actions.push(...result.actions);
      errors.push(...result.errors);
    }
  }
  return { actions, errors };
}

export function checkAdapters(root: string): { errors: string[]; warnings: string[] } {
  const errors: string[] = [];
  const warnings: string[] = [];
  if (!existsSync(join(root, "AGENTS.md"))) {
    errors.push("Codex adapter missing AGENTS.md");
  }
  if (!existsSync(join(root, ".agents", "skills"))) {
    errors.push("Codex adapter missing .agents/skills");
  }
  if (existsSync(join(root, ".codex", "skills"))) {
    warnings.push(".codex/skills exists but Codex uses .agents/skills directly");
  }
  if (existsSync(join(root, "CLAUDE.md")) || existsSync(join(root, ".claude", "skills"))) {
    const claude = checkClaude(root);
    errors.push(...claude.errors);
    warnings.push(...claude.warnings);
  }
  if (existsSync(join(root, ".cursor", "rules", "agent-feed.mdc"))) {
    const cursor = checkCursor(root);
    errors.push(...cursor.errors);
    warnings.push(...cursor.warnings);
  }
  return { errors, warnings };
}

function syncClaude(root: string, dryRun: boolean): { actions: WriteAction[]; errors: string[] } {
  const actions: WriteAction[] = [];
  const errors: string[] = [];
  const claudePath = join(root, "CLAUDE.md");
  const skillsSource = join(root, ".agents", "skills");
  const skillsTarget = join(root, ".claude", "skills");
  const targetRoot = join(root, ".claude");

  if (existsSync(claudePath)) {
    const missing = missingClaudeSnippets(claudePath);
    if (missing.length > 0) {
      errors.push(`CLAUDE.md is missing required Agent Feed references: ${missing.join(", ")}`);
    } else {
      actions.push({ path: claudePath, action: "skip", detail: "contains Agent Feed references" });
    }
  } else if (dryRun) {
    actions.push({ path: claudePath, action: "would create" });
  } else {
    writeText(claudePath, claudeMd());
    actions.push({ path: claudePath, action: "create" });
  }

  if (existsSync(skillsTarget) && !isManagedSkillMirror(targetRoot)) {
    errors.push(".claude/skills exists and is unmanaged; move it aside before syncing");
    return { actions, errors };
  }
  if (!existsSync(skillsSource)) {
    if (dryRun) {
      actions.push({
        path: skillsTarget,
        action: "would sync",
        detail: ".agents/skills -> .claude/skills",
      });
      return { actions, errors };
    }
    errors.push("missing .agents/skills; cannot sync Claude skills");
    return { actions, errors };
  }
  if (dryRun) {
    actions.push({
      path: skillsTarget,
      action: sameTree(skillsSource, skillsTarget) ? "skip" : "would sync",
      detail: ".agents/skills -> .claude/skills",
    });
    return { actions, errors };
  }
  copyTreeReplace(skillsSource, skillsTarget);
  writeText(join(targetRoot, "README.md"), skillMirrorReadme());
  actions.push({
    path: skillsTarget,
    action: "sync",
    detail: ".agents/skills -> .claude/skills",
  });
  return { actions, errors };
}

function syncCursor(root: string, dryRun: boolean): { actions: WriteAction[]; errors: string[] } {
  const target = join(root, ".cursor", "rules", "agent-feed.mdc");
  if (existsSync(target) && !isManagedCursorRule(target)) {
    return {
      actions: [],
      errors: [".cursor/rules/agent-feed.mdc exists and is unmanaged"],
    };
  }
  const nextContent = cursorRule();
  if (existsSync(target) && readFileSync(target, "utf8") === nextContent) {
    return { actions: [{ path: target, action: "skip" }], errors: [] };
  }
  const action = existsSync(target) ? "update" : "create";
  if (dryRun) {
    return { actions: [{ path: target, action: `would ${action}` }], errors: [] };
  }
  writeText(target, nextContent);
  return { actions: [{ path: target, action }], errors: [] };
}

function checkClaude(root: string): { errors: string[]; warnings: string[] } {
  const errors: string[] = [];
  const warnings: string[] = [];
  const claudePath = join(root, "CLAUDE.md");
  const skillsTarget = join(root, ".claude", "skills");
  const skillsSource = join(root, ".agents", "skills");
  if (!existsSync(claudePath)) {
    errors.push("Claude adapter missing CLAUDE.md");
  } else {
    for (const snippet of missingClaudeSnippets(claudePath)) {
      errors.push(`CLAUDE.md must contain ${snippet}`);
    }
  }
  if (!existsSync(skillsTarget)) {
    errors.push("Claude adapter missing .claude/skills");
  } else if (existsSync(skillsSource) && !sameTree(skillsSource, skillsTarget)) {
    errors.push(".claude/skills is out of sync with .agents/skills");
  }
  if (existsSync(join(root, ".claude", "rules"))) {
    warnings.push(".claude/rules exists; Agent Feed does not manage Claude path-scoped rules yet");
  }
  return { errors, warnings };
}

function checkCursor(root: string): { errors: string[]; warnings: string[] } {
  const errors: string[] = [];
  const warnings: string[] = [];
  const target = join(root, ".cursor", "rules", "agent-feed.mdc");
  if (!existsSync(target)) {
    errors.push("Cursor adapter missing .cursor/rules/agent-feed.mdc");
  } else if (!isManagedCursorRule(target)) {
    errors.push(".cursor/rules/agent-feed.mdc is not a managed Agent Feed adapter");
  } else {
    const text = readFileSync(target, "utf8");
    if (!text.includes("alwaysApply: true")) {
      errors.push("Cursor adapter must set alwaysApply: true");
    }
    if (!text.includes("@AGENTS.md")) {
      errors.push("Cursor adapter must import @AGENTS.md");
    }
  }
  if (existsSync(join(root, ".cursorrules"))) {
    warnings.push(".cursorrules exists; it is legacy and not managed by Agent Feed");
  }
  return { errors, warnings };
}

function claudeMd(): string {
  return `${CLAUDE_MARKER}
@AGENTS.md

## Claude Code

Use \`AGENTS.md\` as the canonical project protocol.
Use \`.claude/skills/\` for Claude Code skill discovery.
Do not duplicate \`.agents/rules/\`; update the canonical files under \`.agents/\`.
`;
}

function cursorRule(): string {
  return `---
description: Agent Feed AI development protocol
alwaysApply: true
---
${CURSOR_MARKER}

@AGENTS.md

Start with \`AGENTS.md\`, then follow the referenced \`.agents/\` rules, project
constraints, domain docs, and skills.

Treat this Cursor rule as an adapter pointer. Do not duplicate \`.agents/rules/\`
inside \`.cursor/rules/\`.
`;
}

function missingClaudeSnippets(path: string): string[] {
  const text = readFileSync(path, "utf8");
  return CLAUDE_REQUIRED_SNIPPETS.filter((snippet) => !text.includes(snippet));
}

function isManagedCursorRule(path: string): boolean {
  return existsSync(path) && readFileSync(path, "utf8").includes(CURSOR_MARKER);
}

function isManagedSkillMirror(targetRoot: string): boolean {
  const readme = join(targetRoot, "README.md");
  return (
    existsSync(readme) &&
    readFileSync(readme, "utf8").startsWith("# Synced AI Development Skills") &&
    readFileSync(readme, "utf8").includes("generated from `.agents/skills/`")
  );
}

function writeText(path: string, content: string): void {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content, "utf8");
}

function copyTreeReplace(source: string, target: string): void {
  rmSync(target, { recursive: true, force: true });
  mkdirSync(target, { recursive: true });
  for (const sourcePath of walkTree(source)) {
    const targetPath = join(target, relative(source, sourcePath));
    const stats = statSync(sourcePath);
    if (stats.isDirectory()) {
      mkdirSync(targetPath, { recursive: true });
    } else if (stats.isFile()) {
      mkdirSync(dirname(targetPath), { recursive: true });
      cpSync(sourcePath, targetPath);
    }
  }
}

function sameTree(left: string, right: string): boolean {
  if (!existsSync(left) || !existsSync(right)) {
    return false;
  }
  const leftFiles = walkTree(left).filter((item) => statSync(item).isFile());
  const rightFiles = walkTree(right).filter((item) => statSync(item).isFile());
  const leftRels = leftFiles.map((item) => relative(left, item)).sort();
  const rightRels = rightFiles.map((item) => relative(right, item)).sort();
  if (leftRels.join("\n") !== rightRels.join("\n")) {
    return false;
  }
  return leftRels.every(
    (relPath) => readFileSync(join(left, relPath), "utf8") === readFileSync(join(right, relPath), "utf8"),
  );
}

function walkTree(root: string): string[] {
  if (!existsSync(root)) {
    return [];
  }
  const results: string[] = [];
  for (const entry of readdirSync(root)) {
    if (entry === ".DS_Store" || entry === "__pycache__") {
      continue;
    }
    const next = join(root, entry);
    results.push(next);
    if (statSync(next).isDirectory()) {
      results.push(...walkTree(next));
    }
  }
  return results;
}

function skillMirrorReadme(): string {
  return `# Synced AI Development Skills

This directory is generated from \`.agents/skills/\`.

Rules stay in \`.agents/rules/\` and are not synced here.
`;
}
