import { Buffer } from "node:buffer";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { basename, dirname, isAbsolute, join, normalize } from "node:path";

import { type WriteAction } from "./template.js";
import {
  CONFIG_FILE,
  TRUST_ENV,
  legacyConfigPath,
  projectLocalConfigErrors,
  readExistingOrLegacyConfig,
  recommendedHome,
  trustConfigPath,
} from "./trust.js";
import { VERSION } from "./version.js";

const GITHUB_API = process.env.AGENT_FEED_GITHUB_API?.replace(/\/+$/, "") ?? "https://api.github.com";

export type SkillHub = {
  key: string;
  name: string;
  owner: string;
  repo: string;
  branch: string;
  skillsPath: string;
  url: string;
  description: string;
};

export type RemoteSkill = {
  hub: SkillHub;
  name: string;
  path: string;
  url: string;
  description: string;
};

export type RemoteSkillFile = {
  path: string;
  content: string;
};

export type RemoteSkillPackage = {
  skill: RemoteSkill;
  files: RemoteSkillFile[];
};

export type JsonFetcher = (
  url: string,
  options: { token?: string; params?: Record<string, string> },
) => Promise<unknown>;

export const CURATED_HUBS: SkillHub[] = [
  {
    key: "openai",
    name: "OpenAI Skills",
    owner: "openai",
    repo: "skills",
    branch: "main",
    skillsPath: "skills",
    url: "https://github.com/openai/skills",
    description: "OpenAI's public skills repository.",
  },
  {
    key: "anthropic",
    name: "Anthropic Skills",
    owner: "anthropics",
    repo: "skills",
    branch: "main",
    skillsPath: "skills",
    url: "https://github.com/anthropics/skills",
    description: "Anthropic's public skills repository.",
  },
  {
    key: "trailofbits",
    name: "Trail of Bits Skills",
    owner: "trailofbits",
    repo: "skills",
    branch: "main",
    skillsPath: "skills",
    url: "https://github.com/trailofbits/skills",
    description: "Security-focused public skills from Trail of Bits.",
  },
];

export async function searchRemoteSkills(
  keyword: string,
  options: { token?: string; hubs?: SkillHub[]; fetcher?: JsonFetcher } = {},
): Promise<RemoteSkill[]> {
  const terms = keyword
    .split(/\s+/)
    .map((term) => term.trim().toLowerCase())
    .filter(Boolean);
  const fetcher = options.fetcher ?? githubJson;
  const skills: RemoteSkill[] = [];
  const errors: string[] = [];
  for (const hub of options.hubs ?? CURATED_HUBS) {
    try {
      const hubSkills = await listHubSkills(hub, { token: options.token, fetcher });
      for (const skill of hubSkills) {
        const haystack = `${skill.name} ${skill.description} ${hub.name}`.toLowerCase();
        if (terms.length === 0 || terms.every((term) => haystack.includes(term))) {
          skills.push(skill);
        }
      }
    } catch (error) {
      errors.push(`${hub.name}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
  if (errors.length > 0 && skills.length === 0) {
    throw new Error(`Could not load curated skill hubs: ${errors.join("; ")}`);
  }
  return skills.sort((left, right) =>
    `${left.hub.name.toLowerCase()}/${left.name.toLowerCase()}`.localeCompare(
      `${right.hub.name.toLowerCase()}/${right.name.toLowerCase()}`,
    ),
  );
}

export async function fetchRemoteSkill(
  skill: RemoteSkill,
  options: { token?: string; fetcher?: JsonFetcher } = {},
): Promise<RemoteSkillPackage> {
  const files = await fetchTreeFiles(skill.hub, skill.path, {
    root: skill.path,
    token: options.token,
    fetcher: options.fetcher ?? githubJson,
  });
  return { skill, files };
}

export function installRemoteSkillPackage(
  target: string,
  remotePackage: RemoteSkillPackage,
  dryRun: boolean,
): { actions: WriteAction[]; errors: string[] } {
  const skillRoot = join(target, ".agents", "skills");
  if (!existsSync(skillRoot)) {
    return { actions: [], errors: ["missing .agents/skills; run agent-feed init before installing skills"] };
  }
  const destinationName = remotePackage.skill.name;
  if (!/^[a-z0-9._-]+$/.test(destinationName)) {
    return { actions: [], errors: [`remote skill name is not safe to install: ${destinationName}`] };
  }
  const skillDir = join(skillRoot, destinationName);
  if (existsSync(skillDir)) {
    return { actions: [], errors: [`${skillDir} already exists`] };
  }

  const actions: WriteAction[] = [];
  for (const remoteFile of remotePackage.files) {
    if (!safeRelativePath(remoteFile.path)) {
      return { actions: [], errors: [`remote skill file path is not safe to install: ${remoteFile.path}`] };
    }
    const destination = join(skillDir, remoteFile.path);
    const content = normalizeSkillContent(remotePackage, remoteFile);
    actions.push({
      path: destination,
      action: dryRun ? "would create" : "create",
      detail: `from ${remotePackage.skill.hub.name}`,
    });
    if (!dryRun) {
      mkdirSync(dirname(destination), { recursive: true });
      writeFileSync(destination, content, "utf8");
    }
  }
  return { actions, errors: [] };
}

export function normalizeSkillContent(remotePackage: RemoteSkillPackage, remoteFile: RemoteSkillFile): string {
  return remoteFile.path === "SKILL.md"
    ? normalizeSkillFrontmatter(remoteFile.content, remotePackage.skill)
    : remoteFile.content;
}

export function normalizeSkillFrontmatter(content: string, skill: RemoteSkill): string {
  const lines = content.split(/\r?\n/);
  if (lines[0]?.trim() !== "---") {
    return content;
  }
  const closing = lines.findIndex((line, index) => index > 0 && line.trim() === "---");
  if (closing < 0) {
    return content;
  }
  const next = [...lines];
  const keyLines = new Map<string, number>();
  for (let index = 1; index < closing; index += 1) {
    if (!next[index].includes(":")) {
      continue;
    }
    const [key] = next[index].split(":", 1);
    keyLines.set(key.trim(), index);
  }
  const metadata: Record<string, string> = {
    source: `hub:${skill.hub.key}`,
    trust: "custom",
  };
  let insertAt = closing;
  for (const [key, value] of Object.entries(metadata)) {
    const existing = keyLines.get(key);
    if (existing === undefined) {
      next.splice(insertAt, 0, `${key}: ${value}`);
      insertAt += 1;
    } else {
      next[existing] = `${key}: ${value}`;
    }
  }
  let normalized = next.join("\n");
  if (content.endsWith("\n") && !normalized.endsWith("\n")) {
    normalized += "\n";
  }
  return normalized;
}

export function previewSkillTree(remotePackage: RemoteSkillPackage): string {
  return [`${remotePackage.skill.name}/`, ...remotePackage.files.map((file) => `  ${file.path}`)].join("\n");
}

export function githubHeaders(token?: string): Record<string, string> {
  const headers: Record<string, string> = {
    Accept: "application/vnd.github+json",
    "User-Agent": "agent-feed-skill-hub",
    "X-GitHub-Api-Version": "2022-11-28",
  };
  const resolved = (token ?? process.env.GITHUB_TOKEN ?? "").trim();
  if (resolved) {
    headers.Authorization = `Bearer ${resolved}`;
  }
  return headers;
}

export function configuredGithubToken(root?: string): { token?: string; errors: string[] } {
  const path = settingsConfigPath(root);
  if (path.errors.length > 0) {
    return { errors: path.errors };
  }
  if (!existsSync(path.path) && !existsSync(legacyConfigPath(path.path))) {
    return { errors: [] };
  }
  const loaded = readExistingOrLegacyConfig(path.path);
  if (loaded.errors.length > 0) {
    return { errors: loaded.errors };
  }
  const settings = loaded.state.settings;
  if (!settings || typeof settings !== "object" || Array.isArray(settings)) {
    return { errors: [`${path.path} settings must be a JSON object`] };
  }
  const token = (settings as Record<string, unknown>).github_token;
  if (typeof token !== "string" || !token.trim()) {
    return { errors: [] };
  }
  return { token: token.trim(), errors: [] };
}

export function preferredGithubToken(root: string): { token?: string; warnings: string[] } {
  const envToken = (process.env.GITHUB_TOKEN ?? "").trim();
  if (envToken) {
    return { token: envToken, warnings: [] };
  }
  const configured = configuredGithubToken(root);
  return { token: configured.token, warnings: configured.errors };
}

export function skillHubFailureHelp(error: string): string {
  const configPath = settingsConfigPath().path;
  return [
    error,
    "",
    "If GitHub blocked anonymous access, set a token for this command:",
    '  export GITHUB_TOKEN="ghp_your_token_here"',
    "",
    "PowerShell:",
    '  $env:GITHUB_TOKEN = "ghp_your_token_here"',
    "",
    `Or set settings.github_token in ${configPath}:`,
    "{",
    '  "schema_version": 1,',
    `  "agent_feed_version": "${VERSION}",`,
    '  "settings": {',
    '    "github_token": "ghp_your_token_here"',
    "  },",
    '  "projects": {}',
    "}",
  ].join("\n");
}

async function listHubSkills(
  hub: SkillHub,
  options: { token?: string; fetcher: JsonFetcher },
): Promise<RemoteSkill[]> {
  const entries = await githubTree(hub, options);
  const skills: RemoteSkill[] = [];
  for (const entry of entries) {
    const path = typeof entry.path === "string" ? entry.path : "";
    if (entry.type !== "blob" || basename(path) !== "SKILL.md") {
      continue;
    }
    if (hub.skillsPath && !path.startsWith(`${hub.skillsPath}/`)) {
      continue;
    }
    const skillPath = dirname(path).replaceAll("\\", "/");
    const name = basename(skillPath);
    const description = await readRemoteDescription(hub, skillPath, options);
    skills.push({
      hub,
      name,
      path: skillPath,
      url: `${hub.url}/tree/${hub.branch}/${skillPath}`,
      description,
    });
  }
  return skills;
}

async function readRemoteDescription(
  hub: SkillHub,
  skillPath: string,
  options: { token?: string; fetcher: JsonFetcher },
): Promise<string> {
  for (const fileName of ["SKILL.md", "README.md"]) {
    try {
      const content = await githubFileText(hub, `${skillPath}/${fileName}`, options);
      const frontmatter = parseFrontmatter(content);
      if (frontmatter.description) {
        return frontmatter.description;
      }
      const heading = firstMarkdownHeading(content);
      if (heading) {
        return heading;
      }
    } catch (error) {
      if (error instanceof Error && error.message.includes("HTTP 404")) {
        continue;
      }
      throw error;
    }
  }
  return "";
}

async function fetchTreeFiles(
  hub: SkillHub,
  path: string,
  options: { root: string; token?: string; fetcher: JsonFetcher },
): Promise<RemoteSkillFile[]> {
  const files: RemoteSkillFile[] = [];
  const entries = await githubContents(hub, path, options);
  for (const entry of entries) {
    const entryPath = typeof entry.path === "string" ? entry.path : "";
    if (entry.type === "dir") {
      files.push(...(await fetchTreeFiles(hub, entryPath, options)));
    } else if (entry.type === "file") {
      const relPath = entryPath.slice(options.root.length).replace(/^\/+/, "");
      files.push({
        path: relPath,
        content: await githubFileText(hub, entryPath, options),
      });
    }
  }
  return files;
}

async function githubContents(
  hub: SkillHub,
  path: string,
  options: { token?: string; fetcher: JsonFetcher },
): Promise<Array<Record<string, unknown>>> {
  const data = await options.fetcher(`${GITHUB_API}/repos/${hub.owner}/${hub.repo}/contents/${path}`, {
    token: options.token,
    params: { ref: hub.branch },
  });
  if (Array.isArray(data)) {
    return data.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object");
  }
  throw new Error(`Expected directory listing for ${hub.owner}/${hub.repo}/${path}`);
}

async function githubTree(
  hub: SkillHub,
  options: { token?: string; fetcher: JsonFetcher },
): Promise<Array<Record<string, unknown>>> {
  const data = await options.fetcher(`${GITHUB_API}/repos/${hub.owner}/${hub.repo}/git/trees/${hub.branch}`, {
    token: options.token,
    params: { recursive: "1" },
  });
  if (data && typeof data === "object" && !Array.isArray(data)) {
    const tree = (data as Record<string, unknown>).tree;
    if (Array.isArray(tree)) {
      return tree.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object");
    }
  }
  throw new Error(`Expected recursive tree for ${hub.owner}/${hub.repo}`);
}

async function githubFileText(
  hub: SkillHub,
  path: string,
  options: { token?: string; fetcher: JsonFetcher },
): Promise<string> {
  const data = await options.fetcher(`${GITHUB_API}/repos/${hub.owner}/${hub.repo}/contents/${path}`, {
    token: options.token,
    params: { ref: hub.branch },
  });
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error(`Expected file response for ${hub.owner}/${hub.repo}/${path}`);
  }
  const encoded = (data as Record<string, unknown>).content;
  if (typeof encoded !== "string") {
    throw new Error(`Missing content for ${hub.owner}/${hub.repo}/${path}`);
  }
  return Buffer.from(encoded.replace(/\s+/g, ""), "base64").toString("utf8");
}

async function githubJson(
  url: string,
  options: { token?: string; params?: Record<string, string> },
): Promise<unknown> {
  const requestUrl = new URL(url);
  for (const [key, value] of Object.entries(options.params ?? {})) {
    requestUrl.searchParams.set(key, value);
  }
  const response = await fetch(requestUrl, { headers: githubHeaders(options.token) });
  if (!response.ok) {
    throw new Error(formatHttpStatusError(response, requestUrl.toString()));
  }
  return response.json() as Promise<unknown>;
}

function formatHttpStatusError(response: Response, url: string): string {
  if (response.status === 403 && response.headers.get("x-ratelimit-remaining") === "0") {
    const reset = response.headers.get("x-ratelimit-reset");
    return `GitHub API rate limit reached. Set GITHUB_TOKEN or settings.github_token.${reset ? ` reset=${reset}` : ""}`;
  }
  if (response.status === 404) {
    return `GitHub path not found: ${url}`;
  }
  return `GitHub request failed with HTTP ${response.status}: ${url}`;
}

function parseFrontmatter(content: string): Record<string, string> {
  const lines = content.split(/\r?\n/);
  if (lines[0]?.trim() !== "---") {
    return {};
  }
  const values: Record<string, string> = {};
  for (const line of lines.slice(1)) {
    if (line.trim() === "---") {
      break;
    }
    if (!line.includes(":")) {
      continue;
    }
    const [key, ...rest] = line.split(":");
    values[key.trim()] = rest.join(":").trim().replace(/^["']|["']$/g, "");
  }
  return values;
}

function firstMarkdownHeading(content: string): string {
  for (const line of content.split(/\r?\n/)) {
    if (line.startsWith("# ")) {
      return line.replace(/^# /, "").trim();
    }
  }
  return "";
}

function settingsConfigPath(root?: string): { path: string; errors: string[] } {
  const config = trustConfigPath();
  if (config.path && config.errors.length === 0) {
    const local = root ? projectLocalConfigErrors(root, config.path) : [];
    return { path: config.path, errors: local };
  }
  return { path: join(recommendedHome(), CONFIG_FILE), errors: [] };
}

function safeRelativePath(path: string): boolean {
  const normalized = normalize(path);
  return !isAbsolute(path) && normalized !== ".." && !normalized.startsWith(`..${"/"}`) && !normalized.startsWith(`..${"\\"}`);
}
