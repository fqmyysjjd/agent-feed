import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const cliPath = join(process.cwd(), "dist-node", "src", "cli.js");

function withTrustEnv(): { AGENT_FEED_HOME: string } {
  return { AGENT_FEED_HOME: mkdtempSync(join(tmpdir(), "agent-feed-home-")) };
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

test("version command works", () => {
  const result = spawnSync(process.execPath, [cliPath, "--version"], { encoding: "utf8" });
  assert.equal(result.status, 0);
  assert.match(result.stdout, /1\.0\.0/);
});

test("init dry-run prints planned files", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const result = spawnSync(process.execPath, [cliPath, "init", target, "--dry-run"], {
    encoding: "utf8",
  });
  assert.equal(result.status, 0);
  assert.match(result.stdout, /AGENTS\.md/);
});

test("subcommand help does not execute the command", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const result = spawnSync(process.execPath, [cliPath, "init", "--help"], {
    cwd: target,
    encoding: "utf8",
  });
  assert.equal(result.status, 0);
  assert.match(result.stdout, /Usage:/);
  assert.equal(existsSync(join(target, "AGENTS.md")), false);
});

test("init writes canonical files", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const result = spawnSync(process.execPath, [cliPath, "init", target], {
    encoding: "utf8",
    env: { ...process.env, ...withTrustEnv() },
  });
  assert.equal(result.status, 0);
  const agents = readFileSync(join(target, "AGENTS.md"), "utf8");
  const metadata = JSON.parse(readFileSync(join(target, ".agents", "agent-feed.json"), "utf8")) as {
    agent_feed_version?: unknown;
    verification_profile?: unknown;
  };
  assert.match(agents, /Agent Feed/);
  assert.equal(metadata.agent_feed_version, "1.0.0");
  assert.equal(metadata.verification_profile, "none");
});

test("init preflights adapter conflicts before writing canonical files", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  writeFileSync(join(target, "CLAUDE.md"), "existing project instructions\n", "utf8");
  const result = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "claude"], {
    encoding: "utf8",
  });
  assert.equal(result.status, 3);
  assert.match(result.stderr, /CLAUDE\.md is missing required Agent Feed references/);
  assert.equal(existsSync(join(target, "AGENTS.md")), false);
  assert.equal(existsSync(join(target, ".agents")), false);
});

test("sync dry-run previews adapter writes", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none"], {
    encoding: "utf8",
    env: { ...process.env, ...withTrustEnv() },
  });
  assert.equal(init.status, 0, init.stdout + init.stderr);

  const result = spawnSync(
    process.execPath,
    [cliPath, "sync", target, "--clients", "claude,cursor", "--dry-run"],
    { encoding: "utf8" },
  );
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, /\.claude\/skills/);
  assert.match(result.stdout, /\.cursor\/rules\/agent-feed\.mdc/);
});

test("sync does not write adapters before init", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const result = spawnSync(process.execPath, [cliPath, "sync", target, "--clients", "cursor"], {
    encoding: "utf8",
  });
  assert.equal(result.status, 3);
  assert.match(result.stderr, /missing \.agents/);
  assert.throws(() => readFileSync(join(target, ".cursor", "rules", "agent-feed.mdc"), "utf8"));
});

test("sync dry-run is blocked before init", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const result = spawnSync(
    process.execPath,
    [cliPath, "sync", target, "--clients", "cursor", "--dry-run"],
    { encoding: "utf8" },
  );
  assert.equal(result.status, 3);
  assert.match(result.stderr, /missing \.agents/);
});

test("claude skill mirror removes stale files on sync", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "claude"], {
    encoding: "utf8",
    env,
  });
  assert.equal(init.status, 0, init.stdout + init.stderr);

  const stale = join(target, ".claude", "skills", "stale-skill", "SKILL.md");
  mkdirSync(join(target, ".claude", "skills", "stale-skill"), { recursive: true });
  writeFileSync(stale, "---\nname: stale-skill\n---\n", "utf8");

  const result = spawnSync(process.execPath, [cliPath, "sync", target, "--clients", "claude"], { encoding: "utf8", env });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.equal(existsSync(stale), false);
});

test("preview shows canonical upgrade diff", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none"], {
    encoding: "utf8",
    env,
  });
  assert.equal(init.status, 0, init.stdout + init.stderr);

  const agentsPath = join(target, "AGENTS.md");
  writeFileSync(agentsPath, `${readFileSync(agentsPath, "utf8")}\nextra drift\n`, "utf8");

  const result = spawnSync(process.execPath, [cliPath, "preview", target], { encoding: "utf8", env });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, /would update/);
  assert.match(result.stdout, /AGENTS\.md/);
  assert.match(result.stdout, /--- AGENTS\.md \(current\)/);
});

test("status reports managed drift", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none"], {
    encoding: "utf8",
    env,
  });
  assert.equal(init.status, 0, init.stdout + init.stderr);

  const agentsPath = join(target, "AGENTS.md");
  writeFileSync(agentsPath, `${readFileSync(agentsPath, "utf8")}\nextra drift\n`, "utf8");

  const result = spawnSync(process.execPath, [cliPath, "status", target], { encoding: "utf8", env });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, /Managed drift: 1 change\(s\)/);
  assert.match(result.stdout, /Next: run agent-feed preview/);
});

test("upgrade updates managed canonical files but keeps user-maintained project files", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none"], {
    encoding: "utf8",
    env,
  });
  assert.equal(init.status, 0, init.stdout + init.stderr);

  const agentsPath = join(target, "AGENTS.md");
  writeFileSync(agentsPath, `${readFileSync(agentsPath, "utf8")}\nextra drift\n`, "utf8");

  const projectFile = join(target, ".agents", "project", "README.md");
  const customProject = `${readFileSync(projectFile, "utf8")}\nUser project notes.\n`;
  writeFileSync(projectFile, customProject, "utf8");

  const result = spawnSync(process.execPath, [cliPath, "upgrade", target], { encoding: "utf8", env });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.doesNotMatch(readFileSync(agentsPath, "utf8"), /extra drift/);
  assert.equal(readFileSync(projectFile, "utf8"), customProject);
});

test("check reports adapter errors for missing Claude mirror", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none"], {
    encoding: "utf8",
    env,
  });
  assert.equal(init.status, 0, init.stdout + init.stderr);

  writeFileSync(join(target, "CLAUDE.md"), "@AGENTS.md\n.claude/skills\n.agents/\n", "utf8");
  mkdirSync(join(target, ".claude"), { recursive: true });

  const result = spawnSync(process.execPath, [cliPath, "check", target], { encoding: "utf8", env });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Claude adapter missing \.claude\/skills/);
});

test("init is blocked when AGENT_FEED_HOME is missing", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env };
  delete env.AGENT_FEED_HOME;
  const result = spawnSync(process.execPath, [cliPath, "init", target], { encoding: "utf8", env });
  assert.equal(result.status, 3);
  assert.match(result.stderr, /AGENT_FEED_HOME is required/);
});

test("init can create AGENT_FEED_HOME with --env-home", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const shellHome = mkdtempSync(join(tmpdir(), "agent-feed-shell-"));
  const trustHome = join(shellHome, ".agent-feed");
  const env: NodeJS.ProcessEnv = { ...process.env, HOME: shellHome, SHELL: "/bin/bash" };
  delete env.AGENT_FEED_HOME;

  const result = spawnSync(
    process.execPath,
    [cliPath, "init", target, "--clients", "none", "--env-home", trustHome],
    { encoding: "utf8", env },
  );

  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.equal(existsSync(join(target, "AGENTS.md")), true);
  assert.equal(existsSync(join(trustHome, "config.json")), true);
  assert.match(readFileSync(join(shellHome, ".bashrc"), "utf8"), /AGENT_FEED_HOME/);
});

test("env print, setup, status, and uninstall work", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const shellHome = mkdtempSync(join(tmpdir(), "agent-feed-shell-"));
  const trustHome = join(shellHome, ".agent-feed");
  const env = { ...process.env, HOME: shellHome, SHELL: "/bin/bash", AGENT_FEED_HOME: "" };

  const print = spawnSync(
    process.execPath,
    [cliPath, "env", "print", "--home", trustHome, "--shell", "bash"],
    { encoding: "utf8", env },
  );
  assert.equal(print.status, 0, print.stdout + print.stderr);
  assert.match(print.stdout, new RegExp(`export AGENT_FEED_HOME="${escapeRegExp(trustHome)}"`));

  const dryRun = spawnSync(
    process.execPath,
    [cliPath, "env", "setup", target, "--home", trustHome, "--shell", "bash", "--dry-run"],
    { encoding: "utf8", env },
  );
  assert.equal(dryRun.status, 0, dryRun.stdout + dryRun.stderr);
  assert.match(dryRun.stdout, /would create/);
  assert.equal(existsSync(join(trustHome, "config.json")), false);

  const setup = spawnSync(
    process.execPath,
    [cliPath, "env", "setup", target, "--home", trustHome, "--shell", "bash"],
    { encoding: "utf8", env },
  );
  assert.equal(setup.status, 0, setup.stdout + setup.stderr);
  assert.equal(existsSync(join(trustHome, "config.json")), true);
  assert.match(readFileSync(join(shellHome, ".bashrc"), "utf8"), /agent-feed env/);

  const status = spawnSync(process.execPath, [cliPath, "env", "status", target], {
    encoding: "utf8",
    env: { ...process.env, HOME: shellHome, SHELL: "/bin/bash", AGENT_FEED_HOME: trustHome },
  });
  assert.equal(status.status, 0, status.stdout + status.stderr);
  assert.match(status.stdout, /environment is ready/i);

  const blocked = spawnSync(
    process.execPath,
    [cliPath, "env", "uninstall", "--home", trustHome, "--shell", "bash", "--remove-home"],
    {
      encoding: "utf8",
      env: { ...process.env, HOME: shellHome, SHELL: "/bin/bash", AGENT_FEED_HOME: trustHome },
    },
  );
  assert.equal(blocked.status, 3, blocked.stdout + blocked.stderr);
  assert.match(blocked.stderr, /pass -y/);

  const uninstall = spawnSync(
    process.execPath,
    [cliPath, "env", "uninstall", "--home", trustHome, "--shell", "bash", "--remove-home", "-y"],
    {
      encoding: "utf8",
      env: { ...process.env, HOME: shellHome, SHELL: "/bin/bash", AGENT_FEED_HOME: trustHome },
    },
  );
  assert.equal(uninstall.status, 0, uninstall.stdout + uninstall.stderr);
  assert.equal(existsSync(trustHome), false);
  assert.doesNotMatch(readFileSync(join(shellHome, ".bashrc"), "utf8"), /agent-feed env/);
});

test("env setup migrates legacy external config", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const shellHome = mkdtempSync(join(tmpdir(), "agent-feed-shell-"));
  const trustHome = join(shellHome, ".agent-feed");
  const legacyPath = join(trustHome, "agent-feed.json");
  mkdirSync(trustHome, { recursive: true });
  writeFileSync(
    legacyPath,
    `${JSON.stringify(
      {
        schema_version: 1,
        agent_feed_version: "0.0.0",
        settings: { github_token: "ghp_legacy" },
        projects: {},
      },
      null,
      2,
    )}\n`,
    "utf8",
  );

  const result = spawnSync(
    process.execPath,
    [cliPath, "env", "setup", target, "--home", trustHome, "--shell", "bash"],
    {
      encoding: "utf8",
      env: { ...process.env, HOME: shellHome, SHELL: "/bin/bash", AGENT_FEED_HOME: "" },
    },
  );

  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.equal(existsSync(legacyPath), false);
  const migrated = JSON.parse(readFileSync(join(trustHome, "config.json"), "utf8")) as {
    settings?: { github_token?: string };
  };
  assert.equal(migrated.settings?.github_token, "ghp_legacy");
});

test("config get reads project config values", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none"], { encoding: "utf8", env });
  assert.equal(init.status, 0, init.stdout + init.stderr);
  const result = spawnSync(process.execPath, [cliPath, "config", "get", "verification_profile", "--path", target], {
    encoding: "utf8",
    env,
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, /none/);
});

test("config check warns about stale user-level project entries", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const trustHome = withTrustEnv().AGENT_FEED_HOME;
  const env = { ...process.env, AGENT_FEED_HOME: trustHome };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none"], { encoding: "utf8", env });
  assert.equal(init.status, 0, init.stdout + init.stderr);
  const configPath = join(trustHome, "config.json");
  const config = JSON.parse(readFileSync(configPath, "utf8")) as Record<string, unknown>;
  const projects = config.projects as Record<string, unknown>;
  projects[join(target, "missing-project")] = {
    project_root: join(target, "missing-project"),
    project_name: "Missing",
    assets: {},
  };
  writeFileSync(configPath, `${JSON.stringify(config, null, 2)}\n`, "utf8");
  const result = spawnSync(process.execPath, [cliPath, "config", "check", "--path", target], { encoding: "utf8", env });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stderr, /stale project entry/);
});

test("config prune requires -y and removes stale entries", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const trustHome = withTrustEnv().AGENT_FEED_HOME;
  const env = { ...process.env, AGENT_FEED_HOME: trustHome };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none"], { encoding: "utf8", env });
  assert.equal(init.status, 0, init.stdout + init.stderr);
  const configPath = join(trustHome, "config.json");
  const config = JSON.parse(readFileSync(configPath, "utf8")) as Record<string, unknown>;
  const staleRoot = join(target, "missing-project");
  (config.projects as Record<string, unknown>)[staleRoot] = {
    project_root: staleRoot,
    project_name: "Missing",
    assets: {},
  };
  writeFileSync(configPath, `${JSON.stringify(config, null, 2)}\n`, "utf8");

  const blocked = spawnSync(process.execPath, [cliPath, "config", "prune"], { encoding: "utf8", env });
  assert.equal(blocked.status, 3);
  assert.match(blocked.stdout + blocked.stderr, /pass -y/);

  const applied = spawnSync(process.execPath, [cliPath, "config", "prune", "-y"], { encoding: "utf8", env });
  assert.equal(applied.status, 0, applied.stdout + applied.stderr);
  const updated = JSON.parse(readFileSync(configPath, "utf8")) as Record<string, unknown>;
  assert.equal(staleRoot in (updated.projects as Record<string, unknown>), false);
});

test("config set updates skill defaults and regenerates skill index", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none"], { encoding: "utf8", env });
  assert.equal(init.status, 0, init.stdout + init.stderr);

  const skillDir = join(target, ".agents", "skills", "local-helper");
  mkdirSync(skillDir, { recursive: true });
  const skillFile = join(skillDir, "SKILL.md");
  writeFileSync(
    skillFile,
    ["---", "name: local-helper", "description: Use when testing configured defaults.", "---", "", "# Local Helper", ""].join("\n"),
    "utf8",
  );

  const result = spawnSync(
    process.execPath,
    [
      cliPath,
      "config",
      "set",
      "settings.skills",
      '{"default_import_source":"local","default_import_trust":"reviewed"}',
      "--path",
      target,
    ],
    { encoding: "utf8", env },
  );
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(readFileSync(skillFile, "utf8"), /source: local/);
  assert.match(readFileSync(skillFile, "utf8"), /trust: reviewed/);
  assert.match(readFileSync(join(target, ".agents", "skills", "README.md"), "utf8"), /\| `local-helper` \|/);
});
