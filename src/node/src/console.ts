import { stderr, stdout } from "node:process";

import chalk from "chalk";
import Table from "cli-table3";

import type { CheckReport, ProjectStatus } from "./checks.js";
import type { ConfigCheckReport } from "./config.js";
import type { WriteAction } from "./template.js";
import { VERSION } from "./version.js";

type Stream = "stdout" | "stderr";
type Colorizer = (value: string) => string;

export function printWelcome(): void {
  const logo = `${chalk.bold.cyan("AGENT")}\n${chalk.bold.green("FEED")}`;
  const body = [
    `${chalk.bold.white("Agent Feed")}`,
    chalk.dim("A source-controlled workflow pipeline for AI coding agents."),
    "",
    `${chalk.bold("Start")}    ${command("agent-feed init")}`,
    `${chalk.bold("Verify")}   ${command("agent-feed check")}`,
    `${chalk.bold("Inspect")}  ${command("agent-feed status")}`,
    `${chalk.bold("Preview")}  ${command("agent-feed preview")}`,
  ].join("\n");
  printBox({
    title: `agent-feed ${VERSION}`,
    body: sideBySide(logo, body, 4),
    color: chalk.cyan,
  });
}

export function printErrorPanel(title: string, errors: string[], stream: Stream = "stderr"): void {
  const rows = errors.map((error) => `${chalk.bold.red("!")} ${styleMessage(error)}`);
  printBox({ title, body: rows.join("\n"), color: chalk.red, stream });
}

export function printWritePlan(actions: WriteAction[], options: { showDiffs?: boolean; title?: string } = {}): void {
  const table = new Table({
    head: ["", "Action", "Path", "Detail"].map((item) => chalk.bold(item)),
    style: { head: [], border: ["gray"] },
    wordWrap: false,
  });
  for (const action of actions) {
    table.push([
      actionIcon(action),
      styledAction(action),
      displayPath(action.path),
      chalk.dim(action.detail ?? ""),
    ]);
  }
  const title = options.title ?? writePlanTitle(actions);
  stdout.write(`${chalk.bold(title)}\n${table.toString()}\n`);
  if (options.showDiffs) {
    printDiffDetails(actions);
  }
}

export function hasDiffDetails(actions: WriteAction[]): boolean {
  return actions.some((action) => Boolean(action.diff));
}

export function printDiffDetails(actions: WriteAction[]): void {
  for (const action of actions) {
    if (!action.diff) {
      continue;
    }
    printBox({
      title: `Diff: ${displayPath(action.path)}`,
      body: renderDiff(action.diff),
      color: chalk.yellow,
    });
  }
}

export function renderDiff(diff: string): string {
  return diff
    .split(/\r?\n/)
    .map((line) => diffLineStyle(line)(line))
    .join("\n");
}

export function printCheckReport(report: CheckReport, options: { asJson: boolean }): void {
  if (options.asJson) {
    stdout.write(`${JSON.stringify(report, null, 2)}\n`);
    return;
  }
  if (report.ok && report.warnings.length === 0) {
    printBox({
      title: "Agent Feed",
      body: [
        chalk.bold.green("Checks passed"),
        `${chalk.dim("Target")} ${displayPath(report.target)}`,
        `${chalk.dim("Scope")}  ${report.checks.join(", ")}`,
      ].join("\n"),
      color: chalk.green,
    });
    return;
  }
  const rows = [
    ...report.errors.map((message) => ["!", chalk.red("error"), styleMessage(message)]),
    ...report.warnings.map((message) => ["?", chalk.yellow("warning"), styleMessage(message)]),
  ];
  printDiagnostics(report.ok ? "Checks Passed With Warnings" : "Checks blocked", rows, report.ok ? "stdout" : "stderr");
  printNextStep(checkNextStep(report.errors, report.warnings), report.ok ? "stdout" : "stderr");
}

export function printConfigCheckReport(report: ConfigCheckReport): void {
  if (report.errors.length === 0 && report.warnings.length === 0) {
    printBox({
      title: "Agent Feed",
      body: chalk.bold.green("Config checks passed"),
      color: chalk.green,
    });
    return;
  }
  const rows = [
    ...report.errors.map((message) => ["!", chalk.red("error"), styleMessage(message)]),
    ...report.warnings.map((message) => ["?", chalk.yellow("warning"), styleMessage(message)]),
  ];
  printDiagnostics("Config Diagnostics", rows, report.errors.length > 0 ? "stderr" : "stderr");
  printNextStep(configNextStep(report.errors, report.warnings), "stderr");
}

export function printStatus(status: ProjectStatus, options: { asJson: boolean }): void {
  if (options.asJson) {
    stdout.write(`${JSON.stringify(status, null, 2)}\n`);
    return;
  }
  const table = new Table({
    head: ["Area", "Source", "State"].map((item) => chalk.bold(item)),
    style: { head: [], border: ["gray"] },
    wordWrap: false,
  });
  table.push(
    ["Canonical", "AGENTS.md + .agents/", state(status.canonical_installed)],
    ["Codex", "AGENTS.md + .agents/skills (direct)", state(status.codex_ready)],
    ["Claude", "CLAUDE.md + .claude/skills (generated)", state(status.claude_ready)],
    ["Cursor", ".cursor/rules/agent-feed.mdc (generated)", state(status.cursor_ready)],
  );
  stdout.write(`${chalk.bold(`Agent Feed Status: ${displayPath(status.target)}`)}\n${table.toString()}\n`);
  if (status.errors.length > 0 || status.warnings.length > 0) {
    printDiagnostics(
      "Diagnostics",
      [
        ...status.errors.map((message) => ["!", chalk.red("error"), styleMessage(message)]),
        ...status.warnings.map((message) => ["?", chalk.yellow("warning"), styleMessage(message)]),
      ],
      status.errors.length > 0 ? "stderr" : "stdout",
    );
  }
  printNextStep(statusNextStep(status));
}

export function printInspectionPlan(target: string, actions: WriteAction[], interactive: boolean): void {
  printWritePlan(actions, { title: `Agent Feed Inspection: ${displayPath(target)}` });
  if (!hasDiffDetails(actions)) {
    return;
  }
  printDiffHint({
    command: `agent-feed preview ${target}`,
    interactive,
  });
}

export function printDiffHint(options: { command: string; interactive: boolean }): void {
  if (options.interactive) {
    stdout.write(
      `${chalk.bold.cyan("Diff details:")} press ${chalk.bold.green("v")} to show all diffs, or press any other key to exit. Script mode: ${command(options.command)}.\n`,
    );
    return;
  }
  stdout.write(`${chalk.bold.cyan("Diff details:")} rerun ${command(options.command)}.\n`);
}

export function printActionResult(options: {
  title: string;
  message: string;
  kind?: "success" | "warning" | "error" | "info";
  detail?: string;
}): void {
  const color =
    options.kind === "success"
      ? chalk.green
      : options.kind === "warning"
        ? chalk.yellow
        : options.kind === "error"
          ? chalk.red
          : chalk.cyan;
  const stream = options.kind === "error" ? "stderr" : "stdout";
  const body = [chalk.bold(color(options.message)), options.detail ? chalk.dim(styleMessage(options.detail)) : ""]
    .filter(Boolean)
    .join("\n");
  printBox({ title: options.title, body, color, stream });
}

export function printPanel(
  title: string,
  body: string,
  options: { kind?: "success" | "warning" | "error" | "info"; stream?: Stream } = {},
): void {
  const color =
    options.kind === "success"
      ? chalk.green
      : options.kind === "warning"
        ? chalk.yellow
        : options.kind === "error"
          ? chalk.red
          : chalk.cyan;
  printBox({ title, body, color, stream: options.stream });
}

export function printRecommendedCommand(message: string, value: string, options: { path?: string } = {}): void {
  const pieces = [chalk.bold.cyan(message)];
  if (options.path) {
    pieces.push(" Edit ", pathStyle(options.path), ", then run ");
  } else {
    pieces.push(" Run ");
  }
  pieces.push(command(value), ".");
  stdout.write(`${pieces.join("")}\n`);
}

export function printWarning(message: string, stream: Stream = "stderr"): void {
  write(stream, `${chalk.bold.yellow("Warning:")} ${styleMessage(message)}\n`);
}

export function printInfo(message: string): void {
  stdout.write(`${styleMessage(message)}\n`);
}

export function printNextStep(message: string, stream: Stream = "stdout"): void {
  write(stream, `${chalk.bold.cyan("Next:")} ${styleMessage(message)}\n`);
}

export function styleMessage(message: string): string {
  let styled = message.replace(/`([^`]+)`/g, (_match, value: string) => command(value));
  styled = styled.replace(/((?:\.{1,2}|~|\/|[A-Za-z]:\\)[^\s,;:]+|[A-Za-z0-9_.-]+\/[^\s,;:]+)/g, (match) => {
    if (match.includes("\u001B[")) {
      return match;
    }
    return pathStyle(match);
  });
  return styled;
}

export function command(value: string): string {
  return chalk.bold.green(value);
}

export function pathStyle(value: string): string {
  return chalk.italic.blue(value);
}

function printDiagnostics(title: string, rows: string[][], stream: Stream): void {
  const table = new Table({
    head: ["", "Type", "Message"].map((item) => chalk.bold(item)),
    style: { head: [], border: ["gray"] },
    wordWrap: false,
  });
  for (const row of rows) {
    table.push(row);
  }
  write(stream, `${chalk.bold(title)}\n${table.toString()}\n`);
}

function writePlanTitle(actions: WriteAction[]): string {
  if (actions.length === 0) {
    return "No Changes";
  }
  if (actions.some((action) => actionSeverity(action) === "warning")) {
    return "Review Required";
  }
  if (actions.some((action) => actionSeverity(action) === "preview")) {
    return "Preview";
  }
  return "Changes";
}

function actionIcon(action: WriteAction): string {
  const severity = actionSeverity(action);
  if (severity === "warning") {
    return chalk.bold.yellow("!");
  }
  if (severity === "preview") {
    return chalk.cyan("~");
  }
  if (severity === "success") {
    return chalk.green("+");
  }
  return chalk.dim("-");
}

function styledAction(action: WriteAction): string {
  const severity = actionSeverity(action);
  if (severity === "warning") {
    return chalk.bold.yellow(action.action);
  }
  if (severity === "preview") {
    return chalk.cyan(action.action);
  }
  if (severity === "success") {
    return chalk.green(action.action);
  }
  return chalk.dim(action.action);
}

function actionSeverity(action: WriteAction): "warning" | "preview" | "neutral" | "success" {
  const value = action.action.toLowerCase();
  if (value.includes("blocked") || value.includes("warn") || value.includes("error")) {
    return "warning";
  }
  if (value.startsWith("would")) {
    return "preview";
  }
  if (["create", "update", "sync", "delete", "backup", "ok"].includes(value)) {
    return "success";
  }
  return "neutral";
}

function displayPath(value: string): string {
  const cwd = process.cwd();
  if (value === cwd) {
    return ".";
  }
  if (value.startsWith(`${cwd}/`)) {
    return value.slice(cwd.length + 1);
  }
  return value;
}

function diffLineStyle(line: string): (value: string) => string {
  if (line.startsWith("@@")) {
    return chalk.bold.cyan;
  }
  if (line.startsWith("--- ")) {
    return chalk.bold.red;
  }
  if (line.startsWith("+++ ")) {
    return chalk.bold.green;
  }
  if (line.startsWith("-")) {
    return chalk.red;
  }
  if (line.startsWith("+")) {
    return chalk.green;
  }
  if (line.startsWith("diff ") || line.startsWith("index ")) {
    return chalk.bold;
  }
  if (line.startsWith("\\")) {
    return chalk.dim;
  }
  return (value: string) => value;
}

function state(ok: boolean): string {
  return ok ? chalk.green("ready") : chalk.red("blocked");
}

function checkNextStep(errors: string[], warnings: string[]): string {
  const diagnostics = [...errors, ...warnings].join("\n");
  if (diagnostics.includes("stale project entry")) {
    return "Run `agent-feed config prune`, then rerun `agent-feed check -a`.";
  }
  if (diagnostics.includes("AGENT_FEED_HOME") || diagnostics.includes("user-level Agent Feed config")) {
    return "Run `agent-feed env setup`, then rerun `agent-feed check -a`.";
  }
  if (errors.length > 0) {
    return "Fix the diagnostics above, then rerun `agent-feed check -a`.";
  }
  return "Review the warnings above before the final handoff.";
}

function configNextStep(errors: string[], warnings: string[]): string {
  const diagnostics = [...errors, ...warnings].join("\n");
  if (diagnostics.includes("stale project entry")) {
    return "Run `agent-feed config prune`, then rerun `agent-feed config check`.";
  }
  if (diagnostics.includes("AGENT_FEED_HOME") || diagnostics.includes("user-level Agent Feed config")) {
    return "Run `agent-feed env setup`, then rerun `agent-feed config check`.";
  }
  if (errors.length > 0) {
    return "Fix the config diagnostics above, then rerun `agent-feed config check`.";
  }
  return "Review the config warnings above.";
}

function statusNextStep(status: ProjectStatus): string {
  if (!status.canonical_installed) {
    return "Run `agent-feed init` in this project.";
  }
  if (status.errors.length > 0) {
    return "Run `agent-feed check -a` for the full failure list.";
  }
  if (status.warnings.length > 0) {
    return "Review the warnings above, then run `agent-feed preview` before updating.";
  }
  return "Run `agent-feed preview` to inspect managed drift before updating.";
}

function printBox(options: {
  title: string;
  body: string;
  color: Colorizer;
  stream?: Stream;
}): void {
  const lines = options.body.split("\n");
  const width = Math.max(
    stripAnsi(options.title).length + 4,
    ...lines.map((line) => stripAnsi(line).length + 4),
  );
  const top = `${options.color("╭")}${options.color("─".repeat(width - 2))}${options.color("╮")}`;
  const title = ` ${options.title} `;
  const titleLine = `${options.color("│")}${center(title, width - 2)}${options.color("│")}`;
  const bottom = `${options.color("╰")}${options.color("─".repeat(width - 2))}${options.color("╯")}`;
  const body = lines
    .map((line) => `${options.color("│")} ${line}${" ".repeat(width - stripAnsi(line).length - 3)}${options.color("│")}`)
    .join("\n");
  write(options.stream ?? "stdout", `${top}\n${titleLine}\n${body}\n${bottom}\n`);
}

function sideBySide(left: string, right: string, gap: number): string {
  const leftLines = left.split("\n");
  const rightLines = right.split("\n");
  const leftWidth = Math.max(...leftLines.map((line) => stripAnsi(line).length));
  const height = Math.max(leftLines.length, rightLines.length);
  const rows: string[] = [];
  for (let index = 0; index < height; index += 1) {
    const leftLine = leftLines[index] ?? "";
    const rightLine = rightLines[index] ?? "";
    rows.push(`${leftLine}${" ".repeat(leftWidth - stripAnsi(leftLine).length + gap)}${rightLine}`);
  }
  return rows.join("\n");
}

function center(value: string, width: number): string {
  const visible = stripAnsi(value).length;
  const padding = Math.max(width - visible, 0);
  const left = Math.floor(padding / 2);
  const right = padding - left;
  return `${" ".repeat(left)}${value}${" ".repeat(right)}`;
}

function write(stream: Stream, value: string): void {
  (stream === "stderr" ? stderr : stdout).write(value);
}

function stripAnsi(value: string): string {
  return value.replace(/\u001B\[[0-9;]*m/g, "");
}
