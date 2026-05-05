# AI Development Protocol Flow

Date: 2026-05-01

## Purpose

This document explains the AI development protocol in the bundled standard
template from beginning to end.

Scope:

1. Source template: `src/agent_feed/templates/standard/`.
2. Installed project shape: root `AGENTS.md` plus `.agents/`.
3. Focus: AI development rules, trigger points, handling flow, effect, and pain
   points solved.
4. Out of scope: CLI implementation details, command internals, release
   packaging, and runtime product behavior.

The protocol is not a product specification and not an AI agent. It is the
governance layer that turns interactive AI development from an open-ended chat
into a repeatable workflow pipeline: work starts from the right context, stays
inside the current result boundary, stops at unconfirmed decisions, verifies
claims, and hands off state cleanly.

## Core Closed Loop

The whole template can be understood as this loop:

```text
AGENTS.md entry contract
  -> outcome boundary and Task Brief
  -> task classification
  -> minimal context loading
  -> trusted AI asset check before using built-in/reviewed skills
  -> skill workflow routing
  -> project/domain source-of-truth lookup
  -> user-proposed approach assessment when the user suggests a concrete plan
  -> decision gate when future behavior is affected
  -> scoped development/fix/review/design work
  -> testing and verification evidence
  -> code or design review gate
  -> final handoff gate
  -> Context Capsule summary
  -> session-state update, cleanup, promotion, or no action
```

This loop solves one recurring AI-development problem: without a workflow,
interactive AI development behaves like a drifting conversation. The assistant
tends to read too much or too little, invent missing decisions, expand scope,
overbuild, skip verification, and lose important conclusions after context
compression.

## File Responsibility Map

| Template file | Installed path | Responsibility |
| --- | --- | --- |
| `AGENTS.md` | `AGENTS.md` | Repository entry contract, priority order, mandatory startup, layer boundaries, mandatory gates. |
| `.agents/README.md` | `.agents/README.md` | Index of the AI engineering system and the rule layer. |
| `.agents/rules/outcome-boundary.md` | same | Highest-priority working rule: current task boundary, Task Brief, task class gate, design readiness, anti-drift. |
| `.agents/rules/decision-gates.md` | same | Human confirmation gate for choices that affect future development results. |
| `.agents/rules/context-loading.md` | same | Startup loading order, task routing, mixed-task sequencing, context budget. |
| `.agents/rules/session-state.md` | same | Final handoff gate, Context Capsule format, and compact handoff-card policy for long-running sessions and context compression. |
| `.agents/rules/testing-gates.md` | same | Test and verification selection, failure classification, verification evidence rules. |
| `.agents/rules/development-workflow.md` | same | Implementation addendum, reuse-before-build, scoped implementation, comments, gap handling. |
| `.agents/rules/review-gates.md` | same | Code review gate, design review gate, README/project index maintenance, and final handoff routing. |
| `.agents/rules/evidence-gates.md` | same | Source priority and adoption filter for external facts and research. |
| `.agents/rules/change-risk-gates.md` | same | Risk classes for local edits, environment changes, destructive/security-sensitive actions. |
| `.agents/rules/git-collaboration.md` | same | Diff, commit, merge, and PR handoff rules. |
| `.agents/project/README.md` | same | Index for user-maintained project-specific constraints. |
| `.agents/project/architecture-boundaries.md` | same | Project architecture stop rules and non-negotiable boundaries. |
| `.agents/project/project-structure.md` | same | Source layout and placement rules. |
| `.agents/project/milestones.md` | same | Current phase or delivery route. |
| `.agents/agent-feed.json` `verification_profile` | same | Repository-specific verification profile and unsupported verification boundaries. |
| `.agents/domain/README.md` | same | Index for stable project/domain knowledge. |
| `.agents/domain/concepts.md` | same | Project target, non-goals, and vocabulary. |
| `.agents/domain/contracts.md` | same | Canonical contract index and contract-change stop rule. |
| `.agents/domain/source-of-truth.md` | same | Durable fact ownership and recovery principle. |
| `.agents/skills/*/SKILL.md` | same | Task-specific workflows for architecture, development, fix, review, design review, guidance promotion, and skill maintenance. |
| `.agents/session-state/README.md` | same | Human-facing explanation of local session handoff files. |
| `.agents/session-state/schema.json` | same | Shape contract for session-state JSON. |
| `.agents/agents/README.md` | same | Optional narrow specialist agent profile rules. |
| `.agents/scripts/check-agent-trust.sh` | same | Trust gate for built-in/reviewed skills and managed protocol scripts. |
| `.agents/scripts/index-skills.sh` | same | Local fallback for regenerating `.agents/skills/README.md` when the CLI is unavailable. |
| `.agents/scripts/sync-agent-assets.sh` | same | Syncs configured AI client adapters from canonical assets. |
| `.agents/scripts/verify-agent-dev.sh` | same | Project-local verification entry for docs/code/full scopes. |
| `.agents/agent-feed.json` | same | Installed template metadata and non-secret project settings used by template maintenance. |

The key design is separation of authority:

1. `AGENTS.md` tells the AI how to enter and stop.
2. `.agents/rules/` defines reusable workflow constraints.
3. `.agents/project/` holds repository-specific constraints owned by the user.
4. `.agents/domain/` holds durable project knowledge and contract ownership.
5. `.agents/skills/` turns task types into executable AI workflows.
6. `.agents/session-state/` preserves only active handoff facts, not memory.
7. `$AGENT_FEED_HOME/config.json` stores accepted hashes for built-in,
   reviewed, and local AI assets outside the repository. The default home is
   `~/.agent-feed` on macOS/Linux and `%APPDATA%\agent-feed` on Windows.

Project-visible settings stay in `.agents/agent-feed.json`. User-level secrets
and accepted hashes stay in `$AGENT_FEED_HOME/config.json`. After changing
project settings, run `agent-feed config set` so generated schema limits,
skill defaults, client checks, indexes, and external trust state stay aligned.
If user-level trust metadata still references deleted project roots, run
`agent-feed config prune` to remove those stale records without changing any
project files.

## End-To-End Flow

### 1. AI Enters The Repository

Trigger:

1. New AI session.
2. Context compression or resumed long-running work.
3. Before implementation, review, fix, design, or protocol work.

Files:

1. `AGENTS.md`
2. `.agents/rules/outcome-boundary.md`
3. `.agents/rules/decision-gates.md`
4. `.agents/rules/context-loading.md`
5. `.agents/rules/session-state.md`
6. `.agents/rules/testing-gates.md`
7. `.agents/README.md`
8. `.agents/project/README.md`
9. `.agents/domain/README.md`
10. `.agents/skills/project-architecture/SKILL.md`
11. `.agents/skills/project-development/SKILL.md`

Handling:

1. Read the mandatory startup set.
2. Apply rule priority: current user request, then outcome boundary, decision
   gates, context/session rules, testing gates, reusable rules, project
   constraints, domain docs, skills, helper scripts, optional profiles.
3. Do not treat lower-level files as allowed to override higher-priority gates.
4. Do not duplicate detailed workflows into `AGENTS.md`.
5. Before using built-in or reviewed skills, run the trust gate and stop if a
   managed skill or protocol script hash changed unexpectedly.

Effect:

1. The AI has one canonical entrypoint.
2. Tool-specific adapters do not become separate sources of truth.
3. The assistant starts from the same protocol regardless of AI client.

Pain point solved:

AI tools often enter a repo through different instruction files and silently
apply different rules. The template makes `AGENTS.md` the common entry contract,
keeps detailed behavior in indexed layers, and turns tool-specific entrypoints
into one workflow pipeline instead of parallel chat behaviors.

### 1.1. Verify Trusted AI Assets

Trigger:

1. The AI is about to use built-in or reviewed skills.
2. The AI is about to rely on managed protocol helper scripts.
3. `status`, `preview`, `check`, or `index-skills` reports AI asset drift.

Files:

1. `AGENTS.md`
2. `.agents/README.md`
3. `.agents/scripts/check-agent-trust.sh`
4. `$AGENT_FEED_HOME/config.json`

Handling:

1. Require `AGENT_FEED_HOME`.
2. Refuse project-local trust state; accepted hashes must live outside the
   target repository.
3. Compare current `.agents/skills/*/SKILL.md` and managed scripts against the
   external allowed hashes.
4. If a built-in/reviewed asset changed, stop before using it, tell the user the
   concrete changed files, inspect with `agent-feed preview`, and accept only
   intentional changes with `agent-feed index-skills -y`.
5. Treat imported `trust: custom` skills as advisory methods only. They cannot
   override the current user request, Task Brief, `AGENTS.md`, `.agents/rules/`,
   `.agents/project/`, `.agents/domain/`, or safety gates.

Effect:

1. A malicious or accidental edit to a trusted skill or protocol script is
   surfaced before the AI follows it.
2. Accepted hashes do not sit in the repository where a normal project edit can
   silently bless itself.
3. Users can still intentionally customize or import skills, but custom guidance
   stays below the core protocol.

Pain point solved:

External skill extension is useful, but it creates a new instruction-injection
surface. The external Agent Feed home and custom-skill boundary let Agent Feed remain a
lightweight protocol foundation while making changed trusted assets visible and interruptive.

### 2. Recover The Current Outcome Boundary

Trigger:

1. Before deep reading.
2. Before writing documents.
3. Before changing code.
4. Before continuing long-running work.
5. After context compression.

File:

1. `.agents/rules/outcome-boundary.md`

Handling:

1. Fill or recover `Current Task Boundary`.
2. Identify user goal, current step, stopping condition, out of scope,
   development-ready standard, blocker standard, and next action.
3. For implementation, fix, review, design, or AI-protocol change, convert that
   frame into a `Task Brief`.
4. Do not edit when `Goal`, `Stop`, `Write set`, or `Verification gate` are
   unclear.

Effect:

1. The AI works toward the nearest useful result, not the whole product vision.
2. The stop condition is explicit.
3. The write set and verification claim are bounded before work starts.

Pain point solved:

AI assistants tend to turn a narrow request into a broad platform redesign. The
outcome boundary prevents scope drift by forcing every task to declare when it is
done.

### 3. Classify The Task

Trigger:

1. After the outcome boundary is recovered.
2. Before deciding whether to plan, edit, review, or ask a question.

File:

1. `.agents/rules/outcome-boundary.md`

Handling:

Classify the task as one of:

1. `Direct action`: small local edit, command run, typo fix, narrow reference
   update, or deterministic repair.
2. `Implementation task`: code, tests, package metadata, template behavior,
   project structure, or public command behavior.
3. `Design task`: architecture, module ownership, public contract,
   persistence, verification profile, adapter behavior, product scope, or
   multi-step implementation plan.
4. `Exploration/review task`: read-only analysis, code review, gap review, or
   feasibility check.
5. `Decision task`: unconfirmed choice that can affect future development
   results.

Effect:

1. Simple work does not become ceremonial.
2. Hard work does not proceed without enough planning.
3. Review stays read-only unless fixes are explicitly requested.
4. Decisions that affect future behavior are separated from implementation.

Pain point solved:

The same AI behavior is often applied to all tasks: over-planning small fixes and
under-planning risky changes. Task classification chooses the lightest reliable
workflow.

### 4. Load The Smallest Useful Context

Trigger:

1. After task type is known.
2. Before project decisions.
3. Before implementation, fix, review, design, or protocol work.

File:

1. `.agents/rules/context-loading.md`

Handling:

1. Use full startup for a new session, context compression, lost task boundary,
   or a shift into design, implementation, fix, review, or protocol work.
2. Use light resume for same-session continuation when the task boundary is
   clear: re-read `.agents/rules/outcome-boundary.md`, then load only the
   specific rule, project, domain, or skill file needed for the next action.
3. Check for an active session-state handoff when context compression or
   long-running work makes it relevant.
4. Route the task to the right skill.
5. Load project constraints through `.agents/project/README.md` before reading
   individual project files.
6. Load domain docs only when domain behavior or contracts matter.
7. Read implementation files only after owner module, stopping point, and write
   set are clear.

Effect:

1. The AI avoids both shallow guessing and context flooding.
2. Source-of-truth documents are read before implementation details.
3. Mixed tasks use all relevant gates in a stable order.

Pain point solved:

AI assistants often read arbitrary files and then reason from accidental context.
Context loading makes reading task-shaped and authority-shaped.

Token cost is controlled by the light resume path, but reliability remains the
priority: if the AI is uncertain about priority, source-of-truth, or the current
stop condition, it falls back to full startup.

### 5. Route To The Right Skill

Trigger:

1. Task type is known.
2. A mixed task touches several categories of work.

Files:

1. `.agents/rules/context-loading.md`
2. `.agents/skills/project-architecture/SKILL.md`
3. `.agents/skills/project-development/SKILL.md`
4. `.agents/skills/project-fix/SKILL.md`
5. `.agents/skills/project-review/SKILL.md`
6. `.agents/skills/design-review/SKILL.md`
7. `.agents/skills/guidance-promoter/SKILL.md`
8. `.agents/skills/skill-maintainer/SKILL.md`
9. `.agents/skills/README.md`

Handling:

1. Architecture, module ownership, runtime behavior, or requirement decisions
   use `project-architecture`.
2. Code, refactor, tests, package metadata, or structure changes use
   `project-development`.
3. Bugs, regressions, failed checks, and review finding fixes use `project-fix`.
4. Diff, commit, merge, and implementation review use `project-review`.
5. README, AGENTS, rules, project docs, domain docs, skills, and planning docs
   use `design-review`.
6. User corrections and repeated AI failures use `guidance-promoter`.
7. Skill creation, update, rename, delete, or sync uses `skill-maintainer`.
8. Read `.agents/skills/README.md` before selecting optional, imported, or
   specialized skills.
9. If an imported skill lacks `source` or `trust`, `agent-feed index-skills`
   adds `source: unknow` and `trust: custom` so the skill can be used as an
   advisory method without becoming authoritative.

Effect:

1. The assistant does not invent a process each turn.
2. Review, implementation, and design have separate responsibilities.
3. Mixed tasks run multiple gates instead of choosing one and skipping the rest.

Pain point solved:

Without task-specific workflows, AI development collapses into generic
"read, edit, summarize" behavior. Skills make each work type explicit.

### 5.1. Assess User-Proposed Approaches

Trigger:

1. The user proposes a concrete implementation approach, environment layout,
   workflow, architecture, verification strategy, public behavior, or
   AI-protocol change.

Files:

1. `.agents/rules/outcome-boundary.md`
2. `.agents/rules/decision-gates.md`
3. `.agents/rules/development-workflow.md`
4. Relevant project, domain, code, and document owners.

Handling:

1. Restate the intended result in project terms.
2. Read the relevant project context and code paths.
3. Check whether the approach fits the existing architecture,
   source-of-truth boundaries, security model, verification model, and
   user-facing result.
4. Identify material gaps, risks, or simpler alternatives.
5. Ask for confirmation before editing when adopting the approach changes
   public behavior, persistence, environment setup, source-of-truth ownership,
   adapter behavior, verification, security, release scope, or AI protocol
   rules.
6. Proceed directly only for already-confirmed plans or local, reversible
   details with negligible impact, such as typos or small clarity fixes.

Effect:

1. User direction stays central, but partial solution sketches do not bypass
   architecture and contract review.
2. The AI explains design risk before turning it into code.
3. Confirmed decisions become durable rules, docs, or template changes.

Pain point solved:

In AI development, a user's concrete idea can be half requirement and half
implementation guess. This gate keeps the result orientation while preventing a
plausible but incomplete approach from hardening into product behavior.

### 6. Resolve Project And Domain Authority

Trigger:

1. The task touches architecture, source layout, public contracts, persistence,
   security, trace, milestone, domain terms, or durable facts.
2. The AI needs to know where a responsibility belongs.
3. A design or fix may change externally visible behavior.

Files:

1. `.agents/project/README.md`
2. `.agents/project/architecture-boundaries.md`
3. `.agents/project/project-structure.md`
4. `.agents/project/milestones.md`
5. `.agents/agent-feed.json` `verification_profile`
6. `.agents/domain/README.md`
7. `.agents/domain/concepts.md`
8. `.agents/domain/contracts.md`
9. `.agents/domain/source-of-truth.md`

Handling:

1. Read `.agents/project/README.md` first because it is the recall index for
   project-specific constraints. Choose the relevant indexed file by matching
   the current task against each file's description and trigger; do not load all
   project files by default.
2. Read `.agents/domain/README.md` when domain facts, contracts, durable
   ownership, or source-of-truth rules may matter. Choose the relevant indexed
   domain file the same way; do not load all domain files by default.
3. Use project files for repository-specific architecture, placement,
   verification, milestone, release, dependency, and security rules.
4. Use domain files for stable project concepts, public contracts, and durable
   source-of-truth ownership.
5. If a required public contract is missing from the canonical contract index,
   stop and ask unless the change is purely local implementation detail.
6. Treat generated project/domain files as scaffolds until repository evidence
   supports concrete guidance. When evidence is clear, replace scaffold-only
   sections with project-specific facts; ask the user only when the missing
   decision could affect future development results.
7. If `.feed-backup/` exists, read the newest backup's migration guide and
   manifest before project-specific development. Preserve decisive legacy AI
   workflows and project rules by migrating supported facts into project/domain
   files. Stop for the user when a legacy rule conflicts with Agent Feed,
   overlaps but could change the AI-development loop, or lacks enough evidence.
8. After feature, architecture, source layout, verification, persistence,
   security, public contract, domain, or ownership changes, review related
   project/domain files and update stale guidance in the same task.
9. If a project or domain markdown file is added, removed, renamed, or
   materially changed, update the corresponding README index in the same task.
   The docs verification gate checks that direct `.agents/project/*.md` and
   `.agents/domain/*.md` files are indexed.

Effect:

1. Reusable rules do not get polluted with one-project facts.
2. Project facts have a predictable home.
3. Public contracts and durable facts cannot be invented inside code.

Pain point solved:

Project-specific knowledge often lives only in chat or gets mixed into generic
prompts. The project/domain split makes ownership recoverable and prevents
cross-project rule drift.

### 7. Apply Decision Gates

Trigger:

1. A discovered gap, ambiguity, or improvement affects future development
   results.
2. A choice would change public behavior, CLI/API contracts, persistence,
   migration strategy, AI instruction entrypoints, source-of-truth boundaries,
   adapter behavior, verification gates, release packaging, dependencies,
   permissions, network behavior, destructive operations, product positioning,
   or scope.

File:

1. `.agents/rules/decision-gates.md`

Handling:

1. Stop before editing.
2. Present the problem.
3. Explain why it affects future development.
4. Offer concrete options.
5. Recommend one option if appropriate.
6. Default to stopping if the user does not confirm.
7. Once confirmed, update the relevant stable asset so the decision is durable.

Effect:

1. The human remains the owner of product, architecture, protocol, and
   source-of-truth decisions.
2. The AI cannot turn "I found a gap" into "I invented the policy".
3. Confirmed decisions become durable documentation instead of staying in chat.

Pain point solved:

AI assistants often silently resolve ambiguity in ways that later become hidden
architecture or product decisions. Decision gates force those choices into an
explicit confirmation path.

### 8. Implement Or Fix Within The Boundary

Trigger:

1. The task is classified as implementation.
2. The user asks for a fix.
3. A review gate finds issues inside the current Task Brief.

Files:

1. `.agents/skills/project-development/SKILL.md`
2. `.agents/skills/project-fix/SKILL.md`
3. `.agents/rules/development-workflow.md`
4. `.agents/rules/change-risk-gates.md`
5. `.agents/domain/contracts.md`

Handling:

1. Complete the Task Brief first.
2. Add implementation-specific fields: milestone, task type, owner module,
   public API touched, persistence touched, tests expected, comment impact, and
   forbidden changes.
3. Search for existing owners, helpers, adapters, tests, fixtures, validators,
   command patterns, or dependencies before building new code.
4. Trace upstream callers and downstream consumers before replacing behavior.
5. Implement the smallest scoped change.
6. Add or update tests for changed behavior, failure paths, boundaries, or
   invariants.
7. Stop if a new write target, contract boundary, verification gate, or
   out-of-scope change appears.

Effect:

1. Implementation is owner-aware and contract-aware.
2. Existing project patterns are reused before new abstractions are introduced.
3. Riskier actions are classified before they happen.
4. Hidden scope expansion is caught during work.

Pain point solved:

AI assistants frequently rewrite too much, add abstractions without need, or
ignore existing helpers. The development workflow makes reuse, ownership, and
smallest-scope implementation mandatory.

### 9. Use External Evidence Only When Needed

Trigger:

1. The task depends on external facts, current ecosystem practice, protocol
   behavior, API behavior, security guidance, or dependency selection.

File:

1. `.agents/rules/evidence-gates.md`

Handling:

1. Prefer current repository files first.
2. Prefer official docs, specifications, standards, or source repositories for
   external facts.
3. Use issue trackers, release notes, and changelogs when relevant.
4. Use secondary articles only for patterns or comparison.
5. Separate sourced facts from project-specific inference.
6. Do not import external frameworks wholesale into the repo.

Effect:

1. Claims based on external behavior are source-backed.
2. Current, unstable facts are not treated as memory.
3. External practices are adopted only when they improve reliability,
   verification, context recovery, security, speed without weakening review, or
   reduced drift.

Pain point solved:

AI assistants can confidently cite stale or generic ecosystem claims. Evidence
gates make external facts explicit and bounded.

### 10. Select Verification Evidence

Trigger:

1. Code, tests, contracts, project behavior, project structure, or AI protocol
   files change.
2. A test or verification command fails.
3. The assistant is about to claim the result is verified.

Files:

1. `.agents/rules/testing-gates.md`
2. `.agents/agent-feed.json` `verification_profile`

Handling:

1. Select the narrowest verification that proves the current task boundary.
2. Broaden verification when shared contracts or public surfaces are touched.
3. For documentation or AI protocol changes, check links, references, naming,
   sync requirements, and relevant consistency checks.
4. For local logic, run targeted tests and add coverage when needed.
5. For public API, module ports, persistence, or shared contracts, run targeted
   contract tests and usually the full local code gate.
6. On failure, classify it as product/code bug, stale test, environment/tooling
   issue, sandbox/permission issue, or unrelated pre-existing failure.
7. Do not weaken or delete tests unless the source of truth proves the test is
   stale.

Effect:

1. Verification is tied to the Task Brief instead of being a generic checkbox.
2. Failures are not hidden or hand-waved.
3. Final claims distinguish passed checks, skipped checks, and residual risk.

Pain point solved:

AI assistants often say "verified" after weak or unrelated checks. Testing gates
force evidence to match the actual boundary.

### 11. Run Code Or Design Review Gates

Trigger:

1. Code, refactor, fix, public contract, store contract, module port, tests, or
   project structure changed.
2. A design document, architecture plan, README, AGENTS, rule, domain file,
   project file, skill, or handoff document changed.

Files:

1. `.agents/rules/review-gates.md`
2. `.agents/skills/project-review/SKILL.md`
3. `.agents/skills/design-review/SKILL.md`
4. `.agents/skills/project-fix/SKILL.md`

Handling:

For code:

1. Run relevant checks.
2. Review milestone fit, project constraints, module ownership,
   public/internal boundaries, documented ownership, contract drift, tests,
   error handling, trace/audit anchors, and secret safety.
3. In pure review mode, report findings and do not edit.
4. In implementation mode, fix P0/P1 findings and default-fix P2 findings
   inside the current Task Brief when safe.

For design:

1. Rebuild the task boundary.
2. Check whether the document can drive the next development step without
   invented decisions.
3. Fix only blocking findings already supported by source-of-truth and inside
   the Task Brief.
4. Apply decision gates when a fix would require an unconfirmed contract,
   architecture, adapter, verification, source-of-truth, or product-scope
   choice.
5. Check whether README or project indexes need maintenance.

Effect:

1. The assistant reviews its own changes before final handoff.
2. Review findings are severity-classified and routed.
3. Design documents must be development-ready, not just polished.
4. Final handoff includes a Context Capsule with completed work, verification,
   session-state action, known gaps, next action, next reading, and constraints
   not to break.

Pain point solved:

AI-generated work often stops at "I changed files" without a quality gate or
next-action clarity. Review gates make completion auditable.

### 12. Maintain Session State Or Promote Stable Guidance

Trigger:

1. Context compression could dilute information needed for the next action.
2. A long-running task has unresolved next action, blocker, or pending
   validation.
3. The user confirms or rejects a rule, boundary, or documentation
   responsibility.
4. The user corrects future AI development behavior.
5. A repeated AI failure becomes stable guidance.

Files:

1. `.agents/rules/session-state.md`
2. `.agents/session-state/README.md`
3. `.agents/session-state/schema.json`
4. `.agents/skills/guidance-promoter/SKILL.md`

Handling:

1. Store only `current_task` and short `carry_forwards`.
2. Keep at most seven carry-forwards.
3. Each carry-forward must explain content, why it must survive compression,
   and when it expires.
4. Do not store transcripts, facts already in stable docs, completed tasks, or
   low-value notes.
5. Promote durable cross-session conclusions into rules, project constraints,
   domain docs, skills, README, or design docs.
6. Remove session-state entries once they expire or are promoted.
7. Final handoff must always decide whether session state was updated, cleaned,
   promoted, or not needed, and why.

Effect:

1. Long-running work can resume after context compression.
2. Session state does not become a noisy memory system.
3. Stable guidance moves into durable source-of-truth files.

Pain point solved:

AI chats lose important decisions after compression, but full transcripts are too
noisy. Session state preserves only the active handoff facts needed to continue.

### 13. Optional Specialist Agent Profiles

Trigger:

1. A task benefits from a narrow checker or worker.
2. The assistant or user delegates a scoped subtask.

File:

1. `.agents/agents/README.md`

Handling:

1. Use profiles only when useful.
2. Require narrow responsibility and explicit required reading.
3. Require actionable findings with file/line references when possible.
4. Do not let profiles modify files unless assigned a write set.

Effect:

1. Delegated work remains scoped.
2. Specialist checks do not become competing entry contracts.

Pain point solved:

Delegation can create unbounded parallel work. Agent profiles constrain delegated
responsibility.

## Trigger Matrix

| Situation | Triggered file or workflow | Required handling | Effect |
| --- | --- | --- | --- |
| New AI session starts | `AGENTS.md` | Read mandatory startup and apply priority order | Consistent entry across AI clients |
| Context was compressed | `outcome-boundary`, `session-state` | Recover boundary and relevant handoff card | Continuity without transcript replay |
| User asks for a small deterministic edit | `outcome-boundary` task class gate | Treat as direct action after boundary recovery | Avoid unnecessary planning ceremony |
| User asks for implementation | `project-development`, `development-workflow` | Fill Task Brief and implementation addendum | Scoped implementation with owner/test clarity |
| User asks for bug fix | `project-fix` | Reproduce or trace, locate owner, smallest fix | Fix addresses root cause, not symptom only |
| User asks for code review | `project-review` | Pure review mode, findings first, no edits | Review does not mutate code unexpectedly |
| AI changes code as part of work | `review-gates` code review gate | Run checks and review boundaries/tests/security | Implementation has internal quality gate |
| AI edits README, rules, domain, project docs, or plans | `design-review` | Check if next development can proceed without invented decisions | Design becomes actionable, not just polished |
| A gap affects future behavior | `decision-gates` | Stop, present options, wait for confirmation | Human owns contract/scope/protocol decisions |
| Work touches external facts or dependencies | `evidence-gates` | Use source priority and separate facts from inference | Reduces stale or generic recommendations |
| Work touches public contract or durable fact | `domain/contracts`, `source-of-truth` | Read canonical contract owner or stop if missing | Prevents hallucinated contracts |
| Work touches project architecture, structure, release, verification, dependency, or security rules | `.agents/project/README.md` | Read the project index, then the relevant indexed file only | Project-specific ownership stays local without full-context loading |
| Work touches domain concepts, public contracts, durable facts, or source-of-truth ownership | `.agents/domain/README.md` | Read the domain index, then the relevant indexed file only | Domain facts are recoverable without loading every domain document |
| AI uses built-in or reviewed skills | `check-agent-trust.sh`, `$AGENT_FEED_HOME/config.json` | Stop if a managed skill or protocol script hash changed unexpectedly | Prevents silently following tampered trusted guidance |
| User imports, edits, or removes a skill | `skill-hub`, `skills`, `index-skills`, `.agents/skills/README.md` | Fill missing metadata, remove stale index/trust entries, and keep custom skills advisory | Extends capability without letting external guidance override core rules |
| User proposes a concrete implementation plan | User-proposed approach gate | Assess against code, contracts, and decision gates before editing | Avoids turning partial solution sketches into hidden product decisions |
| Work changes AI protocol assets | `testing-gates`, `review-gates` | Verify links, names, mirrors, indexes, session JSON | Protocol health is evidence-backed |
| Work involves git review or commit handoff | `git-collaboration` | Review diff, keep commit scope clean, use concise imperative messages | Supports team development without mixing unrelated changes |
| User correction should persist | `guidance-promoter` | Decide stable asset versus session-state | Repeated failures become stable guidance |
| Final handoff | `session-state` Final Handoff Gate | State completion, verification, session state, gaps, next action | Next turn can resume cleanly |

## Pain Point Coverage

| Pain point | Protocol mechanism | Why it works |
| --- | --- | --- |
| Different AI clients follow different instructions | `AGENTS.md` plus thin adapters | One canonical entry contract; clients point back to it. |
| AI starts coding before knowing the stop condition | `outcome-boundary` and Task Brief | Goal, stop, write set, and verification are explicit before edits. |
| Simple tasks get over-planned | Task class gate | Direct actions can proceed with a light process. |
| Hard tasks proceed without enough planning | Task class gate plus design readiness | Architecture/contract work must become development-ready first. |
| AI invents product or architecture decisions | `decision-gates` | Future-affecting choices require human confirmation. |
| AI follows a changed trusted skill without noticing | `check-agent-trust.sh` plus external trust state | Changed built-in/reviewed skills and managed scripts interrupt the workflow before use. |
| Imported skills override project rules | Skill index metadata and priority rules | Missing metadata defaults to `source: unknow`, `trust: custom`; custom skills are advisory only. |
| User-proposed partial solutions bypass design review | User-proposed approach gate | The AI must inspect project context, evaluate fit, and ask when future behavior changes. |
| Project facts pollute reusable rules | `.agents/project/` | Repository-specific constraints have a user-maintained lane. |
| Public contracts are buried in code or chat | `.agents/domain/contracts.md` | Contract changes must point to an authoritative owner or stop. |
| AI rebuilds existing helpers | `development-workflow` reuse-before-build | Existing owners, dependencies, and patterns are checked first. |
| Verification is vague | `testing-gates` | Tests are selected by task boundary and failures must be classified. |
| Review is skipped | `review-gates` and review skills | Code and design changes have mandatory post-change review. |
| Context compression loses decisions | `session-state` | Every final handoff decides whether active facts must be preserved and later cleaned. |
| Session state becomes noisy memory | Carry-forward limits and promotion rules | Only active facts survive; durable guidance moves to stable docs. |
| User corrections disappear | `guidance-promoter` | Corrections are classified and promoted into the right asset. |

## Related Reading

This document explains the workflow loop itself. The adjacent public docs are:

1. `docs/template-model.md`: canonical structure, adapters, settings, trust ownership, and skill import boundaries.
2. `examples/basic-output.md`: the generated repository shape after `agent-feed init`.
3. `examples/live-protocol/README.md`: the actual protocol files used to build Agent Feed itself.

## Practical Reading Order

To understand or debug the protocol quickly, read in this order:

1. `src/agent_feed/templates/standard/AGENTS.md`
2. `src/agent_feed/templates/standard/.agents/README.md`
3. `src/agent_feed/templates/standard/.agents/rules/outcome-boundary.md`
4. `src/agent_feed/templates/standard/.agents/rules/context-loading.md`
5. `src/agent_feed/templates/standard/.agents/rules/decision-gates.md`
6. `src/agent_feed/templates/standard/.agents/rules/development-workflow.md`
7. `src/agent_feed/templates/standard/.agents/rules/testing-gates.md`
8. `src/agent_feed/templates/standard/.agents/rules/review-gates.md`
9. `src/agent_feed/templates/standard/.agents/rules/session-state.md`
10. `src/agent_feed/templates/standard/.agents/project/README.md`
11. `src/agent_feed/templates/standard/.agents/domain/README.md`
12. `src/agent_feed/templates/standard/.agents/skills/*/SKILL.md`

The mental model is simple: entry first, boundary second, routing third, source
of truth fourth, action fifth, verification/review sixth, handoff last.
