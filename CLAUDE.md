# CLAUDE.md — Developer Guide for AI Agents

This file provides authoritative guidance for AI coding agents (Claude, Copilot, etc.) working in this repository.

---

## Repository Identity

- **Package:** `pubsublib` (PyPI)
- **Language:** Python ≥ 3.8
- **Purpose:** Opinionated AWS SNS/SQS + Redis pub/sub abstraction for Orange Health microservices
- **Build system:** Hatchling (`pyproject.toml`)

---

## Directory Map

```
pubsublib-python/
├── src/
│   ├── __init__.py                         # namespace root
│   └── pubsublib/
│       ├── __init__.py                     # package init
│       ├── aws/
│       │   ├── __init__.py
│       │   ├── main.py                     # AWSPubSubAdapter — primary public class
│       │   ├── exceptions.py               # custom exceptions
│       │   └── utils/
│       │       └── helper.py               # attribute binding, validation, MD5, size check
│       └── common/
│           ├── cache_adapter.py            # Redis wrapper (CacheAdapter)
│           └── codec.py                    # gzip+base64 encode/decode utilities
├── docs/
│   └── architecture/
│       ├── overview.md                     # high-level system diagram and key decisions
│       ├── service-layer.md                # class and method reference
│       ├── integrations.md                 # SNS, SQS, Redis integration details
│       ├── configuration.md                # all config parameters and env vars
│       ├── observability.md                # logging, trace_id, metrics
│       └── branching.md                    # branching strategy and versioning
├── .github/
│   ├── CODEOWNERS                          # @architv @rdvs @raj-nt
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│       └── python-publish.yml              # publish to PyPI on v* tag
├── pyproject.toml                          # project metadata, dependencies, version
├── publish.sh                              # manual publish helper script
├── README.md
├── CLAUDE.md                               # this file
└── AGENTS.md                               # agent-specific conventions
```

---

## Architectural Layering

```
┌─────────────────────────────────────────┐
│           Caller / Consumer Service     │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│         AWSPubSubAdapter                │  ← src/pubsublib/aws/main.py
│   (public API: create, publish, poll,   │
│    subscribe, tag, fetch)               │
└──────┬──────────┬───────────┬───────────┘
       │          │           │
┌──────▼──┐  ┌───▼───┐  ┌────▼──────────┐
│ helper  │  │ codec │  │ CacheAdapter  │
│ (utils) │  │       │  │ (Redis)       │
└──────┬──┘  └───────┘  └───────────────┘
       │
┌──────▼──────────────────────────────────┐
│         boto3 (SNS + SQS clients)       │
└─────────────────────────────────────────┘
```

Rules:
- `aws/main.py` is the **only** public interface. Do not add public functions to `helper.py` or `codec.py`.
- `common/` modules must remain **AWS-agnostic**. Do not import boto3 there.
- `codec.py` must remain **pure functions** (no state, no I/O).
- `cache_adapter.py` must not reference SNS/SQS.

---

## Coding Conventions

### Python Style
- Type hints on all public method signatures
- Docstrings on all public methods (existing style: `:param x:` / `:return:`)
- Private methods prefixed with `__` (name-mangled) inside `AWSPubSubAdapter`
- Use `logger = logging.getLogger(__name__)` in every module that logs
- Never configure logging handlers inside the library

### Required Message Attributes
Every published event **must** include:
- `source` — originating service name
- `contains` — data entity type
- `event_type` — event discriminator
- `trace_id` — auto-generated UUID v4 if not supplied by the caller

Validation is enforced in `helper.validate_message_attributes`.

### Large-Message Handling
Messages > 64 KB are automatically offloaded to Redis. The Redis key is stored in `attributes["redis_key"]`. Do not change the 64 KB threshold without updating `helper.is_large_message` and the docs.

### Compression
Controlled by `compress_enabled` on the adapter instance (or `PUBSUBLIB_COMPRESSION_ENABLED` env var). When enabled, the message body is gzip+base64 encoded and `attributes["compress"] = "true"` is set. Consumers check this flag before decompressing.

---

## Adding a New Feature

1. **Branch** from `dev`: `git checkout -b feature/OH-<JIRAID>-<short-desc>`
2. **Add functionality** in the appropriate module:
   - New transport/cloud provider → create `src/pubsublib/<provider>/` mirroring the `aws/` structure
   - New utility → add to the relevant `common/` or `utils/` module
   - New public method → add to `AWSPubSubAdapter` with type hints and docstring
3. **Update docs** if you change the public API, configuration options, or message attribute contract
4. **Bump the version** in `pyproject.toml` following `YY.MMDD.PATCHCOUNT`
5. **PR to `dev`** using the PR template; ensure CODEOWNER approval

---

## Adding a New Cloud Provider

The library is structured for multi-provider expansion. To add, for example, a GCP Pub/Sub adapter:

1. Create `src/pubsublib/gcp/__init__.py`
2. Create `src/pubsublib/gcp/main.py` with a `GCPPubSubAdapter` class exposing the same public method signatures as `AWSPubSubAdapter`
3. Create `src/pubsublib/gcp/exceptions.py` for provider-specific exceptions
4. Reuse `src/pubsublib/common/codec.py` and `src/pubsublib/common/cache_adapter.py` unchanged
5. Add provider-specific dependencies to `pyproject.toml`
6. Document in `docs/architecture/integrations.md`

---

## Versioning

Format: `YY.MMDD.PATCHCOUNT`  
Release candidates: `RC-YY.MMDD.BUILDCOUNT`  
Update `version` in `pyproject.toml`; create a matching git tag `v<version>` on `main` to trigger PyPI publish.

---

## Running Locally

```bash
pip install hatchling boto3 botocore redis
pip install -e .
```

For local AWS emulation, use [LocalStack](https://localstack.cloud/):
```bash
docker run -d -p 4566:4566 localstack/localstack
```

Pass `sns_endpoint_url="http://localhost:4566"` and `sqs_endpoint_url="http://localhost:4566"` to the adapter.

---

## Key Files to Read First

When starting a task, read in this order:
1. `src/pubsublib/aws/main.py` — the entire public API
2. `src/pubsublib/aws/utils/helper.py` — validation and attribute rules
3. `src/pubsublib/common/codec.py` — compression pipeline
4. `src/pubsublib/common/cache_adapter.py` — Redis contract
5. `docs/architecture/overview.md` — overall design rationale
