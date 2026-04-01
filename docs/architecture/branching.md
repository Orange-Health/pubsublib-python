# Branching Strategy

This document describes the Git branching model, versioning scheme, and merge conventions for `pubsublib-python`.

---

## Branch Overview

| Branch | Purpose | Merges Into | Source Branch |
|---|---|---|---|
| `main` | Production-ready code; PyPI releases cut from here | — | hotfix only |
| `dev` | Integration branch; all features merge here first | `main` (via release) | — |
| `release/*` | Release stabilisation | `main` + `dev` | `dev` |
| `feature/<JIRAID>-<name>` | Individual features or improvements | `dev` | `dev` |
| `hotfix/<JIRAID>-<desc>` | Critical production fixes | `main` + `dev` + `release/*` | `main` |

---

## Gitflow Diagram

```mermaid
gitGraph
   commit id: "init" tag: "24.0101.0"

   branch dev
   checkout dev
   commit id: "dev: base"

   branch feature/OH-101-compression
   checkout feature/OH-101-compression
   commit id: "feat: gzip codec"
   commit id: "feat: compress flag"
   checkout dev
   merge feature/OH-101-compression id: "merge OH-101"

   branch feature/OH-102-raw-poll
   checkout feature/OH-102-raw-poll
   commit id: "feat: raw poll method"
   checkout dev
   merge feature/OH-102-raw-poll id: "merge OH-102"

   branch release/24.0315
   checkout release/24.0315
   commit id: "chore: bump 24.0315.0" tag: "RC-24.0315.1"
   commit id: "fix: release polish"
   checkout main
   merge release/24.0315 id: "release 24.0315.0" tag: "24.0315.0"
   checkout dev
   merge release/24.0315 id: "back-merge release"

   checkout main
   branch hotfix/OH-210-fifo-name-check
   checkout hotfix/OH-210-fifo-name-check
   commit id: "fix: FIFO name validation"
   checkout main
   merge hotfix/OH-210-fifo-name-check id: "hotfix merge main" tag: "24.0315.1"
   checkout dev
   merge hotfix/OH-210-fifo-name-check id: "hotfix back-merge dev"
```

---

## Branch Naming Conventions

### Feature Branches
```
feature/<JIRAID>-<short-description>
```
- Always branch from `dev`
- Merge back into `dev` via pull request
- Delete after merge

**Examples:**
```
feature/OH-101-compression-support
feature/OH-155-filter-policy
feature/OH-200-redis-ttl-config
```

### Hotfix Branches
```
hotfix/<JIRAID>-<short-description>
```
- Always branch from `main`
- Merge into: `main`, `dev`, and the active `release/*` branch (if one exists)
- Triggers a patch version increment

**Examples:**
```
hotfix/OH-210-fifo-name-check
hotfix/OH-222-redis-connection-leak
```

### Release Branches
```
release/<YY.MMDD>
```
- Branched from `dev` when a release is being prepared
- Only bug fixes and release chores committed here
- Merged into `main` (tagged) and back-merged into `dev`

---

## Versioning Scheme

### Production Release
```
YY.MMDD.PATCHCOUNT
```

| Segment | Description | Example |
|---|---|---|
| `YY` | 2-digit year | `24` |
| `MMDD` | Zero-padded month and day | `0315` |
| `PATCHCOUNT` | Sequential patch increment for the day; starts at `0` | `0`, `1`, `2` |

Examples: `24.0315.0`, `24.0315.1`, `26.0401.0`

### Release Candidate
```
RC-YY.MMDD.BUILDCOUNT
```
Tagged on the `release/*` branch during stabilisation.

Examples: `RC-24.0315.1`, `RC-26.0401.2`

### Staging / Exploratory Tags
```
stag-<description>
```
Used for internal staging deployments, not published to PyPI.

Examples: `stag-compression-test`, `stag-fifo-validation`

---

## PyPI Publishing

Releases are published to PyPI automatically by the GitHub Actions workflow (`.github/workflows/python-publish.yml`) when a tag matching `v*` is pushed to `main`:

```
git tag v24.0315.0
git push origin v24.0315.0
```

The workflow:
1. Checks out the tagged commit
2. Builds the package with `python -m build`
3. Publishes via `pypa/gh-action-pypi-publish` using the `PYPI_API_TOKEN` secret

---

## Pull Request Rules

- All PRs target either `dev` (features) or `main` (hotfixes)
- At least one CODEOWNER approval is required (see `.github/CODEOWNERS`)
- PRs must follow the `.github/PULL_REQUEST_TEMPLATE.md` format
- Direct pushes to `main` are not permitted except for hotfix merges by CODEOWNERS
