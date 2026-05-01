# Verification Profile

Default verification entry:

```sh
sh .agents/scripts/verify-agent-dev.sh <scope>
```

Scopes:

1. `docs`: AI engineering docs, links, session-state JSON, and skill mirrors.
2. `code`: selected project code gate.
3. `full`: `docs` plus selected project code gate.

{{VERIFICATION_PROFILE_DOC}}

## Change Rule

If the selected profile does not match the repository's actual test, lint, type-check, build, or smoke-test commands, update `.agents/scripts/verify-agent-dev.sh` before claiming `code` or `full` verification passed.
