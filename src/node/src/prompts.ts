import { clearLine, emitKeypressEvents, moveCursor } from "node:readline";
import { stdin, stdout } from "node:process";

import { checkbox, confirm, input, password, select } from "@inquirer/prompts";
import chalk from "chalk";

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

export async function promptPathStep(message: string, fallback: string): Promise<string | undefined> {
  return promptOrCancel(() =>
    input({
      message,
      default: fallback,
    }),
  );
}

export async function promptText(message: string, fallback: string): Promise<string> {
  return input({
    message,
    default: fallback,
  });
}

export async function promptTextStep(message: string, fallback: string): Promise<string | undefined> {
  return promptOrCancel(() =>
    input({
      message,
      default: fallback,
    }),
  );
}

export async function promptConfirm(message: string, fallback = false): Promise<boolean> {
  return confirm({
    message,
    default: fallback,
  });
}

export async function promptSecret(message: string): Promise<string> {
  return (
    (await promptOrCancel(() =>
      password({
        message,
        mask: "*",
      }),
    )) ?? ""
  );
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

export async function promptClientsStep(message: string, defaults: readonly Client[]): Promise<Client[] | undefined> {
  return promptOrCancel(() => promptClients(message, defaults));
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

export async function promptVerificationProfileStep(
  message: string,
  fallback: VerificationProfile,
): Promise<VerificationProfile | undefined> {
  return promptOrCancel(() => promptVerificationProfile(message, fallback));
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

export async function promptSkillKeyword(fallback = ""): Promise<string | undefined> {
  return promptOrCancel(() =>
    input({
      message: "Search curated skill hubs",
      default: fallback || undefined,
    }),
  );
}

export async function promptSkillSelection(
  skills: RemoteSkill[],
  options: { onPreview?: (skill: RemoteSkill) => Promise<void> | void } = {},
): Promise<RemoteSkill[] | undefined> {
  if (!canPrompt()) {
    return skills;
  }
  return interactiveSkillSelection(skills, options);
}

export async function promptViewDiffKey(): Promise<boolean> {
  const key = await readSingleKey();
  return key.toLowerCase() === "v";
}

export function isPromptCanceled(error: unknown): boolean {
  return error instanceof Error && error.name === "ExitPromptError";
}

async function promptOrCancel<T>(fn: () => Promise<T>): Promise<T | undefined> {
  try {
    return await fn();
  } catch (error) {
    if (isPromptCanceled(error)) {
      return undefined;
    }
    throw error;
  }
}

async function readSingleKey(): Promise<string> {
  if (!canPrompt()) {
    return "";
  }
  const previousRaw = stdin.isRaw;
  return new Promise((resolve) => {
    const onData = (chunk: Buffer) => {
      cleanup();
      stdout.write("\n");
      resolve(chunk.toString("utf8"));
    };
    const cleanup = () => {
      stdin.off("data", onData);
      if (stdin.setRawMode) {
        stdin.setRawMode(Boolean(previousRaw));
      }
      stdin.pause();
    };
    if (stdin.setRawMode) {
      stdin.setRawMode(true);
    }
    stdin.resume();
    stdin.once("data", onData);
  });
}

async function interactiveSkillSelection(
  skills: RemoteSkill[],
  options: { onPreview?: (skill: RemoteSkill) => Promise<void> | void },
): Promise<RemoteSkill[] | undefined> {
  let cursor = 0;
  const selected = new Set<number>();
  let renderedLines = 0;
  let busy = false;
  const previousRaw = stdin.isRaw;

  const render = () => {
    clearRenderedLines(renderedLines);
    const windowSize = 12;
    const start = Math.min(Math.max(cursor - Math.floor(windowSize / 2), 0), Math.max(skills.length - windowSize, 0));
    const visible = skills.slice(start, start + windowSize);
    const lines = [
      `${chalk.cyan("?")} ${chalk.bold("Select skills to install")}`,
      chalk.dim("Space select, v preview, Enter install, Esc back"),
      chalk.dim("Tip: v fetches and previews the highlighted skill; Cmd/Ctrl-click source URLs when supported."),
      ...visible.map((skill, offset) => {
        const index = start + offset;
        const pointer = index === cursor ? chalk.cyan(">") : " ";
        const marker = selected.has(index) ? chalk.green("●") : chalk.dim("○");
        const name = index === cursor ? chalk.bold(skill.name) : skill.name;
        return `${pointer} ${marker} ${name} ${chalk.dim(skill.hub.name)} ${chalk.dim(skill.description)}`;
      }),
    ];
    if (skills.length > windowSize) {
      lines.push(chalk.dim(`Showing ${start + 1}-${start + visible.length} of ${skills.length}. Narrow the keyword to see fewer.`));
    }
    stdout.write(`${lines.join("\n")}\n`);
    renderedLines = lines.length;
  };

  return new Promise((resolve, reject) => {
    const cleanup = () => {
      stdin.off("keypress", onKeypress);
      if (stdin.setRawMode) {
        stdin.setRawMode(Boolean(previousRaw));
      }
      stdin.pause();
      clearRenderedLines(renderedLines);
      stdout.write("\u001B[?25h");
    };

    const finish = (value: RemoteSkill[] | undefined) => {
      cleanup();
      resolve(value);
    };

    const previewCurrent = async () => {
      if (!options.onPreview || busy) {
        return;
      }
      busy = true;
      clearRenderedLines(renderedLines);
      renderedLines = 0;
      if (stdin.setRawMode) {
        stdin.setRawMode(false);
      }
      try {
        await options.onPreview(skills[cursor]);
      } catch (error) {
        cleanup();
        reject(error);
        return;
      } finally {
        if (stdin.setRawMode) {
          stdin.setRawMode(true);
        }
        busy = false;
      }
      render();
    };

    const onKeypress = (_input: string, key: { name?: string; sequence?: string; ctrl?: boolean }) => {
      if (busy) {
        return;
      }
      if (key.ctrl && key.name === "c") {
        finish(undefined);
        return;
      }
      if (key.name === "escape") {
        finish(undefined);
        return;
      }
      if (key.name === "return") {
        finish([...selected].sort((left, right) => left - right).map((index) => skills[index]));
        return;
      }
      if (key.name === "space") {
        if (selected.has(cursor)) {
          selected.delete(cursor);
        } else {
          selected.add(cursor);
        }
        render();
        return;
      }
      if (key.name === "up") {
        cursor = (cursor - 1 + skills.length) % skills.length;
        render();
        return;
      }
      if (key.name === "down") {
        cursor = (cursor + 1) % skills.length;
        render();
        return;
      }
      if ((key.sequence ?? "").toLowerCase() === "v") {
        void previewCurrent();
      }
    };

    emitKeypressEvents(stdin);
    stdout.write("\u001B[?25l");
    if (stdin.setRawMode) {
      stdin.setRawMode(true);
    }
    stdin.resume();
    stdin.on("keypress", onKeypress);
    render();
  });
}

function clearRenderedLines(count: number): void {
  if (count <= 0) {
    return;
  }
  moveCursor(stdout, 0, -count);
  for (let index = 0; index < count; index += 1) {
    clearLine(stdout, 0);
    if (index < count - 1) {
      moveCursor(stdout, 0, 1);
    }
  }
  moveCursor(stdout, 0, -(count - 1));
}
