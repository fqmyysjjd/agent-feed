# Basic Generated Output

This example shows the shape of a small project after `agent-feed init`.

## Before

```text
example-api/
  pyproject.toml
  src/
  tests/
```

## Command

```sh
cd example-api
agent-feed init --project-name "Example API" --clients claude,cursor --profile python
```

## After

```text
example-api/
  AGENTS.md
  CLAUDE.md
  .agents/
    README.md
    agent-feed.json
    agents/
    domain/
      README.md
      concepts.md
      contracts.md
      source-of-truth.md
    project/
      README.md
      milestones.md
      project-structure.md
      verification-commands.sh
    rules/
      change-risk-gates.md
      context-loading.md
      decision-gates.md
      development-workflow.md
      evidence-gates.md
      outcome-boundary.md
      review-gates.md
      session-state.md
      testing-gates.md
    scripts/
      check-agent-assets.sh
      check-agent-trust.sh
      index-skills.sh
      sync-agent-assets.sh
      verify-agent-dev.sh
    session-state/
      README.md
      schema.json
    skills/
      README.md
      concept-review/
      design-review/
      guidance-promoter/
      project-architecture/
      project-development/
      project-fix/
      project-review/
      skill-maintainer/
  .claude/
    skills/
      ...
  .cursor/
    rules/
      agent-feed.mdc
```

## What To Edit First

1. Put repository-specific constraints in `.agents/project/README.md` and related files under `.agents/project/`.
2. Put stable domain concepts and contracts in `.agents/domain/`.
3. Use `agent-feed config set verification_profile custom` if the selected profile does not match the real project test commands, then edit `.agents/project/verification-commands.sh`.
4. Set `AGENT_FEED_HOME` to an external directory, then run `agent-feed index-skills -y` after reviewing generated AI-development assets.
5. Run `agent-feed check` after editing generated AI-development assets.

## Expected Result

After initialization, AI coding tools should start from the same canonical entrypoint, recover the current task boundary, route to the relevant rules or skills, stop before unconfirmed decisions, and report verification evidence before claiming completion.
