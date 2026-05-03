# Release Checklist

Agent Feed publishes to PyPI through GitHub Trusted Publishing.

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

## Regular Release

1. Update `pyproject.toml` version.
2. Update `CHANGELOG.md` for the same version.
3. Run local verification:

   ```sh
   AGENT_FEED_HOME=/private/tmp/agent-feed-trust-home sh .agents/scripts/verify-agent-dev.sh full
   uv build
   ```

4. Remove stale local distributions before final packaging:

   ```sh
   rm -rf dist
   uv build
   ```

5. Check package metadata:

   ```sh
   uvx twine check dist/*
   ```

6. Commit and push to `main`.
7. Confirm GitHub CI is green.
8. Create a GitHub Release with a tag matching the version, for example `v0.1.2`.
9. Publishing starts automatically when the GitHub Release is published.
10. Confirm the publish workflow succeeds.
11. Verify the install after PyPI updates:

    ```sh
    uv tool install agent-feed
    agent-feed --version
    agent-feed --help
    ```

## Notes

- PyPI versions are immutable. Do not publish until the version, README, and package metadata are final.
- Do not commit local `dist/` contents or private deploy keys.
- Use a new patch version for any follow-up fix after publishing.
