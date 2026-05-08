#!/usr/bin/env node
import { existsSync } from "node:fs";
import { dirname, join, delimiter } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const packageRoot = dirname(scriptDir);
const args = process.argv.slice(2);
const runtimeEnv = {
  ...process.env,
  AGENT_FEED_INSTALL_SOURCE: process.env.AGENT_FEED_INSTALL_SOURCE || "npm",
};

const sourceCli = join(packageRoot, "src", "agent_feed", "cli.py");
const sourceRoot = join(packageRoot, "src");
const venvPython = process.platform === "win32"
  ? join(packageRoot, ".agent-feed-python", "Scripts", "python.exe")
  : join(packageRoot, ".agent-feed-python", "bin", "python");

function pythonCandidates() {
  const candidates = [];
  const localVenvPython = process.platform === "win32"
    ? join(packageRoot, ".venv", "Scripts", "python.exe")
    : join(packageRoot, ".venv", "bin", "python");
  if (existsSync(localVenvPython)) {
    candidates.push({ command: localVenvPython, prefix: [] });
  }
  if (process.env.AGENT_FEED_PYTHON) {
    candidates.push({ command: process.env.AGENT_FEED_PYTHON, prefix: [] });
  }
  candidates.push({ command: "python3", prefix: [] });
  candidates.push({ command: "python", prefix: [] });
  if (process.platform === "win32") {
    candidates.push({ command: "py", prefix: ["-3"] });
  }
  return candidates;
}

function run(command, commandArgs, env = runtimeEnv) {
  const result = spawnSync(command, commandArgs, {
    stdio: "inherit",
    env,
  });
  if (result.error) {
    console.error(`agent-feed npm wrapper failed to run ${command}: ${result.error.message}`);
    process.exit(1);
  }
  process.exit(result.status ?? 1);
}

function canImport(candidate, env = runtimeEnv) {
  const result = spawnSync(
    candidate.command,
    [...candidate.prefix, "-c", "import agent_feed.cli"],
    { stdio: "ignore", env },
  );
  return result.status === 0;
}

if (existsSync(sourceCli)) {
  const env = {
    ...runtimeEnv,
    PYTHONPATH: process.env.PYTHONPATH
      ? `${sourceRoot}${delimiter}${process.env.PYTHONPATH}`
      : sourceRoot,
  };
  const candidate = pythonCandidates().find((item) => canImport(item, env));
  if (candidate) {
    run(candidate.command, [...candidate.prefix, "-m", "agent_feed.cli", ...args], env);
  }
}

if (existsSync(venvPython)) {
  run(venvPython, ["-m", "agent_feed.cli", ...args], runtimeEnv);
}

const candidate = pythonCandidates().find((item) => canImport(item, runtimeEnv));
if (candidate) {
  run(candidate.command, [...candidate.prefix, "-m", "agent_feed.cli", ...args], runtimeEnv);
}

console.error("Agent Feed npm wrapper could not find the Python Agent Feed package.");
console.error("Run `npm install -g agent-feed` again, or install the Python CLI directly with `uv tool install agent-feed`.");
process.exit(1);
