# Open Source Readiness

Date: 2026-05-01

This document tracks public repository readiness for Agent Feed.

It is intentionally separate from `README.md`: the README should stay readable for first-time visitors, while this file records discoverability, product gaps, and release-readiness work.

## GitHub Topics

Use these topics on the GitHub repository page:

```text
ai-coding
ai-agents
coding-agents
agentic-development
ai-engineering
ai-development
ai-software-engineering
ai-assisted-development
agents-md
claude-code
cursor
codex
developer-tools
context-management
verification
code-review
software-quality
cli
python
developer-experience
```

Avoid unrelated high-volume topics such as `rag`, `langchain`, `dify`, `azure-ai`, or `model-finetuning` unless Agent Feed later ships direct functionality for those domains.

## Suggested GitHub Description

```text
Reusable AGENTS.md, .agents rules, and AI coding workflows for reliable agent-assisted development across Codex, Claude Code, and Cursor.
```

## Current Product Gaps

These are not blockers for an initial open-source release, but they are important for maturity.

### GitHub Repository Gaps

1. Remote metadata:
   - Add the public GitHub remote.
   - Configure repository description and topics in the GitHub UI.
   - Add `[project.urls]` after the public URL is known.
2. CI maturity:
   - Current CI runs on Ubuntu, macOS, and Windows for Python 3.11 and 3.12.
   - Keep the wheel install smoke test so packaging regressions fail before release.
   - Confirm the full matrix on GitHub after the remote is created.
3. Release workflow:
   - Add a PyPI Trusted Publishing workflow and release checklist before publishing.
4. Badges:
   - Add CI and PyPI badges after the repository and package URLs are known.
5. Public docs:
   - `docs/ai-development-protocol-flow.md` is public.
   - Keep `docs/open-source-readiness.md` internal because it is a planning and gap-tracking artifact.

### Product And Documentation Gaps

1. Brownfield adoption:
   - Define migration behavior for repositories that already have `AGENTS.md`, `.agents/`, `.claude/`, or `.cursor/`.
2. Monorepo support:
   - Define how verification profiles and project constraints work in monorepos.
3. Troubleshooting:
   - Add common failure modes for init refusal, stale skill index, adapter drift, shell command failures, and global install confusion.
4. Example depth:
   - `examples/basic-output.md` shows the generated structure.
   - Later examples should show Python, Node, and docs-only projects.
5. Comparison page:
   - Add a short comparison with AGENTS.md, Claude Code memory, Cursor Rules, SuperClaude, and AI coding agent frameworks.

### Competitive / Adjacent-Project Gaps

1. Compared with Claude Code memory / `CLAUDE.md`:
   - Agent Feed already treats `AGENTS.md` and `.agents/` as canonical and generates `CLAUDE.md` as an adapter.
   - Gap: keep tracking Claude Code memory and skills conventions so the adapter does not drift from official behavior.
   - Gap: document when a user should edit `.agents/project/` versus Claude-specific files.
2. Compared with Cursor Rules:
   - Agent Feed already generates a Cursor always-apply rule pointing to the canonical source.
   - Gap: current Cursor support is intentionally thin; later support may need scoped rule generation for larger projects.
   - Gap: document how `.cursor/rules/agent-feed.mdc` should coexist with a user's existing Cursor rules.
3. Compared with SuperClaude Framework:
   - Agent Feed is more tool-neutral and focuses on repository protocol, verification, and adapter sync rather than a Claude-only command/persona framework.
   - Gap: SuperClaude has stronger user-facing docs, command matrices, examples, troubleshooting, and onboarding depth.
   - Gap: Agent Feed needs a concise comparison page to explain this boundary without positioning itself as a replacement.
4. Compared with AGENTS.md:
   - Agent Feed extends the single-file instruction idea into installable rules, skills, session-state, checks, and client adapters.
   - Gap: explain why a project would use Agent Feed instead of only writing `AGENTS.md`.
5. Compared with mature Python CLI projects:
   - Agent Feed now has baseline CI, community files, issue templates, PR template, changelog, and code of conduct.
   - Gap: add release automation and clearer release notes before stable publishing.

### Dogfood Case Study Status

A dogfood case study is between P1 and P2:

1. Why it matters:
   - Agent Feed's core claim is that a repository-level AI development protocol improves reliability.
   - A short case study showing how this repository uses Agent Feed on itself would make the claim more credible.
2. Why it is not pure P1:
   - It is not required for users to install or evaluate the CLI.
   - If written too early, it can become marketing text instead of evidence.
3. Recommended shape:
   - Write it only after a few more real changes have been completed with the protocol.
   - Keep it factual: problem, protocol rule used, failure caught, verification run, final result.
   - Place it under docs or examples, not in the README first screen.

## GitHub Release Readiness

Current local GitHub-readiness state:

1. `LICENSE` exists.
2. `README.md` explains the project purpose, pain points, macro flow, commands, and safety model.
3. `docs/ai-development-protocol-flow.md` is public documentation and allowed by `.gitignore`.
4. `examples/basic-output.md` shows the generated output shape.
5. `.github/workflows/ci.yml` exists and runs tests, ruff, mypy, package build, wheel install smoke, and CLI smoke checks on Ubuntu, macOS, and Windows for Python 3.11 and 3.12 on push to `main` and pull requests.
6. Issue templates exist for bug reports, feature requests, and docs/protocol feedback.
7. A pull request template exists.
8. `CONTRIBUTING.md` exists.
9. `SECURITY.md` exists.
10. `CODE_OF_CONDUCT.md` exists.
11. `CHANGELOG.md` exists.

Remaining GitHub blockers:

1. No GitHub remote is configured in this local checkout.
2. GitHub repository description and topics must be set in the GitHub UI after the repository exists.
3. CI has not run on GitHub yet.
4. `[project.urls]` cannot be finalized until the public GitHub URL is known.

## PyPI Release Readiness

Current local package state:

1. `pyproject.toml` exists and uses Hatchling.
2. Console script is configured as `agent-feed = "agent_feed.cli:main"`.
3. Wheel and sdist builds are already supported locally.
4. README is the configured package long description.
5. Runtime dependencies are declared.
6. Tests, local `.agents/`, and local client mirrors are excluded from the package build by default. Repository docs remain in git but are not included in the wheel build.
7. CI includes a built-wheel install smoke test.

Before publishing to PyPI:

1. Confirm the package name `agent-feed` is available on PyPI.
2. Decide the public GitHub repository URL.
3. Add `[project.urls]` to `pyproject.toml` once the GitHub URL is known.
4. Decide whether public docs such as `docs/ai-development-protocol-flow.md` should be included in the sdist, or keep them GitHub-only and use absolute GitHub links from README.
5. Rebuild distributions from a clean tree.
6. Run package metadata checks, preferably `twine check dist/*`.
7. Test install from the built wheel in a clean temporary environment.
8. Test the CLI after wheel install:
   - `agent-feed --version`
   - `agent-feed --help`
   - `agent-feed init --help`
9. Prefer PyPI Trusted Publishing through GitHub Actions instead of a long-lived API token.
10. If using Trusted Publishing, configure the PyPI publisher with:
    - repository owner
    - repository name
    - workflow filename
    - optional `pypi` GitHub environment
11. Add a release checklist:
    - update version
    - update changelog or release notes
    - run full verification
    - build clean artifacts
    - publish
    - verify install from PyPI

## Initial PyPI Blockers

These are the current blockers before a confident PyPI publish:

1. No GitHub remote is configured in this local checkout, so `[project.urls]` cannot be filled safely yet.
2. No release workflow exists.
3. No Trusted Publisher is configured.
4. Build artifacts in `dist/` may be stale; rebuild from the current tree before publishing.
5. `twine check dist/*` has not been run in the current tree.
6. No public release checklist has been executed end to end yet.
