# Release Checklist

Agent Feed publishes to PyPI through GitHub Trusted Publishing.
The npm workflow currently verifies the TypeScript package on release builds,
but the registry publish step stays disabled until the Node CLI reaches public
command parity with the Python runtime.

Current npm parity covers the non-network lifecycle/config foundation:
`init`, `sync`, `preview`, `upgrade`, `check`, `status`, `config get/set/check/prune`,
`env status/setup/print/uninstall`, and `index-skills`. Keep npm publishing
disabled until `skill-hub`, legacy backup migration, and richer interactive behavior are intentionally
ported or explicitly declared out of scope.

## One-Time PyPI Setup

Create a PyPI pending publisher before the first release:

1. Project name: `agent-feed`
2. Owner: `fqmyysjjd`
3. Repository: `agent-feed`
4. Workflow: `publish.yml`
5. Environment: `pypi`

The GitHub workflow is `.github/workflows/publish.yml`.

If the project already exists on PyPI later, configure the same trusted
publisher under that project's publishing settings instead of creating a
pending publisher.

## One-Time npm Setup

Prepare npm trusted publishing for the `agent-feed` package before enabling the
registry publish step:

1. Package name: `agent-feed`
2. Owner: `fqmyysjjd`
3. Repository: `agent-feed`
4. Workflow: `publish.yml`

npm trusted publishing requires GitHub Actions OIDC, npm CLI 11.5.1 or newer,
and Node 22.14.0 or newer. Keep the release publish job on Node 24 even though
the package runtime supports older Node versions.

## Regular Release

1. Update `pyproject.toml` version.
2. Update root `package.json` version to match.
3. Update `CHANGELOG.md` for the same version.
5. Run local verification:

   ```sh
   AGENT_FEED_HOME=/private/tmp/agent-feed-trust-home sh .agents/scripts/verify-agent-dev.sh full
   uv build
   npm ci
   npm run build:all
   npm run check
   ```

6. Remove stale local distributions before final packaging:

   ```sh
   rm -rf dist
   uv build
   ```

7. Check package metadata:

   ```sh
   uvx twine check dist/*
   npm run pack:dry-run
   ```

8. Commit and push to `main`.
9. Confirm GitHub CI is green.
10. Create a GitHub Release with a tag matching the version, for example `v1.0.0`.
11. PyPI publishing starts automatically when the GitHub Release is published.
12. Confirm the PyPI publish job and the npm verification job succeed.
13. Verify installs after registry updates:

    ```sh
    uv tool install agent-feed
    agent-feed --version
    agent-feed --help
    ```

## Notes

- PyPI and npm versions are immutable. Do not publish until the version, README, and package metadata are final.
- Keep `pyproject.toml` and root `package.json` versions identical. The Node CLI reads its version from `package.json`.
- Do not commit local `dist/` contents or private deploy keys.
- Use a new patch version for any follow-up fix after publishing.
