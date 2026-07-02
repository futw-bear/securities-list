# Repository Guidelines

## Project Purpose

This repository maintains a Taiwan securities list that is automatically fetched, parsed, versioned, and exposed through program-friendly APIs. Treat source exchange data as the authority, and keep generated outputs deterministic so downstream users can rely on stable diffs and reproducible releases.

## Expected Structure

The repository is currently in its initialization stage. Prefer this layout as the project grows:

- `.github/workflows/`: scheduled and manual GitHub Actions for data refresh, validation, and publishing.
- `src/` or `scripts/`: fetchers, parsers, validators, and release helpers.
- `data/raw/`: downloaded source files when they are intentionally committed.
- `data/generated/`: normalized JSON, CSV, or other API-ready artifacts.
- `tests/`: parser fixtures, schema checks, and regression cases.
- `docs/`: API contract notes and data-source documentation.

Do not commit secrets, access tokens, or machine-local cache files.

## Development Commands

Document new commands in `README.md` as soon as they are introduced. Until a toolchain is selected, prefer conventional script names:

- `test`: run all parser, schema, and fixture tests.
- `lint`: run formatting and static checks.
- `build`: regenerate API-ready artifacts from checked-in fixtures or source data.
- `update`: fetch the latest upstream securities data and regenerate outputs.

If commands require network access, keep tests able to run offline by using fixtures.

## Data And API Contracts

Generated outputs should be deterministic: sort records by a stable security identifier, use consistent field names, and avoid timestamp churn unless the timestamp is part of the public contract. Preserve enough source metadata to audit where each record came from, including source URL, fetch date, and parser version when applicable.

When changing API fields, update documentation and add migration notes. Prefer additive changes over breaking changes. If a breaking change is necessary, explain the compatibility impact in the pull request.

## Testing Expectations

Add focused fixture tests for every parser rule, especially edge cases such as suspended securities, renamed securities, delisted records, duplicate identifiers, non-ASCII names, and missing optional fields. Validate generated files against schemas before publishing them from GitHub Actions.

For automation changes, verify both scheduled and manual workflow paths where possible. Keep workflows idempotent so rerunning a job does not create unrelated diffs.

## Commit And Pull Request Guidelines

Use concise, imperative commit messages, for example `Add TWSE parser fixture` or `Normalize generated JSON order`. Pull requests should describe the data source touched, the generated artifacts changed, and the validation performed.

Before merging, ensure the working tree only contains intentional changes. Avoid broad refactors while changing parser behavior unless the refactor is required for the parser change.
