import { stdin, stdout } from "node:process";

import { checkbox, confirm, input, password, select } from "@inquirer/prompts";

import { ALL_CHECKS, type CheckName } from "./checks.js";
import type { Client } from "./adapters.js";
import type { RemoteSkill } from "./skill-hub.js";
import type { VerificationProfile } from "./template.js";

export function canPrompt(): boolean {
  return Boolean(stdin.isTTY && stdout.isTTY);
}

export async function promptPath(message: string, fallback: string): Promise<string> {
  return input({
    message,
    default: fallback,
  });
}

export async function promptText(message: string, fallback: string): Promise<string> {
  return input({
    message,
    default: fallback,
  });
}

export async function promptConfirm(message: string, fallback = false): Promise<boolean> {
  return confirm({
    message,
    default: fallback,
  });
}

export async function promptSecret(message: string): Promise<string> {
  return password({
    message,
    mask: "*",
  });
}

export async function promptClients(message: string, defaults: readonly Client[]): Promise<Client[]> {
  const selected = await checkbox<Client>({
    message,
    choices: [
      { name: "Codex", value: "codex", checked: defaults.includes("codex") },
      { name: "Claude Code", value: "claude", checked: defaults.includes("claude") },
      { name: "Cursor", value: "cursor", checked: defaults.includes("cursor") },
    ],
    required: false,
    pageSize: 6,
  });
  return selected;
}

export async function promptChecks(defaults: readonly CheckName[]): Promise<CheckName[]> {
  const selected = await checkbox<CheckName>({
    message: "Select checks to run",
    choices: ALL_CHECKS.map((check) => ({
      name: check,
      value: check,
      checked: defaults.includes(check),
    })),
    required: false,
    pageSize: ALL_CHECKS.length,
  });
  return selected;
}

export async function promptVerificationProfile(
  message: string,
  fallback: VerificationProfile,
): Promise<VerificationProfile> {
  return select<VerificationProfile>({
    message,
    default: fallback,
    choices: [
      { name: "Python", value: "python", description: "Use pytest/ruff/mypy oriented verification." },
      { name: "Node", value: "node", description: "Use npm/TypeScript oriented verification." },
      { name: "Custom", value: "custom", description: "Require project-owned verification commands." },
      { name: "None", value: "none", description: "Install no code verification profile." },
    ],
    pageSize: 4,
  });
}

export async function promptMainAction(): Promise<string> {
  return select<string>({
    message: "What do you want to do?",
    choices: [
      { name: "Initialize protocol", value: "init", description: "Install AGENTS.md and .agents/." },
      { name: "Check project", value: "check", description: "Validate protocol and adapters." },
      { name: "Inspect status", value: "status", description: "Show managed drift and next steps." },
      { name: "Preview changes", value: "preview", description: "Show full managed diffs." },
      { name: "Sync adapters", value: "sync", description: "Update Claude/Cursor adapters." },
      { name: "Configure environment", value: "env", description: "Set AGENT_FEED_HOME." },
    ],
  });
}

export async function promptSkillKeyword(fallback = ""): Promise<string> {
  return input({
    message: "Search curated skill hubs",
    default: fallback || undefined,
  });
}

export async function promptSkillSelection(skills: RemoteSkill[]): Promise<RemoteSkill[]> {
  const selected = await checkbox<string>({
    message: "Select skills to install (space selects, enter installs; use --dry-run to preview file writes first)",
    choices: skills.map((skill, index) => ({
      name: `${skill.name} (${skill.hub.name})`,
      value: String(index),
      description: skill.description,
    })),
    required: false,
    pageSize: Math.min(Math.max(skills.length, 6), 12),
  });
  return selected.map((value) => skills[Number.parseInt(value, 10)]).filter(Boolean);
}

export function isPromptCanceled(error: unknown): boolean {
  return error instanceof Error && error.name === "ExitPromptError";
}
