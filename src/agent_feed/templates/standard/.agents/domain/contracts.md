# Contracts

Contracts are the strongest anti-hallucination boundary in AI-assisted development.

## Owns

This file owns public APIs, persistence contracts, module ports, status/event
vocabulary, verification contracts, and project config/trust ownership.

## Read When

Read this before creating or changing public types, CLI/API/SDK behavior,
persistence records, schemas, IDs, statuses, events, module ports, adapters, or
host-facing results.

## Evidence

Replace scaffold evidence with API docs, schemas, migrations, exported modules,
CLI help, tests, contract docs, source files, or integration boundaries.

## Canonical Index

Before creating or changing a public type, store protocol, module port, ID, status, event, record, or host-facing result, read the project canonical contract document.

Set that document here:

`TODO: path/to/contract-index.md`

## Project Contract Map

| Contract area | Canonical owner | Evidence | Change rule |
| --- | --- | --- | --- |
| Public API / CLI / SDK | TODO | TODO | Stop before changing user-visible behavior without owner evidence. |
| Persistence / records / schema | TODO | TODO | Stop before changing durable semantics, migrations, recovery, or finalization. |
| Module ports / adapters | TODO | TODO | Keep public/internal boundaries explicit before adding integration glue. |
| Status / event / audit vocabulary | TODO | TODO | Do not introduce new status/event terms without a canonical owner. |
| Verification contract | TODO | TODO | Keep test evidence tied to the changed public or durable surface. |

## Contract Change Rule

If a task requires a contract not present in the canonical index, stop and ask unless it is purely local implementation detail with no public, persistence, source-of-truth, or externally visible impact.

## Skill Index Contract

`.agents/skills/README.md` is generated from `.agents/skills/*/SKILL.md` frontmatter.

After adding, removing, renaming, importing, or editing skills, run `agent-feed index-skills` or `sh .agents/scripts/index-skills.sh`, then sync configured client adapters.

Skill frontmatter must include `name`, `description`, `source`, and `trust`. Allowed trust values are `core`, `reviewed`, and `custom`.

`.agents/agent-feed.json` may also define project settings that affect skill defaults, session-state schema limits, or Claude reference checks. Change those settings with `agent-feed config set KEY VALUE` so derived assets and external trust state are refreshed in the same step.

## Agent Feed Trust Home Contract

Trusted AI asset hashes live in `$AGENT_FEED_HOME/config.json`, outside the current project.

Default user-level locations:

1. macOS/Linux: `~/.agent-feed`
2. Windows: `%APPDATA%\agent-feed`

Do not store accepted trust hashes in `.agents/`, generated skill indexes, client adapters, package installation directories, or tool-cache directories.
