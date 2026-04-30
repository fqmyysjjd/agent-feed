# Architecture Boundaries

This file defines repository-specific architecture boundaries for {{PROJECT_NAME}}.

Replace this template with concrete constraints before major implementation work.

## Non-Negotiable Boundaries

1. Define the public API surface.
2. Define the composition root or app entrypoint.
3. Define source-of-truth owners for durable facts.
4. Define module/import boundaries.
5. Define persistence ownership.
6. Define secret and user-data handling rules.

## Stop Rules

Stop and ask for confirmation when a task requires:

1. A new public contract not described in project docs.
2. New source-of-truth ownership.
3. A new dependency, database layer, package manager, build tool, or SDK boundary.
4. A change to security, permission, audit, privacy, or trace behavior.
5. A change to persistence, recovery, finalization, projection, or other durable semantics.
