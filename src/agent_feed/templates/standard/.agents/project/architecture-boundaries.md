# Architecture Boundaries

This file defines repository-specific architecture boundaries for {{PROJECT_NAME}}.

Replace scaffold rows with concrete constraints before major implementation work. Every durable boundary should point to evidence in code, docs, tests, config, or generated assets.

## AI Maintenance

Before feature, architecture, dependency, persistence, security, public-contract, or adapter work, read this file and verify whether it still matches the repository.

If this file is still generic and the repository has enough evidence, infer concrete boundaries first. If a change alters a listed boundary, update the row in the same task.

## Non-Negotiable Boundaries

| Boundary | Current rule | Evidence | Stop/decision rule |
| --- | --- | --- | --- |
| Public API surface | TODO | TODO: README, API docs, exported modules, CLI help, schema files, tests | Stop before adding or changing public behavior without an owner document or test. |
| Composition root / entrypoint | TODO | TODO: app entrypoint, package metadata, main module, command registration | Stop before moving startup or runtime wiring across ownership boundaries. |
| Durable source of truth | TODO | TODO: storage docs, schemas, config files, state records, contract docs | Stop before creating new durable ownership. |
| Module/import boundary | TODO | TODO: source tree, imports, architecture docs, tests | Stop before cross-layer imports or new shared abstractions. |
| Persistence ownership | TODO | TODO: database modules, migration files, storage adapters, repository contracts | Stop before changing durable semantics or recovery behavior. |
| Secret/user-data handling | TODO | TODO: config docs, env handling, security docs, redaction tests | Stop before storing, logging, or moving secrets/user data. |

## Stop Rules

Stop and ask for confirmation when a task requires:

1. A new public contract not described in project docs.
2. New source-of-truth ownership.
3. A new dependency, database layer, package manager, build tool, or SDK boundary.
4. A change to security, permission, audit, privacy, or trace behavior.
5. A change to persistence, recovery, finalization, projection, or other durable semantics.
