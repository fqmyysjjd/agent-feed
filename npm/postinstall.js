#!/usr/bin/env node
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const packageRoot = dirname(scriptDir);
const sourceCli = join(packageRoot, "src", "agent_feed", "cli.py");

if (existsSync(sourceCli) && existsSync(join(packageRoot, "pyproject.toml"))) {
  console.log("agent-feed npm postinstall: source checkout detected; skipping Python runtime bootstrap.");
  process.exit(0);
}

const packageJson = JSON.parse(readFileSync(join(packageRoot, "package.json"), "utf8"));
const venvDir = join(packageRoot, ".agent-feed-python");
const venvPython = process.platform === "win32"
  ? join(venvDir, "Scripts", "python.exe")
  : join(venvDir, "bin", "python");

function pythonCandidates() {
  const candidates = [];
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

function isUsable(candidate) {
  const result = spawnSync(
    candidate.command,
    [...candidate.prefix, "-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"],
    { stdio: "ignore" },
  );
  return result.status === 0;
}

function run(command, args) {
  const result = spawnSync(command, args, { stdio: "inherit" });
  if (result.error) {
    throw new Error(result.error.message);
  }
  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(" ")} exited with ${result.status}`);
  }
}

try {
  const python = pythonCandidates().find(isUsable);
  if (!python) {
    throw new Error("Python 3.11 or newer is required.");
  }

  if (!existsSync(venvPython)) {
    run(python.command, [...python.prefix, "-m", "venv", venvDir]);
  }
  run(venvPython, ["-m", "pip", "install", `agent-feed==${packageJson.version}`]);
} catch (error) {
  console.error("agent-feed npm postinstall failed to bootstrap the Python runtime.");
  console.error(error instanceof Error ? error.message : String(error));
  console.error("You can install Agent Feed directly with `uv tool install agent-feed` or `pipx install agent-feed`.");
  process.exit(1);
}
