# Testing Gates

Use this rule when AI-assisted development changes code, tests, contracts, project behavior, project structure, or AI engineering protocol files.

Testing is evidence for the current task boundary. It is not a checkbox or a substitute for design review.

## Test Selection

Choose the narrowest tests that prove the current task boundary, then broaden when the change touches shared surfaces.

1. Documentation or AI protocol only:
   - Check links, references, naming rules, sync requirements, and relevant consistency scripts.
   - Run `sh .agents/scripts/verify-agent-dev.sh docs`.
2. Local pure logic or shared utility:
   - Run targeted tests for the changed function or invariant.
   - Add a test when changed behavior has no existing coverage.
3. Public API, public types, module ports, persistence contracts, or other shared contracts:
   - Run targeted contract tests.
   - Run the project full code gate unless the task boundary explicitly limits verification and residual risk is reported.
4. Bug fix, review finding fix, or regression fix:
   - Prefer a test that would fail before the fix and pass after it.

## New Code Test Gate

When new code, tests, commands, modules, public behavior, or implementation paths are added, the AI assistant must define the concrete test flow before claiming the task is complete.

For every non-trivial code addition, answer:

```md
| Item | Content |
| --- | --- |
| Changed behavior | What user-visible, internal, or contract behavior changed |
| Existing test pattern | Existing test, fixture, helper, or command pattern reused |
| New or updated test | Test file/function or reason no test change is needed |
| Proof | Why this test proves the changed behavior and not only that code executes |
| Command | Exact command that must be run |
| Broader verification | Whether targeted tests are enough or code/full verification is required |
```

Do not add tests only to exercise implementation details. Prefer tests that prove behavior, boundary preservation, error handling, regression prevention, or integration with an existing command/profile.

If no test is added for new code, state the reason and run the narrowest existing verification that proves the changed behavior. If no existing verification proves it, add or request a test before final completion.

## Failure Handling

When a test or verification command fails:

1. Do not hide the failure.
2. Classify the failure as product/code bug, stale test, environment/tooling issue, sandbox/permission issue, or unrelated pre-existing failure.
3. Trace the failure to the owner module and contract before editing broad code.
4. Do not weaken or delete a test unless the source of truth proves the test is stale.
5. If verification cannot run, state the exact command, reason, and residual risk in the final handoff.

## Verification Entry

Use `sh .agents/scripts/verify-agent-dev.sh <scope>` when it matches the current Task Brief:

1. `docs`: AI engineering docs, `.agents/` links, session-state JSON, and skill mirrors.
2. `code`: project-specific code gate. The stable entrypoint is `.agents/scripts/verify-agent-dev.sh`; configure custom project commands in `.agents/project/verification-commands.sh`.
3. `full`: docs checks plus code gate.

The script does not choose scope for the AI. Select the narrowest sufficient scope and report any skipped broader checks.
