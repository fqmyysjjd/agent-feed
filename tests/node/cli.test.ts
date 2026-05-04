import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const cliPath = join(process.cwd(), "dist-node", "src", "cli.js");
const skillHubModulePath = join(process.cwd(), "dist-node", "src", "skill-hub.js");

function withTrustEnv(): { AGENT_FEED_HOME: string } {
  return { AGENT_FEED_HOME: mkdtempSync(join(tmpdir(), "agent-feed-home-")) };
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

test("version command works", () => {
  const result = spawnSync(process.execPath, [cliPath, "--version"], { encoding: "utf8" });
  assert.equal(result.status, 0);
  assert.match(result.stdout, /agent-feed 1\.0\.0/);
  assert.match(result.stdout, /executable:/);
  assert.match(result.stdout, /package:/);
});

test("hidden compatibility aliases work", () => {
  const version = spawnSync(process.execPath, [cliPath, "version"], { encoding: "utf8" });
  assert.equal(version.status, 0);
  assert.match(version.stdout, /agent-feed 1\.0\.0/);

  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const init = spawnSync(process.execPath, [cliPath, "i", target, "--profile", "python", "--clients", "none"], {
    encoding: "utf8",
    env,
  });
  assert.equal(init.status, 0, init.stdout + init.stderr);

  const sync = spawnSync(process.execPath, [cliPath, "s", target, "--clients", "cursor", "--dry-run"], {
    encoding: "utf8",
    env,
  });
  assert.equal(sync.status, 0, sync.stdout + sync.stderr);
  assert.match(sync.stdout, /\.cursor\/rules\/agent-feed\.mdc/);

  const check = spawnSync(process.execPath, [cliPath, "c", target, "--checks", "structure", "--json"], {
    encoding: "utf8",
    env,
  });
  assert.equal(check.status, 0, check.stdout + check.stderr);
  assert.equal(JSON.parse(check.stdout).ok, true);
});

test("init dry-run prints planned files", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const result = spawnSync(process.execPath, [cliPath, "init", target, "--profile", "python", "--dry-run"], {
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
  const result = spawnSync(process.execPath, [cliPath, "init", target, "--profile", "python"], {
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
  assert.equal(metadata.verification_profile, "python");
});

test("init backs up unmanaged Claude instructions before writing adapter", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  writeFileSync(join(target, "CLAUDE.md"), "existing project instructions\n", "utf8");
  const result = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "claude", "--profile", "python"], {
    encoding: "utf8",
    env,
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, /backup/);
  assert.equal(existsSync(join(target, "AGENTS.md")), true);
  const backupRoot = join(target, ".feed-backup");
  assert.equal(existsSync(backupRoot), true);
  const backupDirs = readdirSync(backupRoot);
  assert.equal(backupDirs.length, 1);
  assert.equal(readFileSync(join(backupRoot, backupDirs[0], "CLAUDE.md"), "utf8"), "existing project instructions\n");
});

test("init keeps existing Claude instructions when Agent Feed references are present", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const userClaude = [
    "# Existing Claude Instructions",
    "",
    "@AGENTS.md",
    "",
    "Use `.claude/skills` and keep `.agents/` canonical.",
    "",
  ].join("\n");
  writeFileSync(join(target, "CLAUDE.md"), userClaude, "utf8");

  const result = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "claude", "--profile", "python"], {
    encoding: "utf8",
    env,
  });

  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.equal(readFileSync(join(target, "CLAUDE.md"), "utf8"), userClaude);
  assert.equal(existsSync(join(target, ".feed-backup")), false);
  assert.equal(existsSync(join(target, ".claude", "skills", "project-development", "SKILL.md")), true);
});

test("sync dry-run previews adapter writes", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none", "--profile", "python"], {
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

  const conflict = spawnSync(process.execPath, [cliPath, "sync", target, "-a", "--clients", "cursor", "--dry-run"], {
    encoding: "utf8",
  });
  assert.equal(conflict.status, 3);
  assert.match(conflict.stderr, /use either -a\/--all or --clients/);
});

test("sync dry-run can preview adapters before init", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const result = spawnSync(
    process.execPath,
    [cliPath, "sync", target, "--clients", "cursor", "--dry-run"],
    { encoding: "utf8" },
  );
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, /would create/);
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

test("claude skill mirror removes stale files on sync", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "claude", "--profile", "python"], {
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
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none", "--profile", "python"], {
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
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none", "--profile", "python"], {
    encoding: "utf8",
    env,
  });
  assert.equal(init.status, 0, init.stdout + init.stderr);

  const agentsPath = join(target, "AGENTS.md");
  writeFileSync(agentsPath, `${readFileSync(agentsPath, "utf8")}\nextra drift\n`, "utf8");

  const result = spawnSync(process.execPath, [cliPath, "status", target], { encoding: "utf8", env });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, /Agent Feed Inspection/);
  assert.match(result.stdout, /would update/);
  assert.match(result.stdout, /Diff details: rerun agent-feed preview/);
});

test("upgrade updates managed canonical files but keeps user-maintained project files", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none", "--profile", "python"], {
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

test("uninstall removes managed assets and project trust state", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--profile", "python"], {
    encoding: "utf8",
    env,
  });
  assert.equal(init.status, 0, init.stdout + init.stderr);

  const trustPath = join(env.AGENT_FEED_HOME!, "config.json");
  const before = JSON.parse(readFileSync(trustPath, "utf8")) as {
    projects?: Record<string, unknown>;
  };
  assert.equal(target in (before.projects ?? {}), true);

  const dryRun = spawnSync(process.execPath, [cliPath, "uninstall", target, "--dry-run"], {
    encoding: "utf8",
    env,
  });
  assert.equal(dryRun.status, 0, dryRun.stdout + dryRun.stderr);
  assert.match(dryRun.stdout, /would delete/);
  assert.equal(existsSync(join(target, "AGENTS.md")), true);

  const applied = spawnSync(process.execPath, [cliPath, "uninstall", target, "-y"], {
    encoding: "utf8",
    env,
  });
  assert.equal(applied.status, 0, applied.stdout + applied.stderr);
  assert.equal(existsSync(join(target, ".agents")), false);
  const after = JSON.parse(readFileSync(trustPath, "utf8")) as {
    projects?: Record<string, unknown>;
  };
  assert.equal(target in (after.projects ?? {}), false);
});

test("check reports adapter errors for missing Claude mirror", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none", "--profile", "python"], {
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
  const result = spawnSync(process.execPath, [cliPath, "init", target, "--profile", "python"], { encoding: "utf8", env });
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
    [cliPath, "init", target, "--clients", "none", "--profile", "python", "--env-home", trustHome],
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

test("init -y requires an explicit verification profile", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const result = spawnSync(process.execPath, [cliPath, "init", target, "-y", "--clients", "none"], {
    encoding: "utf8",
    env: { ...process.env, ...withTrustEnv() },
  });
  assert.equal(result.status, 3);
  assert.match(result.stderr, /choose a project verification profile explicitly/i);
  assert.equal(existsSync(join(target, "AGENTS.md")), false);
});

test("check supports explicit sub-check selection and json output", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--profile", "python", "--clients", "none"], {
    encoding: "utf8",
    env,
  });
  assert.equal(init.status, 0, init.stdout + init.stderr);

  const result = spawnSync(process.execPath, [cliPath, "check", target, "--checks", "structure,config", "--json"], {
    encoding: "utf8",
    env,
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  const payload = JSON.parse(result.stdout) as { ok: boolean; checks: string[] };
  assert.equal(payload.ok, true);
  assert.deepEqual(payload.checks, ["structure", "config"]);
});

test("status json reports trusted hash mismatch for changed managed script", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--profile", "python"], {
    encoding: "utf8",
    env,
  });
  assert.equal(init.status, 0, init.stdout + init.stderr);

  const scriptFile = join(target, ".agents", "scripts", "check-agent-assets.sh");
  writeFileSync(scriptFile, `${readFileSync(scriptFile, "utf8")}\necho unsafe-script-change\n`, "utf8");

  const result = spawnSync(process.execPath, [cliPath, "status", target, "--json"], {
    encoding: "utf8",
    env,
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  const payload = JSON.parse(result.stdout) as { errors: string[] };
  assert.match(JSON.stringify(payload.errors), /trusted hash mismatch/);
  assert.match(JSON.stringify(payload.errors), /\.agents\/scripts\/check-agent-assets\.sh/);
});

test("preview reports trusted hash mismatch with diff details", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none", "--profile", "python"], {
    encoding: "utf8",
    env,
  });
  assert.equal(init.status, 0, init.stdout + init.stderr);

  const scriptFile = join(target, ".agents", "scripts", "verify-agent-dev.sh");
  writeFileSync(scriptFile, `${readFileSync(scriptFile, "utf8")}\n# trust drift\n`, "utf8");

  const result = spawnSync(process.execPath, [cliPath, "preview", target], {
    encoding: "utf8",
    env,
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, /review/);
  assert.match(result.stdout, /Agent Feed asset changed/);
  assert.match(result.stdout, /verify-agent-dev\.sh/);
  assert.match(result.stdout, /trust drift/);
});

test("check validates session-state handoff cards", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--profile", "python"], {
    encoding: "utf8",
    env,
  });
  assert.equal(init.status, 0, init.stdout + init.stderr);

  const sessionDir = join(target, ".agents", "session-state");
  const sessionFile = join(sessionDir, "codex-example.json");
  writeFileSync(
    sessionFile,
    `${JSON.stringify(
      {
        schema_version: 1,
        session: { id: "codex-example", label: "Example session", updated_at: "2026-05-01T02:10:33+0800" },
        current_task: {
          goal: "Keep handoff state compact.",
          current_step: "Validate the new schema.",
          stop_condition: "Session check accepts a valid handoff card.",
          next_action: "Run docs checks.",
        },
        carry_forwards: [
          {
            id: "cli-boundary",
            type: "decision",
            content: "Do not merge public commands without a CLI contract decision.",
            why_keep: "Losing this would cause unsafe command cleanup.",
            expires_when: "Command boundary review is accepted or deferred.",
            updated_at: "2026-05-01T02:10:33+0800",
          },
        ],
      },
      null,
      2,
    )}\n`,
    "utf8",
  );

  const valid = spawnSync(process.execPath, [cliPath, "check", target, "--checks", "session", "--json"], {
    encoding: "utf8",
    env,
  });
  assert.equal(valid.status, 0, valid.stdout + valid.stderr);
  assert.equal(JSON.parse(valid.stdout).ok, true);

  writeFileSync(
    sessionFile,
    `${JSON.stringify(
      {
        schema_version: 1,
        session: { id: "codex-example", label: "Example session", updated_at: "2026-05-01T02:10:33+0800" },
        current_task: {
          goal: "Keep handoff state compact.",
          current_step: "Validate custom max.",
          stop_condition: "Session check uses configured max.",
          next_action: "Run docs checks.",
        },
        carry_forwards: Array.from({ length: 8 }, (_, index) => ({
          id: `item-${index}`,
          type: "decision",
          content: "x",
          why_keep: "x",
          expires_when: "x",
          updated_at: "2026-05-01T02:10:33+0800",
        })),
      },
      null,
      2,
    )}\n`,
    "utf8",
  );

  const invalid = spawnSync(process.execPath, [cliPath, "check", target, "--checks", "session", "--json"], {
    encoding: "utf8",
    env,
  });
  assert.equal(invalid.status, 1, invalid.stdout + invalid.stderr);
  assert.match(invalid.stdout, /carry_forwards must contain at most 7 items/);
});

test("config get reads project config values", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none", "--profile", "python"], { encoding: "utf8", env });
  assert.equal(init.status, 0, init.stdout + init.stderr);
  const result = spawnSync(process.execPath, [cliPath, "config", "get", "verification_profile", "--path", target], {
    encoding: "utf8",
    env,
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, /python/);

  const jsonResult = spawnSync(process.execPath, [cliPath, "config", "get", "verification_profile", "--path", target, "--json"], {
    encoding: "utf8",
    env,
  });
  assert.equal(jsonResult.status, 0, jsonResult.stdout + jsonResult.stderr);
  assert.equal(JSON.parse(jsonResult.stdout), "python");
});

test("config check warns about stale user-level project entries", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const trustHome = withTrustEnv().AGENT_FEED_HOME;
  const env = { ...process.env, AGENT_FEED_HOME: trustHome };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none", "--profile", "python"], { encoding: "utf8", env });
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

  const jsonResult = spawnSync(process.execPath, [cliPath, "config", "check", "--path", target, "--json"], {
    encoding: "utf8",
    env,
  });
  assert.equal(jsonResult.status, 0, jsonResult.stdout + jsonResult.stderr);
  const payload = JSON.parse(jsonResult.stdout);
  assert.equal(payload.ok, true);
  assert.equal(payload.target, target);
  assert.match(payload.project_config, /\.agents\/agent-feed\.json$/);
  assert.match(payload.user_config, /config\.json$/);
  assert.match(JSON.stringify(payload), /stale project entry/);
});

test("config prune requires -y and removes stale entries", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const trustHome = withTrustEnv().AGENT_FEED_HOME;
  const env = { ...process.env, AGENT_FEED_HOME: trustHome };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none", "--profile", "python"], { encoding: "utf8", env });
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
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none", "--profile", "python"], { encoding: "utf8", env });
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

test("skill hub installs selected remote skill and indexes it", async () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const init = spawnSync(process.execPath, [cliPath, "init", target, "--clients", "none", "--profile", "python"], {
    encoding: "utf8",
    env,
  });
  assert.equal(init.status, 0, init.stdout + init.stderr);

  const skillHub = await import(skillHubModulePath);
  const hub = {
    key: "example",
    name: "Example Hub",
    owner: "example",
    repo: "skills",
    branch: "main",
    skillsPath: "skills",
    url: "https://github.com/example/skills",
    description: "Example skills.",
  };
  const skills = await skillHub.searchRemoteSkills("review", {
    hubs: [hub],
    fetcher: async (url: string) => {
      if (url.includes("/git/trees/")) {
        return {
          tree: [{ type: "blob", path: "skills/remote-review/SKILL.md" }],
        };
      }
      if (url.includes("/contents/skills/remote-review/SKILL.md")) {
        return {
          content: Buffer.from(
            [
              "---",
              "name: remote-review",
              "description: Use when testing remote skill install.",
              "source: upstream",
              "trust: reviewed",
              "---",
              "",
              "# Remote Review",
              "",
            ].join("\n"),
            "utf8",
          ).toString("base64"),
        };
      }
      throw new Error(`unexpected url: ${url}`);
    },
  });
  assert.equal(skills.length, 1);

  const remotePackage = await skillHub.fetchRemoteSkill(skills[0], {
    fetcher: async (url: string) => {
      if (url.includes("/contents/skills/remote-review/SKILL.md")) {
        return {
          content: Buffer.from(
            [
              "---",
              "name: remote-review",
              "description: Use when testing remote skill install.",
              "---",
              "",
              "# Remote Review",
              "",
            ].join("\n"),
            "utf8",
          ).toString("base64"),
        };
      }
      if (url.includes("/contents/skills/remote-review")) {
        return [
          { type: "file", path: "skills/remote-review/SKILL.md" },
        ];
      }
      throw new Error(`unexpected url: ${url}`);
    },
  });
  const install = skillHub.installRemoteSkillPackage(target, remotePackage, false);
  assert.deepEqual(install.errors, []);
  assert.equal(install.actions.length, 1);

  const skillFile = join(target, ".agents", "skills", "remote-review", "SKILL.md");
  const skillText = readFileSync(skillFile, "utf8");
  assert.match(skillText, /source: hub:example/);
  assert.match(skillText, /trust: custom/);

  const indexed = spawnSync(process.execPath, [cliPath, "index-skills", target, "-y"], {
    encoding: "utf8",
    env,
  });
  assert.equal(indexed.status, 0, indexed.stdout + indexed.stderr);
  assert.match(readFileSync(join(target, ".agents", "skills", "README.md"), "utf8"), /`remote-review`/);

  const trustPath = join(env.AGENT_FEED_HOME!, "config.json");
  const trustConfig = JSON.parse(readFileSync(trustPath, "utf8")) as {
    projects?: Record<string, { assets?: Record<string, unknown> }>;
  };
  assert.equal(
    ".agents/skills/remote-review/SKILL.md" in (trustConfig.projects?.[target]?.assets ?? {}),
    true,
  );
});

test("skill hub reads saved github token from user config", async () => {
  const trustHome = withTrustEnv().AGENT_FEED_HOME;
  const configPath = join(trustHome, "config.json");
  mkdirSync(trustHome, { recursive: true });
  writeFileSync(
    configPath,
    `${JSON.stringify(
      {
        schema_version: 1,
        agent_feed_version: "1.0.0",
        settings: { github_token: "saved-token" },
        projects: {},
      },
      null,
      2,
    )}\n`,
    "utf8",
  );
  const skillHub = await import(skillHubModulePath);
  const previous = process.env.AGENT_FEED_HOME;
  process.env.AGENT_FEED_HOME = trustHome;
  try {
    const token = skillHub.configuredGithubToken(mkdtempSync(join(tmpdir(), "agent-feed-node-")));
    assert.deepEqual(token.errors, []);
    assert.equal(token.token, "saved-token");
  } finally {
    if (previous === undefined) {
      delete process.env.AGENT_FEED_HOME;
    } else {
      process.env.AGENT_FEED_HOME = previous;
    }
  }
});

test("skill hub can save github token in user config", async () => {
  const trustHome = withTrustEnv().AGENT_FEED_HOME;
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const skillHub = await import(skillHubModulePath);
  const previous = process.env.AGENT_FEED_HOME;
  process.env.AGENT_FEED_HOME = trustHome;
  try {
    const saved = skillHub.saveGithubToken("new-token", target);
    assert.deepEqual(saved.errors, []);
    assert.equal(saved.actions.length, 1);
    const config = JSON.parse(readFileSync(join(trustHome, "config.json"), "utf8")) as {
      settings?: { github_token?: string };
    };
    assert.equal(config.settings?.github_token, "new-token");
  } finally {
    if (previous === undefined) {
      delete process.env.AGENT_FEED_HOME;
    } else {
      process.env.AGENT_FEED_HOME = previous;
    }
  }
});

test("init backs up existing AI instruction content", () => {
  const target = mkdtempSync(join(tmpdir(), "agent-feed-node-"));
  const env = { ...process.env, ...withTrustEnv() };
  const existingSkill = join(target, ".agents", "skills", "old-skill", "SKILL.md");
  mkdirSync(join(target, ".agents", "skills", "old-skill"), { recursive: true });
  writeFileSync(existingSkill, "---\nname: old-skill\n---\n", "utf8");
  writeFileSync(join(target, "AGENTS.md"), "# Old AI rules\n", "utf8");

  const result = spawnSync(
    process.execPath,
    [cliPath, "init", target, "--project-name", "Example", "--profile", "python", "--clients", "none"],
    { encoding: "utf8", env },
  );
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, /backup/);
  assert.match(readFileSync(join(target, "AGENTS.md"), "utf8"), /Example AI Development Instructions/);

  const backupRoot = join(target, ".feed-backup");
  assert.equal(existsSync(backupRoot), true);
  const backupDirs = readdirSync(backupRoot);
  assert.equal(backupDirs.length, 1);
  const backupDir = join(backupRoot, backupDirs[0]);
  assert.equal(readFileSync(join(backupDir, "AGENTS.md"), "utf8"), "# Old AI rules\n");
  assert.equal(existsSync(join(backupDir, ".agents", "skills", "old-skill", "SKILL.md")), true);
  const manifest = JSON.parse(readFileSync(join(backupDir, "manifest.json"), "utf8")) as {
    purpose?: unknown;
    project_domain_scaffolded?: unknown;
  };
  assert.equal(manifest.purpose, "legacy-ai-instruction-backup");
  assert.equal(manifest.project_domain_scaffolded, true);
  const guide = readFileSync(join(backupDir, "AI_MIGRATION_GUIDE.md"), "utf8");
  assert.match(guide, /must follow these rules/i);
  assert.match(guide, /Stop and ask the user/i);
});
