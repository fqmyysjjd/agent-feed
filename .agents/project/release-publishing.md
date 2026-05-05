# Release Publishing

This file defines Agent Feed's repository-specific release and package
publishing constraints.

## Version Source Of Truth

The GitHub Release tag is the release version source of truth.

For a release tag such as `v1.0.1`, the publish workflow must build and publish
version `1.0.1` across PyPI, npm, and Homebrew.

## Required Automation

1. Before building release artifacts, `.github/workflows/publish.yml` must run
   `scripts/sync-release-version.py "$GITHUB_REF_NAME"`.
2. The sync script must update:
   - `pyproject.toml`
   - `src/agent_feed/__init__.py`
   - `package.json`
   - `package-lock.json`
3. The PyPI job must build from the synchronized Python metadata.
4. The npm job must publish the synchronized `@yysjjd/agent-feed` package.
5. The Homebrew job must resolve the version from `GITHUB_REF_NAME`, wait for
   the matching PyPI sdist, then update `fqmyysjjd/homebrew-tap`.
6. The publish workflow must be safe to rerun after a partial release:
   - PyPI publishing uses `skip-existing`.
   - npm publishing checks whether `@yysjjd/agent-feed@<version>` already
     exists before publishing.
   - Homebrew updates must work after PyPI has already published the release
     version.

## Package Name Constraints

1. PyPI package name remains `agent-feed`.
2. npm package name is `@yysjjd/agent-feed`; npm blocks the unscoped
   `agent-feed` name as too similar to an existing package.
3. The installed CLI command remains `agent-feed`.

## Stop Rules

Stop and ask before:

1. Changing the release version source of truth away from the GitHub Release
   tag.
2. Publishing an npm package under a different package name.
3. Reintroducing manual-only version bump steps as the required release path.
4. Changing PyPI, npm, or Homebrew publishing order.
5. Changing trusted-publisher, provenance, or token requirements.
6. Removing partial-release rerun safety from PyPI, npm, or Homebrew jobs.
