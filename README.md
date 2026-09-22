# DeID Privacy Studio

A text-redaction prototype for exploring entity detection, overlap resolution and configurable privacy transformations on synthetic English-language examples.

## Implementation

[The engine](app/deid/engine.py) supports 25 policy labels and three actions: width-preserving masking, salted SHA-256 pseudonyms and explicit redaction markers. [Recognizers](app/deid/recognizers.py) combine prioritized US/Canadian identifier patterns with an optional spaCy English NER model. Structured patterns take precedence when spans overlap.

Unknown policy actions are rejected by both the API schema and engine instead of silently returning the original value. Policy changes are in-memory and reset on restart. The API provides text/file processing, configuration and optional Celery jobs.

## Run locally

```bash
cp .env.example .env
# Set API_KEY and a fresh DEID_SALT in .env before exposing the API.
docker compose up -d --build
docker compose exec -T api alembic upgrade head
```

For a Python environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn app.main:app --reload
```

The default development URL is `http://localhost:8000`. When configured, `API_KEY` protects `/api/v1/*` except health; an empty key intentionally permits demo access. Never expose that default to sensitive data.

## Verification and scope

Run `python -m pytest` for the repository suite. The regex/policy/API subset runs without model downloads; database/worker tests require their services, and NER behavior requires the spaCy model. The tests isolate rate-limit state so a deliberate 429 test does not affect later requests.

No representative per-label precision/recall evaluation is available. The committed 20-record synthetic generator fixture includes older Greek labels that do not match the current English-focused policy map. The engine falls back to regex-only detection when NER is unavailable; unrecognized names or identifier formats can remain in the output. Deterministic hashes remain linkable and are not anonymization.

This is not a clinical tool, a privacy guarantee, or evidence of HIPAA/GDPR/PIPEDA compliance. Use synthetic examples, not patient records or private financial data.

MIT licensed. See [LICENSE](LICENSE).
