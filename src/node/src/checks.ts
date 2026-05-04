import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { checkAdapters } from "./adapters.js";
import { checkConfig, validateConfigData } from "./config.js";
import { skillIndexErrors } from "./skill-index.js";
import { assetTrustErrors } from "./trust.js";

export type CheckReport = {
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
  ".agents/project/README.md",
  ".agents/domain/README.md",
  ".agents/skills",
  ".agents/skills/README.md",
  ".agents/scripts/verify-agent-dev.sh",
];

export function runChecks(root: string): CheckReport {
  const errors = validateStructure(root);
  const warnings: string[] = [];
  const configReport = checkConfig(root);
  errors.push(...configReport.errors);
  warnings.push(...configReport.warnings);
  errors.push(...skillIndexErrors(root));
  errors.push(...assetTrustErrors(root));
  const adapterReport = checkAdapters(root);
  errors.push(...adapterReport.errors);
  warnings.push(...adapterReport.warnings);
  return { errors, warnings };
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
