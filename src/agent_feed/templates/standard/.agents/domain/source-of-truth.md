# Source Of Truth

Define durable fact ownership for {{PROJECT_NAME}}.

Source-of-truth docs help AI assistants recover where durable facts live before changing behavior. Replace scaffold rows with repository-backed owners as soon as the project has evidence.

## Owns

This file owns durable fact ownership, recovery/update rules, and canonical
source-of-truth locations for the project.

## Read When

Read this before moving canonical ownership, changing recovery behavior,
changing generated/projection ownership, modifying configuration ownership, or
deciding where a durable fact belongs.

## Evidence

Replace scaffold evidence with owner docs, source modules, storage schemas,
config files, generated assets, audit/event docs, tests, or recovery scripts.

## Ownership

| Fact category | Owner document/module | Evidence | Recovery/update rule |
| --- | --- | --- | --- |
| Public API truth | TODO | TODO | Read owner before changing public behavior. |
| Durable state truth | TODO | TODO | Read owner before changing persistence, migration, or recovery. |
| Event/audit truth | TODO | TODO | Read owner before changing trace, audit, or status semantics. |
| Generated/projection truth | TODO | TODO | Regenerate through the owning generator instead of editing projection output directly. |
| Configuration truth | TODO | TODO | Keep project-visible and user-level config ownership separate. |

## Recovery Principle

Recovery should reconstruct from stable facts and documented ownership rather than from incidental implementation state.
