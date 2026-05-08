# Project Milestones

This file defines the current implementation milestone or phase route for {{PROJECT_NAME}}.

Replace this scaffold with project-specific phases once the repository has roadmap, release, issue, README, or code evidence. Keep it short enough to help AI assistants choose scope without inventing a roadmap.

## Owns

This file owns implementation phase, sequencing, and scope route constraints.

## Read When

Read this before planning scope, sequencing multi-step implementation,
release-facing work, or deciding whether a task belongs in the current phase.

## Evidence

Replace scaffold evidence with roadmap docs, issues, release notes, README
sections, tests, implemented code, or current milestone decisions.

## AI Maintenance

Before planning or implementing a feature, read this file to confirm the current phase and out-of-scope work. After a feature lands, update status only when repository evidence proves the phase changed.

## Default Route

| Phase | Goal | Current status | Evidence | Scope rule |
| --- | --- | --- | --- | --- |
| M0 | Project skeleton and tooling | TODO | TODO | Do not add product behavior before the base toolchain is usable. |
| M1 | Public contracts and core abstractions | TODO | TODO | Treat shared contracts as serial integration surfaces. |
| M2 | First vertical runtime/application slice | TODO | TODO | Prefer one working end-to-end path over broad partial surfaces. |
| M3 | Integration and failure paths | TODO | TODO | Cover adapter, recovery, and error behavior before expanding scope. |
| M4 | Durable storage or production hardening | TODO | TODO | Do not claim production readiness without durability and verification evidence. |

Shared contracts and public API are serial integration surfaces unless explicitly split with disjoint write sets.
