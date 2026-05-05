# Release Checklist

Agent Feed publishes one canonical Python implementation to PyPI through GitHub
Trusted Publishing. The npm package is only a thin wrapper: it bootstraps the
same PyPI version into a local Python virtual environment during npm install
and then delegates `agent-feed` to `python -m agent_feed.cli`.

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

Prepare npm trusted publishing for the `agent-feed` wrapper package:

1. Package name: `agent-feed`
2. Owner: `fqmyysjjd`
3. Repository: `agent-feed`
4. Workflow: `publish.yml`

npm trusted publishing requires GitHub Actions OIDC, npm CLI 11.5.1 or newer,
and Node 22.14.0 or newer. Keep the release publish job on Node 24 even though
the package runtime supports older Node versions.

## One-Time Homebrew Setup

Homebrew installs Agent Feed from the published PyPI source distribution through
the custom tap at `fqmyysjjd/homebrew-tap`.

The current user-facing install command is:

```sh
brew install fqmyysjjd/tap/agent-feed
```

Before the first automated tap update, confirm:

1. `fqmyysjjd/homebrew-tap` exists.
2. `Formula/agent-feed.rb` exists in that tap.
3. The main repository has a `HOMEBREW_TAP_TOKEN` GitHub Actions secret with
   write access to `fqmyysjjd/homebrew-tap`.
4. The tap formula validates locally:

   ```sh
   brew style fqmyysjjd/tap/agent-feed
   brew install --build-from-source fqmyysjjd/tap/agent-feed
   brew test fqmyysjjd/tap/agent-feed
   brew audit --strict --online fqmyysjjd/tap/agent-feed
   ```

The release workflow updates the tap after PyPI publishing succeeds. The
Homebrew job reads the version from `pyproject.toml`, waits for the versioned
PyPI `sdist`, updates the formula URL, checksum, and Python resources, validates
the formula with Homebrew, then commits and pushes the formula change to the tap.

Manual fallback for a failed tap update:

1. PyPI has the new `agent-feed` source distribution.
2. The formula URL points to that immutable PyPI `sdist`.
3. The formula `sha256` matches the PyPI `sdist` digest.
4. Python resources are regenerated from the published package.
5. Local Homebrew validation passes:

   ```sh
   brew install --build-from-source fqmyysjjd/tap/agent-feed
   brew test fqmyysjjd/tap/agent-feed
   brew audit --strict --online fqmyysjjd/tap/agent-feed
   ```

## Regular Release

1. Update `pyproject.toml` version.
2. Update root `package.json` version to match.
3. Update `CHANGELOG.md` for the same version.
4. Run local verification:

   ```sh
   AGENT_FEED_HOME=/private/tmp/agent-feed-trust-home sh .agents/scripts/verify-agent-dev.sh full
   uv build
   npm run pack:dry-run
   ```

5. Remove stale local distributions before final packaging:

   ```sh
   rm -rf dist
   uv build
   ```

6. Check package metadata:

   ```sh
   uvx twine check dist/*
   npm run pack:dry-run
   ```

7. Commit and push to `main`.
8. Confirm GitHub CI is green.
9. Create a GitHub Release with a tag matching the version, for example `v1.0.0`.
10. PyPI publishing starts automatically when the GitHub Release is published.
11. The npm wrapper publish and Homebrew tap update start automatically after
    the PyPI job succeeds.
12. Confirm the PyPI publish job, npm publish job, and Homebrew tap update job succeed.
13. Verify installs after registry and tap updates:

    ```sh
    brew install fqmyysjjd/tap/agent-feed
    npm install -g agent-feed
    uv tool install agent-feed
    agent-feed --version
    agent-feed --help
    ```

## Notes

- PyPI and npm versions are immutable. Do not publish until the version, README, and package metadata are final.
- Keep `pyproject.toml` and root `package.json` versions identical. The npm
  wrapper installs the matching PyPI version from `package.json`.
- Do not commit local `dist/` contents or private deploy keys.
- Use a new patch version for any follow-up fix after publishing.
