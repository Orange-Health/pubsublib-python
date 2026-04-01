# AGENTS.md — Agent Conventions

This file is intended for AI coding agents (OpenAI Codex, GitHub Copilot Workspace, Cursor, etc.) working in this repository. It complements `CLAUDE.md` with agent-specific rules and quick-reference information.

---

## Repository at a Glance

| Property | Value |
|---|---|
| Language | Python ≥ 3.8 |
| Package name | `pubsublib` |
| Primary source root | `src/pubsublib/` |
| Public API entry point | `src/pubsublib/aws/main.py` → `AWSPubSubAdapter` |
| Build tool | Hatchling (`pyproject.toml`) |
| CI/CD | GitHub Actions (`.github/workflows/python-publish.yml`) — triggers on `v*` tags |

---

## Boundaries — What You Must NOT Do

- **Do not add boto3 imports to `common/`** — `common/` is provider-agnostic
- **Do not add state or I/O to `codec.py`** — it must remain pure functions
- **Do not create new public functions in `helper.py`** unless they are utilities reusable across the `aws/` layer
- **Do not modify the required attribute set** (`source`, `contains`, `event_type`, `trace_id`) without updating both `helper.validate_message_attributes` and `docs/architecture/observability.md`
- **Do not change the `PUBSUB:` key prefix** in `CacheAdapter` without a migration plan
- **Do not push directly to `main`** — all changes go through PRs targeting `dev`

---

## Required Attribute Contract

Every SNS publish call **must** include these attributes or `validate_message_attributes` will raise:

```python
attributes = {
    "source":     "your-service-name",
    "contains":   "entity-name",
    "event_type": "created|updated|deleted|...",
    # trace_id is auto-generated if omitted
}
```

---

## Module Responsibilities (Quick Reference)

| Module | What it does | What it doesn't do |
|---|---|---|
| `aws/main.py` | All SNS/SQS API calls, compression pipeline orchestration, Redis offload orchestration | No direct Redis or codec logic |
| `aws/utils/helper.py` | Attribute binding, validation, MD5 integrity, 64 KB size check | No AWS API calls |
| `aws/exceptions.py` | Custom exception definitions | No logic |
| `common/cache_adapter.py` | Redis connection pool, namespaced get/set/delete | No AWS knowledge |
| `common/codec.py` | gzip compress/decompress, base64 encode/decode | No state, no AWS, no Redis |

---

## Branching Rules (Summary)

| Branch type | Naming | Branch from | Merges into |
|---|---|---|---|
| Feature | `feature/<JIRAID>-<name>` | `dev` | `dev` |
| Hotfix | `hotfix/<JIRAID>-<desc>` | `main` | `main` + `dev` + active `release/*` |
| Release | `release/<YY.MMDD>` | `dev` | `main` + `dev` |

Versioning: `YY.MMDD.PATCHCOUNT` (production), `RC-YY.MMDD.BUILDCOUNT` (release candidate), `stag-<desc>` (staging).

---

## When Making Changes

### Changing `publish_message` or the publish pipeline
1. Read `__publish_message_standard_queue` and `__publish_message_fifo_queue` — both must be kept in sync
2. Verify compression + large-message logic applies to both paths
3. Update `docs/architecture/overview.md` sequence diagram if the flow changes

### Changing message consumption (`poll_*`)
1. Both `poll_message_from_queue` (SNS envelope) and `poll_raw_message_from_queue` (raw delivery) must handle Redis retrieval and decompression
2. Update `docs/architecture/overview.md` consume sequence diagram

### Changing `CacheAdapter`
1. Preserve the `PUBSUB:` prefix on all keys
2. Verify TTL behaviour — large messages use 14 400 minutes (10 days)

### Changing `codec.py`
1. Keep all functions pure (no side effects)
2. Maintain INFO-level logging with byte count fields for observability
3. `gzip_and_b64` (publish) and `b64_decode_and_gunzip_if` (consume) are the primary pipeline functions

### Bumping the version
1. Update `version` in `pyproject.toml`
2. Follow scheme `YY.MMDD.PATCHCOUNT`
3. Tag on `main` as `v<version>` to trigger PyPI publish

---

## PR Checklist

Before opening a PR, verify:
- [ ] Type hints present on all new/modified public methods
- [ ] Docstrings updated or added
- [ ] `validate_message_attributes` still enforces `source`, `contains`, `event_type`
- [ ] Both standard and FIFO paths handled if changing publish/poll
- [ ] Architecture docs updated if the public API or data flow changed
- [ ] `pyproject.toml` version bumped if the change warrants a release
- [ ] PR description follows `.github/PULL_REQUEST_TEMPLATE.md`

---

## Documentation Files

| File | Update when |
|---|---|
| `docs/architecture/overview.md` | Public API change, new dependency, data flow change |
| `docs/architecture/service-layer.md` | New/modified class, method, or parameter |
| `docs/architecture/integrations.md` | New external integration or change to SNS/SQS/Redis contract |
| `docs/architecture/configuration.md` | New constructor parameter or environment variable |
| `docs/architecture/observability.md` | New log event, new required attribute, new metric recommendation |
| `docs/architecture/branching.md` | Change to branching model or versioning scheme |
| `CLAUDE.md` | Change to directory structure, layering rules, or on-boarding instructions |
| `AGENTS.md` | Change to agent-specific conventions |
