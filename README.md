# DeID Privacy Studio

Policy-governed PHI/PII redaction for clinical and financial text: 25 entity types, per-label mask/hash/redact policies, spaCy NER layered on a prioritized regex ladder.

**[Live demo](https://stelioszach.com/demos/deid/)**

[![CI](https://github.com/stelioszach03/deid-privacy-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/stelioszach03/deid-privacy-studio/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-f59e0b?style=flat-square)](LICENSE)

## Results

| Claim | Value | Evidence |
|---|---|---|
| Entity types | 25 labels | [`app/deid/engine.py`](app/deid/engine.py) `POLICY_MAP` |
| Policy actions | `mask` (width-preserving `*`), `hash` (salted SHA-256), `redact` (`[REDACTED:LABEL]`) | [`app/deid/policies.py`](app/deid/policies.py) |
| Span resolution | deterministic by `(priority, length, start)` — structured IDs beat NER spans | [`app/deid/recognizers.py`](app/deid/recognizers.py) |
| Detection precision / recall | **not measured** | — |

The 25 labels: `ADDRESS`, `CREDIT_CARD`, `DATE`, `DEA`, `EMAIL`, `GPE`, `HEALTH_CARD_CA`, `HICN`, `IBAN`, `IP`, `LOC`, `MRN`, `NPI`, `ORG`, `PASSPORT_US`, `PERSON`, `PHONE_INTL`, `PHONE_US`, `POSTAL_CA`, `ROUTING`, `SIN_CA`, `SSN`, `URL`, `US_STREET`, `ZIP_US`.

**No detection quality is measured.** For PHI redaction the number that matters is recall per label — a false negative is a leak — and this repo does not have one. `scripts/evaluate.py` computes per-label P/R/F1/FNR, but the only labelled data present is `scripts/dataset.jsonl`: 20 synthetic records whose label set (`AMKA`, `PHONE_GR`) predates the current `POLICY_MAP`. Treat this as a working redaction engine, not a validated one.

## Run

```bash
docker compose up -d --build
docker compose exec -T api alembic upgrade head
open http://localhost:8000
```

Local venv:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && python -m spacy download en_core_web_sm
alembic upgrade head && uvicorn app.main:app --reload
pytest -q
```

All `/api/v1/*` routes require an `X-API-Key` header. `POST /api/v1/deid` redacts a text block and returns per-entity spans and actions; `POST /api/v1/deid/file` handles multipart uploads; `GET`/`PUT /api/v1/config` read and override the policy map at runtime; Celery-backed jobs live under `/api/v1/jobs/`.

## Limitations

- **No measured precision or recall**, per above. This must not be run on real PHI.
- **English only.** The spaCy model is `en_core_web_sm` and the regex ladder covers US and Canadian identifier formats.
- **A regex ladder is not a recall guarantee.** Any format outside the ladder — unusual MRN schemes, international addresses — is silently missed.
- **`hash` is deterministic by design.** A fixed `DEID_SALT` keeps hashes joinable across datasets, which also makes low-cardinality fields vulnerable to a dictionary attack. Rotate the salt per release if that matters.
- Policy edits via `PUT /api/v1/config` are in-memory and reset on restart.

## License

MIT — see [LICENSE](LICENSE).
