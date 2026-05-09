# Engineering Architecture

Use this rule for implementation, refactor, tests, project-structure changes,
new files, new directories, ownership decisions, dependency direction,
abstraction, and reuse.

This rule is intentionally repository-agnostic. Do not assume a fixed project
shape such as CLI/core/UI, frontend/backend, service/repository/controller, or
package/module/app. Infer the actual architecture from the current repository.

## Core Rule

Before changing code or structure, identify the smallest existing project unit
that already owns the related behavior.

An owner may be a module, package, directory, component, page, service, route,
job, schema, migration, script, config file, generated asset, test suite,
documentation page, or another unit already used by the project.

Do not create a new owner until repository evidence shows that extending an
existing owner would make the design worse.

## Trigger

Apply this rule before:

1. Adding, moving, renaming, or deleting files or directories.
2. Adding a new command, endpoint, component, service, job, model, schema,
   adapter, script, generated asset, or test group.
3. Expanding a large file, broad function, shared helper, public contract, or
   cross-module behavior.
4. Introducing an abstraction, utility, base class, interface, protocol, hook,
   registry, shared constant, or reusable workflow.
5. Replacing existing behavior or changing dependency direction.
6. Reviewing a diff for maintainability, coupling, duplication, or structure.

Skip the visible architecture card only for tiny edits where the owner,
placement, dependency direction, and verification are obvious from adjacent
code.

## Ownership Discovery

Find the current owner from repository evidence:

1. Existing file and directory names.
2. Import, call, routing, registration, build, or generation paths.
3. Tests and fixtures that already prove related behavior.
4. README, architecture docs, API docs, package docs, or project/domain indexes.
5. Configuration, schema, migration, workflow, or release metadata.
6. Adjacent modules that already handle the same input, output, contract, or
   side effect.

Prefer extending an existing owner when it already owns the behavior and the
change does not mix unrelated responsibilities.

Create a new owner only when you can explain:

1. Why existing owners are insufficient.
2. What the new owner owns.
3. What it explicitly does not own.
4. Which code may call it.
5. Which dependencies it may use.
6. What tests prove its boundary.

If ownership is unclear and the choice affects future development results,
apply `.agents/rules/decision-gates.md` before editing.

## Dependency Direction

Infer dependency direction from existing code before adding imports, calls,
registrations, or generated outputs.

Preserve these generic boundaries unless project evidence says otherwise:

1. Entry points should orchestrate; they should not accumulate reusable domain,
   policy, parsing, validation, persistence, or rendering rules.
2. Reusable logic should not depend on interactive prompts, terminal rendering,
   request/response wrappers, process environment, local filesystem layout,
   network access, or deployment details unless those are part of its documented
   owner contract.
3. Boundary-conversion code should translate between formats, tools, protocols,
   clients, or platforms; it should not become the source of truth for upstream
   rules.
4. Generated outputs, mirrors, caches, and build artifacts must not become the
   canonical source for behavior that is owned elsewhere.
5. Tests should verify the owning behavior without forcing production code to
   depend on test-only structure.

When a change needs to reverse an existing dependency direction, stop and treat
it as an architecture decision.

## Reuse And Abstraction

Reuse before creating new structure:

1. Search for existing owners, helpers, fixtures, validators, parsers, schema
   loaders, formatters, adapters, scripts, or documented patterns.
2. Prefer standard library, existing dependencies, and established project
   patterns over new local machinery.
3. Keep the first occurrence local when it is simple and not a boundary.
4. Extract a helper when repetition or boundary clarity justifies it.
5. Promote to shared utility only when multiple owners need it and the contract
   is stable enough to test.
6. Create a public abstraction only when callers, tests, docs, or external
   contracts prove that the abstraction is durable.

Do not introduce a directory, framework, registry, base class, interface,
protocol, or generic helper only to make the patch look organized.

## Structure Smells

Treat these as review findings or reasons to redesign before editing:

1. A file handles unrelated concerns such as entry handling, policy, parsing,
   persistence, rendering, network calls, and cleanup without clear seams.
2. A new feature is implemented by copying similar logic instead of extending
   the owner that already handles the behavior.
3. A small request requires editing many unrelated files because ownership is
   unclear.
4. A low-level reusable unit imports a high-level entrypoint, UI, transport,
   runtime, or deployment concern without a documented reason.
5. Generated, mirrored, cached, or test-only files become sources of truth.
6. A large smoke test is the only proof for logic that could be tested through
   an owner-level unit or integration boundary.
7. Names introduce new concepts that wrap existing behavior without a durable
   contract.

## Architecture Card

For non-trivial implementation, refactor, file creation, or structure work,
record this compact card in the plan or working notes:

```md
| Item | Decision |
| --- | --- |
| Existing owner | Smallest current project unit that owns related behavior |
| Evidence | Files, calls, tests, docs, or config proving the owner |
| Placement | Where the change belongs and why |
| Reuse | Existing behavior, helper, dependency, pattern, or test reused |
| New owner | Needed? If yes, ownership, non-ownership, callers, dependencies |
| Dependency direction | Existing direction preserved or decision required |
| Abstraction level | Local code / helper / shared utility / public contract |
| Verification | Owner-level tests/checks that prove the boundary |
```

## Review Questions

During review, ask:

1. Did the change modify the real owner of the behavior?
2. Is ownership supported by repository evidence instead of template categories?
3. Are dependency directions preserved?
4. Did the implementation reuse existing behavior before creating new machinery?
5. Is the abstraction level no broader than the current need proves?
6. Do tests follow the owner and prove the boundary?
7. Did any new file, directory, helper, or concept add necessary maintenance
   value?
