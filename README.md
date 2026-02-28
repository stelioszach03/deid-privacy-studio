<div align="center">

[![CI](https://github.com/stelioszach03/deid-privacy-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/stelioszach03/deid-privacy-studio/actions)

# Aegis DeID — PHI / PII Redaction Studio

**Policy-governed de-identification for clinical and financial text with 20+ entity types, per-label mask/hash/redact policies, and an interactive side-by-side studio.**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![spaCy](https://img.shields.io/badge/spaCy-NER-09A3D5?style=flat-square&logo=spacy&logoColor=white)](https://spacy.io/)
[![Redis](https://img.shields.io/badge/Redis-Celery-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-f59e0b?style=flat-square)](LICENSE)

**[Live Studio](https://stelioszach.com/aegis-deid/)**  ·  **[API Health](https://stelioszach.com/aegis-deid/api/v1/health)**  ·  **[API Docs](https://stelioszach.com/aegis-deid/docs)**

</div>

---

## What it detects

The engine layers a spaCy NER pipeline (`en_core_web_sm`) on top of a
prioritized regex ladder (`app/deid/regex_rules.py`). Overlapping spans are
resolved deterministically by `(priority, length, start)`, so structured
identifiers always beat noisier NER spans.

| Group              | Labels                                                            | Default action |
| ------------------ | ----------------------------------------------------------------- | -------------- |
| Contact            | `EMAIL`                                                           | hash           |
|                    | `PHONE_US`, `PHONE_INTL`                                          | mask           |
| Government IDs     | `SSN`, `SIN_CA`, `NPI`, `DEA`, `PASSPORT_US`                      | hash           |
| Healthcare         | `MRN`, `HICN`, `HEALTH_CARD_CA`                                   | hash           |
| Financial          | `CREDIT_CARD`, `ROUTING`, `IBAN`                                  | mask           |
| Location           | `US_STREET`, `ZIP_US`, `POSTAL_CA`, `GPE`, `LOC`, `ADDRESS`       | redact         |
| Temporal           | `DATE`                                                            | mask           |
| Technical          | `URL`, `IP`                                                       | redact         |
| NER (spaCy)        | `PERSON`, `ORG`                                                   | redact         |

The full policy map lives in `app/deid/engine.py::POLICY_MAP` and can be
overridden at runtime via `PUT /api/v1/config`.

## Policy actions

| Action   | Behavior                                           | Output sample               |
| -------- | -------------------------------------------------- | --------------------------- |
| `mask`   | Replace every char with `*` (preserves width)      | `**************`            |
| `hash`   | SHA-256 over `salt + value`, prefixed with label   | `SSN_HASH:7d1c45…a23988e`   |
| `redact` | Swap with `[REDACTED:LABEL]`                       | `[REDACTED:PERSON]`         |

Hashing is deterministic with a configurable salt (`DEID_SALT` env var), so
you can still join or count across hashed datasets.

---

## Quickstart

### Docker Compose (preferred)

```bash
# 1) Bring services up (api, worker, redis, postgres)
docker compose up -d --build

# 2) Apply DB migrations
docker compose exec -T api alembic upgrade head

# 3) Open the UI
open http://localhost:8000
```

### Local venv

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Migrations (requires local Postgres)
alembic upgrade head

# API
uvicorn app.main:app --reload

# (Optional) worker for async eval jobs
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO
```

---

## API

All endpoints live under `/api/v1` and require an `X-API-Key` header (or a
cookie with the same name set on the index route in dev mode).

### `POST /api/v1/deid`

Redact a single block of text.

```bash
curl -sX POST http://localhost:8000/api/v1/deid \
  -H 'X-API-Key: change-me' \
  -H 'Content-Type: application/json' \
  -d '{"text": "Patient Eleanor Whitfield, SSN 412-55-7891, phone (617) 555-0134", "lang_hint": "en"}'
```

```json
{
  "original_len": 62,
  "result_text": "Patient [REDACTED:PERSON], SSN SSN_HASH:7d1c…88e, phone **************",
  "entities": [
    { "label": "PERSON",   "span": [8, 26], "action": "redact" },
    { "label": "SSN",      "span": [32, 43], "action": "hash"   },
    { "label": "PHONE_US", "span": [52, 66], "action": "mask"   }
  ],
  "time_ms": 12
}
```

### `POST /api/v1/deid/file`

Multipart file upload — returns one `DeidResult` per file.

### `GET /api/v1/config` · `PUT /api/v1/config`

Read / update the in-memory policy map and default policy.

### `GET /api/v1/health`

Liveness probe, exempt from auth.

### `POST /api/v1/jobs/deid` · `POST /api/v1/jobs/evaluate` · `GET /api/v1/jobs/{id}`

Celery-backed job queue for long-running evaluation runs against golden
datasets. Results land in Postgres (`metric_runs` table).

---

## Architecture

```
client ──▶ fastapi ──▶ require_api_key + rate_limit + body_limit
                │
                ▼
         deid engine  ──▶ spaCy NER (en_core_web_sm)
                │         prioritized regex ladder
                │         dedupe by (priority, length, start)
                │
                ▼
         POLICY_MAP  ──▶ mask / hash / redact per label
                │
                ▼
         { result_text, entities[], time_ms }

async eval jobs ──▶ celery ──▶ redis broker ──▶ worker ──▶ postgres MetricRun
```

Key modules:

- `app/deid/regex_rules.py` — the prioritized pattern library.
- `app/deid/recognizers.py` — spaCy + regex fusion, MRN overdetection guard.
- `app/deid/engine.py` — `DeidEngine.deidentify(text)` returning a
  `DeidResult` with per-entity spans and actions.
- `app/deid/policies.py` — `mask_value`, `hash_value`, `redact_value` helpers.
- `app/api/v1.py` — Pydantic schemas + routes.
- `app/ui/templates/index.html` + `static/app.js` — interactive redaction desk
  with side-by-side highlighted output and an audit ledger of detected spans.

---

## Configuration

All settings live in `app/core/config.py` and are read from `.env`.

| Variable                 | Default                        | Purpose                                |
| ------------------------ | ------------------------------ | -------------------------------------- |
| `API_KEY`                | `change-me`                    | Required on all `/api/v1/*` routes     |
| `DEID_SALT`              | `changeme-salt`                | SHA-256 salt for `hash` action          |
| `DEID_DEFAULT_POLICY`    | `mask`                         | Fallback when a label is not in map    |
| `MAX_TEXT_SIZE`          | `200000`                       | Char limit per request                 |
| `REQUEST_BODY_LIMIT`     | `1000000`                      | Hard body-size cap (1 MB)              |
| `CORS_ALLOW_ORIGINS`     | `http://localhost:8000`        | Comma-separated allowlist              |
| `POSTGRES_DSN`           | `postgresql+psycopg://…`       | Metrics + eval job persistence         |
| `REDIS_URL`              | `redis://localhost:6379/0`     | Celery broker / rate limiter backend   |

---

## Testing & coverage

```bash
# Unit + integration (hits local Postgres if available)
pytest -q

# Inside docker
docker compose exec -T api pytest -q
```

Covered areas:

- Pattern ladder: every label has a positive + negative test
  (`tests/test_regex_rules.py`).
- Recognizer: dedupe priority, MRN overdetection guard, NER fusion
  (`tests/test_recognizers.py`).
- Engine: policy resolution, deterministic hashing, `MAX_TEXT_SIZE` guard,
  action mapping (`tests/test_engine.py`).
- API: health, config round-trip, single + batch `/deid`, oversize 413
  (`tests/test_api.py`).
- Golden dataset counts (`tests/golden/test_golden_cases.py`).

---

## Screenshots

- Redaction desk with side-by-side source/output and highlighted spans
- Audit ledger of detected entities, filterable by label / action / length
- Policy / architecture panel in the footer of the single-page UI

---

## License

MIT — see [`LICENSE`](./LICENSE).

Built by **Stelios Zacharioudakis** as a portfolio-grade study in privacy
engineering: entity recognition, policy orchestration and deterministic span
rewriting. Part of the **Aegis suite**:

- [Graph Fraud Command Center](https://github.com/stelioszach03/graph-fraud-command-center) — GNN-based payment fraud detection
- [NYC Subway Anomaly](https://github.com/stelioszach03/nyc-subway-anomaly) — streaming anomaly detection on live transit
- [AML Graph Investigator](https://github.com/stelioszach03/aml-graph-investigator) — graph-native AML case explainer
- **Aegis DeID** — this repo
