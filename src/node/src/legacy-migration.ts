import { existsSync, mkdirSync, readdirSync, readFileSync, renameSync, rmdirSync, writeFileSync } from "node:fs";
import { basename, dirname, join, relative, resolve } from "node:path";

import { isManagedSkillMirror, isManagedCursorRule, missingClaudeSnippets } from "./adapters.js";
import { canonicalPlan, type VerificationProfile, type WriteAction } from "./template.js";

const BACKUP_ROOT = ".feed-backup";
const MIGRATION_GUIDE_NAME = "AI_MIGRATION_GUIDE.md";
const MANIFEST_NAME = "manifest.json";

const LEGACY_FILE_PATHS = [
  "AGENTS.md",
  "AGENTS.local.md",
  "CLAUDE.md",
  ".cursorrules",
  ".cursor/rules/agent-feed.mdc",
];

const LEGACY_DIR_PATHS = [
  ".agents",
  ".claude/skills",
  ".codex/skills",
  ".cursor/rules",
];

type LegacyAsset = {
  relPath: string;
  kind: "file" | "directory";
};

export function backupLegacyAiAssets(
  target: string,
  options: {
    projectName: string;
    verificationProfile: VerificationProfile;
    dryRun: boolean;
  },
): { actions: WriteAction[]; errors: string[] } {
  const found = findLegacyAiAssets(target);
  if (found.errors.length > 0 || found.assets.length === 0) {
    return { actions: [], errors: found.errors };
  }

  const backupDir = nextBackupDir(target);
  const actions: WriteAction[] = [];
  const manifestEntries: Array<Record<string, string>> = [];
  for (const asset of found.assets) {
    const source = join(target, asset.relPath);
    const destination = join(backupDir, asset.relPath);
    actions.push({
      path: source,
      action: options.dryRun ? "would backup" : "backup",
      detail: `-> ${toPosix(relative(target, destination))}`,
    });
    manifestEntries.push({
      path: toPosix(asset.relPath),
      kind: asset.kind,
      destination: toPosix(relative(target, destination)),
    });
    if (!options.dryRun) {
      mkdirSync(dirname(destination), { recursive: true });
      renameSync(source, destination);
      pruneEmptyParents(dirname(source), target);
    }
  }

  const manifest = renderManifest({
    projectName: options.projectName,
    assets: manifestEntries,
    projectDomainScaffolded: projectDomainScaffolded(target, options.projectName, options.verificationProfile),
  });
  actions.push(
    writeBackupText(join(backupDir, MANIFEST_NAME), `${JSON.stringify(manifest, null, 2)}\n`, options.dryRun),
    writeBackupText(join(backupDir, MIGRATION_GUIDE_NAME), renderMigrationGuide(manifest), options.dryRun),
  );
  return { actions, errors: [] };
}

export function backupActionsInclude(actions: WriteAction[], relPath: string, target: string): boolean {
  const path = resolve(target, relPath);
  return actions.some(
    (action) =>
      (action.action === "backup" || action.action === "would backup") &&
      (resolve(action.path) === path || isInside(path, action.path)),
  );
}

function findLegacyAiAssets(target: string): { assets: LegacyAsset[]; errors: string[] } {
  const assets: LegacyAsset[] = [];
  const errors: string[] = [];

  for (const relPath of LEGACY_FILE_PATHS) {
    const path = join(target, relPath);
    if (!existsSync(path)) {
      continue;
    }
    if (isDirectoryLike(path)) {
      errors.push(`${toPosix(relPath)} exists but is not a file`);
      continue;
    }
    if (isGeneratedAdapter(path)) {
      continue;
    }
    assets.push({ relPath, kind: "file" });
  }

  for (const relPath of LEGACY_DIR_PATHS) {
    const path = join(target, relPath);
    if (!existsSync(path)) {
      continue;
    }
    if (!isDirectoryLike(path)) {
      errors.push(`${toPosix(relPath)} exists but is not a directory`);
      continue;
    }
    if (readdirSync(path).length === 0) {
      continue;
    }
    if (relPath === ".claude/skills" && isManagedSkillMirror(join(target, ".claude"))) {
      continue;
    }
    assets.push({ relPath, kind: "directory" });
  }

  return { assets: dedupeNestedAssets(assets), errors };
}

function dedupeNestedAssets(assets: LegacyAsset[]): LegacyAsset[] {
  const ordered = [...assets].sort((left, right) => {
    const length = left.relPath.split(/[\\/]/).length - right.relPath.split(/[\\/]/).length;
    return length === 0 ? left.relPath.localeCompare(right.relPath) : length;
  });
  const kept: LegacyAsset[] = [];
  for (const asset of ordered) {
    if (kept.some((existing) => isInside(join("/", asset.relPath), join("/", existing.relPath)))) {
      continue;
    }
    kept.push(asset);
  }
  return kept;
}

function isGeneratedAdapter(path: string): boolean {
  if (basename(path) === "CLAUDE.md") {
    return missingClaudeSnippets(path).length === 0;
  }
  if (basename(path) === "agent-feed.mdc") {
    return isManagedCursorRule(path);
  }
  return false;
}

function nextBackupDir(target: string): string {
  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
  const base = join(target, BACKUP_ROOT, stamp);
  let candidate = base;
  let counter = 2;
  while (existsSync(candidate)) {
    candidate = `${base}-${counter}`;
    counter += 1;
  }
  return candidate;
}

function writeBackupText(path: string, content: string, dryRun: boolean): WriteAction {
  if (dryRun) {
    return { path, action: "would create", detail: "legacy migration record" };
  }
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content, "utf8");
  return { path, action: "create", detail: "legacy migration record" };
}

function pruneEmptyParents(path: string, stop: string): void {
  let current = resolve(path);
  const boundary = resolve(stop);
  while (current !== boundary && isInside(current, boundary)) {
    try {
      rmdirSync(current);
    } catch {
      return;
    }
    current = dirname(current);
  }
}

function projectDomainScaffolded(target: string, projectName: string, verificationProfile: VerificationProfile): boolean {
  const expected = canonicalPlan(target, projectName, verificationProfile).filter(
    (item) => item.relPath.startsWith(".agents/project/") || item.relPath.startsWith(".agents/domain/"),
  );
  for (const item of expected) {
    if (existsSync(item.path) && readFileSync(item.path, "utf8") !== item.content) {
      return false;
    }
  }
  return true;
}

function renderManifest(options: {
  projectName: string;
  assets: Array<Record<string, string>>;
  projectDomainScaffolded: boolean;
}): Record<string, unknown> {
  return {
    version: 1,
    created_at: new Date().toISOString(),
    project_name: options.projectName,
    purpose: "legacy-ai-instruction-backup",
    project_domain_scaffolded: options.projectDomainScaffolded,
    assets: options.assets,
    ai_migration_policy: {
      target_layers: [".agents/project/", ".agents/domain/"],
      must_preserve: [
        "decisive project AI workflows",
        "architecture and source layout boundaries",
        "verification and review requirements",
        "security, persistence, trace, and release constraints",
        "stable domain concepts, contracts, and source-of-truth ownership",
      ],
      must_stop_for_user: [
        "a decisive legacy rule conflicts with Agent Feed generic workflow",
        "a legacy rule is redundant but removing it could affect the AI development loop",
        "evidence is insufficient to decide whether a legacy rule still applies",
        "project/domain files are already user-maintained instead of scaffold-only",
      ],
    },
  };
}

function renderMigrationGuide(manifest: Record<string, unknown>): string {
  const assets = Array.isArray(manifest.assets) ? manifest.assets : [];
  const assetLines = assets
    .filter((entry): entry is Record<string, string> => Boolean(entry) && typeof entry === "object")
    .map((entry) => `- \`${entry.path}\` -> \`${entry.destination}\``)
    .join("\n");
  const scaffoldText = manifest.project_domain_scaffolded
    ? "Project/domain files appear to be scaffold-only, so AI may migrate supported facts directly into `.agents/project/` and `.agents/domain/`."
    : "Project/domain files appear user-maintained, so AI must not overwrite them. Produce a migration report and ask before editing.";
  return `# Legacy AI Instruction Migration Guide

Agent Feed moved pre-existing AI instruction assets into this backup before installing
the canonical protocol.

## Backed Up Assets

${assetLines}

## Migration Policy

${scaffoldText}

AI assistants must follow these rules before using or migrating the backup:

1. Read every backed-up file that can affect AI development behavior.
2. Preserve every decisive workflow, project rule, verification rule, security rule,
   architecture boundary, domain concept, contract, and source-of-truth rule.
3. Move reusable generic guidance only when it is not already covered by Agent Feed.
4. Prefer \`.agents/project/\` for repository-specific engineering constraints.
5. Prefer \`.agents/domain/\` for stable concepts, contracts, and ownership facts.
6. Do not copy stale, duplicated, or conflicting instructions blindly.
7. Stop and ask the user when removing, rewriting, or merging a legacy rule could
   affect the AI development loop or future project results.
8. Record uncertain items as assumptions instead of presenting them as facts.

After migration, run \`sh .agents/scripts/verify-agent-dev.sh docs\`.
`;
}

function isDirectoryLike(path: string): boolean {
  try {
    return readdirSync(path) !== undefined;
  } catch {
    return false;
  }
}

function isInside(path: string, parent: string): boolean {
  const child = resolve(path);
  const boundary = resolve(parent);
  return child === boundary || child.startsWith(`${boundary}/`) || child.startsWith(`${boundary}\\`);
}

function toPosix(path: string): string {
  return path.replaceAll("\\", "/");
}
