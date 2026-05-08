# Project Structure

This file defines repository-specific source layout and placement constraints for {{PROJECT_NAME}}.

Replace scaffold rows with concrete source-tree ownership rules. Use evidence paths so future AI turns can verify placement decisions quickly.

## Owns

This file owns source layout, file placement, generated-file ownership,
adapter/integration placement, and import-direction constraints.

## Read When

Read this before adding, moving, importing, generating, deleting, or relocating
files, modules, tests, docs, protocol assets, or client adapters.

## Evidence

Replace scaffold evidence with package config, source tree paths, imports,
tests, fixtures, generator scripts, managed markers, or documented owners.

## AI Maintenance

Before adding, moving, importing, generating, or deleting files, read this file and confirm the target path has a documented owner. If the source tree changes, update the affected row in the same task.

## Placement Rules

| Area | Path/module | Responsibility | Evidence | Placement rule |
| --- | --- | --- | --- | --- |
| Production source | TODO | TODO | TODO: package config, imports, README, source tree | Add production code only under the documented owner. |
| Tests | TODO | TODO | TODO: test runner config, existing tests, fixtures | Match test location to owner module and behavior risk. |
| Public interface | TODO | TODO | TODO: exports, CLI/API docs, schema files | Keep public contracts separate from internal helpers. |
| Adapters/integrations | TODO | TODO | TODO: adapter modules, generated assets, integration tests | Place external-client glue under the adapter owner. |
| Generated files | TODO | TODO | TODO: generation scripts, managed markers, config | Write generated files only through the owning generator. |
| Forbidden imports | TODO | TODO | TODO: architecture docs, dependency graph, tests | Do not import against the documented direction. |
| Project-local skills | TODO | TODO | TODO: `.agents/skills`, skill index, trust state | Mark custom/imported/reviewed status explicitly. |
