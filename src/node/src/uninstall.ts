import { existsSync, readFileSync, readdirSync, rmSync, rmdirSync, statSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";

import { isManagedSkillMirror, isManagedCursorRule, missingClaudeSnippets } from "./adapters.js";
import { type WriteAction } from "./template.js";
import { checkAssetTrust } from "./trust.js";

export function uninstallPlan(root: string, dryRun: boolean): WriteAction[] {
  const action = dryRun ? "would delete" : "delete";
  const actions: WriteAction[] = [];

  planPath(actions, join(root, "CLAUDE.md"), {
    action,
    safe: isManagedClaudeMd(join(root, "CLAUDE.md")),
    unmanagedDetail: "unmanaged Claude instructions; not removed",
    managedDetail: "managed Claude adapter",
  });

  const claudeRoot = join(root, ".claude");
  const claudeSkills = join(claudeRoot, "skills");
  const claudeReadme = join(claudeRoot, "README.md");
  const managedClaudeSkills = isManagedSkillMirror(claudeRoot);
  planPath(actions, claudeSkills, {
    action,
    safe: managedClaudeSkills,
    unmanagedDetail: "unmanaged Claude skills; not removed",
    managedDetail: "managed Claude skills mirror",
  });
  planPath(actions, claudeReadme, {
    action,
    safe: managedClaudeSkills,
    unmanagedDetail: "unmanaged Claude README; not removed",
    managedDetail: "managed Claude skills README",
  });

  planPath(actions, join(root, ".cursor", "rules", "agent-feed.mdc"), {
    action,
    safe: isManagedCursorRule(join(root, ".cursor", "rules", "agent-feed.mdc")),
    unmanagedDetail: "unmanaged Cursor rule; not removed",
    managedDetail: "managed Cursor adapter",
  });

  const codexSkills = join(root, ".codex", "skills");
  const agentsSkills = join(root, ".agents", "skills");
  planPath(actions, codexSkills, {
    action,
    safe: existsSync(agentsSkills) && existsSync(codexSkills) && sameTree(agentsSkills, codexSkills),
    unmanagedDetail: "legacy .codex/skills is not a verified mirror; not removed",
    managedDetail: "legacy Agent Feed Codex skill mirror",
  });

  planPath(actions, join(root, "AGENTS.md"), {
    action,
    safe: isAgentFeedAgentsMd(join(root, "AGENTS.md")),
    unmanagedDetail: "unmanaged AGENTS.md; not removed",
    managedDetail: "Agent Feed entry contract",
  });

  planPath(actions, join(root, ".agents"), {
    action,
    safe: isAgentFeedAgentsDir(join(root, ".agents")),
    unmanagedDetail: "unmanaged .agents directory; not removed",
    managedDetail: "Agent Feed protocol directory",
  });

  actions.push(...projectTrustUninstallPlan(root, dryRun));
  return actions;
}

export function applyUninstallPlan(root: string, actions: WriteAction[]): WriteAction[] {
  const applied: WriteAction[] = [];
  const parentsToPrune = new Set<string>();
  for (const item of actions) {
    if (item.action === "update" && item.detail === "remove external trust state for this project") {
      removeProjectTrustState(root, item.path);
      applied.push({ path: item.path, action: "updated", detail: item.detail });
      continue;
    }
    if (item.action !== "delete") {
      continue;
    }
    if (!existsSync(item.path)) {
      applied.push({ path: item.path, action: "skip", detail: "already absent" });
      continue;
    }
    rmSync(item.path, { recursive: true, force: true });
    applied.push({ path: item.path, action: "deleted", detail: item.detail });
    if (["agent-feed.mdc", "README.md", "skills"].includes(basename(item.path))) {
      parentsToPrune.add(dirname(item.path));
    }
  }
  for (const directory of parentsToPrune) {
    removeEmptyParents(directory);
  }
  return applied;
}

export function uninstallHasDeletions(actions: WriteAction[]): boolean {
  return actions.some((item) =>
    item.action === "delete" ||
    item.action === "would delete" ||
    item.action === "update" ||
    item.action === "would update",
  );
}

function planPath(
  actions: WriteAction[],
  path: string,
  options: {
    action: string;
    safe: boolean;
    unmanagedDetail: string;
    managedDetail: string;
  },
): void {
  if (!existsSync(path)) {
    return;
  }
  actions.push({
    path,
    action: options.safe ? options.action : "skip",
    detail: options.safe ? options.managedDetail : options.unmanagedDetail,
  });
}

function isManagedClaudeMd(path: string): boolean {
  if (!existsSync(path)) {
    return false;
  }
  return missingClaudeSnippets(path).length === 0 && readFileSync(path, "utf8").includes("## Claude Code");
}

function isAgentFeedAgentsMd(path: string): boolean {
  if (!existsSync(path)) {
    return false;
  }
  const text = readFileSync(path, "utf8");
  return (
    text.includes("AI Development Instructions") &&
    text.includes("repository-level entry contract") &&
    text.includes(".agents/rules/outcome-boundary.md")
  );
}

function isAgentFeedAgentsDir(path: string): boolean {
  const readme = join(path, "README.md");
  return (
    existsSync(path) &&
    existsSync(readme) &&
    readFileSync(readme, "utf8").includes("# AI Development Engineering") &&
    existsSync(join(path, "rules", "outcome-boundary.md")) &&
    existsSync(join(path, "scripts", "check-agent-assets.sh"))
  );
}

function sameTree(left: string, right: string): boolean {
  if (!existsSync(left) || !existsSync(right)) {
    return false;
  }
  const leftFiles = walkTree(left).filter((item) => statSync(item).isFile());
  const rightFiles = walkTree(right).filter((item) => statSync(item).isFile());
  const leftRel = leftFiles.map((item) => item.slice(left.length + 1)).sort();
  const rightRel = rightFiles.map((item) => item.slice(right.length + 1)).sort();
  if (leftRel.join("\n") !== rightRel.join("\n")) {
    return false;
  }
  return leftRel.every(
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

function projectTrustUninstallPlan(root: string, dryRun: boolean): WriteAction[] {
  const report = checkAssetTrust(root);
  if (!report.configPath || report.errors.length > 0 || report.missingState) {
    return [];
  }
  const configText = readFileSync(report.configPath, "utf8");
  const parsed = JSON.parse(configText) as { projects?: Record<string, unknown> };
  const projects = parsed.projects;
  const key = resolve(root);
  if (!projects || typeof projects !== "object" || Array.isArray(projects) || !(key in projects)) {
    return [];
  }
  return [
    {
      path: report.configPath,
      action: dryRun ? "would update" : "update",
      detail: "remove external trust state for this project",
    },
  ];
}

function removeProjectTrustState(root: string, configPath: string): void {
  const parsed = JSON.parse(readFileSync(configPath, "utf8")) as { projects?: Record<string, unknown> };
  if (parsed.projects && typeof parsed.projects === "object" && !Array.isArray(parsed.projects)) {
    delete parsed.projects[resolve(root)];
  }
  writeFileSync(configPath, `${JSON.stringify(parsed, null, 2)}\n`, "utf8");
}

function removeEmptyParents(path: string): void {
  let current = path;
  while (["rules", ".cursor", ".claude", ".codex"].includes(basename(current))) {
    try {
      rmdirSync(current);
    } catch {
      return;
    }
    current = dirname(current);
  }
}
