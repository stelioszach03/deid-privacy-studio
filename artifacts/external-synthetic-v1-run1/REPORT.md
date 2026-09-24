# DeID external synthetic evaluation — 24 September 2026

**Strict exact-span and mapped-label F1: 40.21%** on 500 fixed external synthetic records. Precision 39.29%; recall 41.17%. This is a measured limitation of the current library engine, not a claim of production readiness.

The run completed at `2026-09-24T02:42:36.113956+00:00`, after frozen protocol `d6d4ae2081a2de3d243cec1c7f11b032bfcaaa34646c2c5aad098504de5c2048`. Engine source commit: `c56f9592a8c00e2c88831c0ebfd6963913f819a9`. No engine parameters or labels were tuned against this sample.

## Coverage and scoring

The sample spans 194 templates and 944 gold entities. 855 entities (90.57%) map to the 12 scored categories. Counts: TP=352, FP=544, FN=503. Macro F1 over gold-supported categories: 53.77%.

Exact Unicode-codepoint boundaries and mapped labels are required. A partial address or differently bounded name is an error under this protocol, even if some sensitive characters were removed. These scores are not a character-removal rate or clinical privacy guarantee.

| Mapped category | Gold spans | TP | FP | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ADDRESS | 207 | 1 | 1 | 206 | 50.00% | 0.48% | 0.96% |
| CREDIT_CARD | 47 | 40 | 0 | 7 | 100.00% | 85.11% | 91.95% |
| DATE | 44 | 34 | 192 | 10 | 15.04% | 77.27% | 25.19% |
| EMAIL | 21 | 21 | 0 | 0 | 100.00% | 100.00% | 100.00% |
| GPE | 134 | 57 | 50 | 77 | 53.27% | 42.54% | 47.30% |
| IBAN | 4 | 4 | 0 | 0 | 100.00% | 100.00% | 100.00% |
| IP | 6 | 6 | 1 | 0 | 85.71% | 100.00% | 92.31% |
| ORG | 69 | 20 | 147 | 49 | 11.98% | 28.99% | 16.95% |
| PERSON | 269 | 158 | 100 | 111 | 61.24% | 58.74% | 59.96% |
| PHONE | 39 | 4 | 13 | 35 | 23.53% | 10.26% | 14.29% |
| SSN | 6 | 6 | 1 | 0 | 85.71% | 100.00% | 92.31% |
| ZIP | 9 | 1 | 39 | 8 | 2.50% | 11.11% | 4.08% |

Unsupported gold categories, retained in the coverage ledger: AGE=21, DOMAIN_NAME=13, NRP=24, TITLE=31. US_DRIVER_LICENSE is also unsupported but has zero occurrences in this fixed sample.

Engine categories without matching corpus annotation support, excluded from primary precision and separately counted: LOC=5, SIN_CA=2, URL=13. Their exclusion is prespecified; this is not evidence that these detections were correct.

The clearest gaps are full-address recall and noisy DATE/ORG predictions. The corpus contains international address/phone formats while this engine emphasizes US/Canadian patterns. Exact aggregate address spans differ from component location detections. Small perfect-category results (EMAIL=21 gold, IBAN=4) do not establish general accuracy. No outcome-based record exclusions or relaxed boundary scoring were applied.

## Local CPU timing and Unicode stress

Python 3.11.15; spaCy 3.8.7; en_core_web_sm 3.8.0; Darwin / arm64. One process; no GPU or paid API. Per-document latency includes detection and transformation, excluding model load and warm-up. p50=2.108 ms, p95=4.341 ms, max=6.882 ms. Model loading: 143.799 ms. These are this machine's measurements, not HTTP latency or a throughput guarantee.

| Authored stress case length (codepoints) | Expected emails | Exact email matches | Latency (ms) | Valid spans / email removed |
| ---: | ---: | ---: | ---: | --- |
| 51 | 1 | 1 | 1.865 | True / True |
| 5100 | 100 | 100 | 80.365 | True / True |
| 51000 | 1000 | 1000 | 837.177 | True / True |
| 204000 | 4000 | 4000 | 3613.448 | True / True |

The 500,001-codepoint input was rejected: **True**. Stress texts use authored repeated content; they assess offset handling and bounded processing, not independent language accuracy.

## Provenance and limits

- Dataset: [Presidio-research synthetic fixture at pinned revision](https://github.com/data-privacy-stack/presidio-research/blob/6db3769a3388b4075b93ab2229c5e0b9c30137f7/data/synth_dataset_v2.json). Repository MIT; upstream separately attributes Fake Name Generator identities to Fake Name Generator / Corban Works, LLC under CC BY-SA 3.0 US.
- The raw corpus is not redistributed. Per-document artifacts contain row indices, text hashes, counts and timings only, without text, detected values or raw span annotations.
- A first preflight failed before processing any record because the resolved environment omitted `click`; `click==8.1.8` was installed, then the same frozen engine/evaluator/sample ran once. The zero-record failure receipt is retained in the adjacent `external-synthetic-v1` directory.
- Synthetic templates are correlated; this is a small convenience benchmark and not clinical, population-representative, legal-compliance or calibrated-privacy evidence. No confidence intervals or significance claims.
- The engine combines pretrained spaCy with hand-written patterns. No new NER model was trained. Pretraining contamination is unknown.
- This evaluates the repository library. The separately deployed adapter, HTTP service and browser review workflow were not benchmarked here.
- Weak results remain in the record as measured. Improvements should use distinct development data and a new frozen evaluation, retaining this baseline.

Full source/model hashes, package versions, sample indices and metrics: `protocol.json`, `results.json`, `documents.jsonl` in this directory. See the [frozen protocol](../../docs/evaluation/EXTERNAL_SYNTHETIC_PROTOCOL.md).
