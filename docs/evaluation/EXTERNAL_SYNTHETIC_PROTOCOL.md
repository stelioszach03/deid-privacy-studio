# External synthetic evaluation protocol v1

Freeze before first inference. Evaluate the unchanged library engine at its current committed source revision; record engine and evaluator source hashes. No detector edits, threshold search, new NER model, API calls or external transmission of text.

## Dataset and license

Use [Presidio-research `data/synth_dataset_v2.json`](https://github.com/data-privacy-stack/presidio-research/blob/6db3769a3388b4075b93ab2229c5e0b9c30137f7/data/synth_dataset_v2.json), revision `6db3769a3388b4075b93ab2229c5e0b9c30137f7`, SHA-256 `ec08a771ba8135314cafb60752b2295212222ba3a4cd75d73811839c699e0012`. It has 1,500 synthetic annotated records. [Upstream documentation](https://github.com/data-privacy-stack/presidio-research/blob/6db3769a3388b4075b93ab2229c5e0b9c30137f7/README.md) describes fake PII generation and identifies the fixture. Repository code is [MIT licensed](https://github.com/data-privacy-stack/presidio-research/blob/6db3769a3388b4075b93ab2229c5e0b9c30137f7/LICENSE); the README separately attributes Fake Name Generator identities under **CC BY-SA 3.0 US** to Fake Name Generator / Corban Works, LLC. Do not label all dataset content MIT. No raw texts or identities will be redistributed here; publish aggregate metrics, row indices/hashes and license/source links only.

Select 500 row indices by ascending SHA-256 bytes of `deid-external-v1:17:{index}`. Freeze the selected index list and combined-record hash. Do not filter by text, label, locale, detector success or template. This is a bounded external synthetic evaluation sample, not a new independently sampled clinical test set. The fixture is not used to train or tune this engine during the study; pretrained spaCy contamination is unknown. Related templates may appear multiple times, so no independent-document confidence interval is claimed.

## Runtime

CPU; spaCy 3.8.7 and `en_core_web_sm` 3.8.0. Require the NER model to load; abort rather than silently use regex-only fallback. Record installed package versions and model-file hashes. Run the actual `DeidEngine.deidentify` with the unchanged default policy map, a fixed synthetic-only salt and a 500,000-codepoint limit. No database/API/worker services needed. Wall-clock limit: 600 seconds for actual engine evaluation.

## Scoring fixed before inference

Primary: exact **Unicode codepoint start, end and mapped entity label** precision/recall/F1. No boundary trimming, token overlap, fuzzy matching, relaxed intersection, confidence threshold tuning or post-result remapping.

Gold → common label: `STREET_ADDRESS→ADDRESS`, `ORGANIZATION→ORG`, `PERSON→PERSON`, `GPE→GPE`, `DATE_TIME→DATE`, `CREDIT_CARD→CREDIT_CARD`, `US_SSN→SSN`, `ZIP_CODE→ZIP`, `EMAIL_ADDRESS→EMAIL`, `PHONE_NUMBER→PHONE`, `IBAN_CODE→IBAN`, `IP_ADDRESS→IP`. Predictions map `US_STREET/ADDRESS→ADDRESS`, `PHONE_US/PHONE_INTL→PHONE`, `ZIP_US→ZIP`; other supported labels keep the common name.

Gold labels `AGE`, `TITLE`, `NRP`, `DOMAIN_NAME`, `US_DRIVER_LICENSE` have no directly equivalent supported engine category and are counted separately. Engine categories without a matching annotation schema (e.g. MRN, DEA, LOC, Canadian identifiers, URL) are also counted separately and excluded from primary precision rather than assuming those annotations are complete. Report both counts and supported gold coverage. All mapped predictions are scored across all selected texts, including false detections on unsupported-gold records. No record is dropped. A label/boundary mismatch contributes one false positive and one false negative.

Report micro counts/metrics and per-label TP/FP/FN/P/R/F1. Undefined precision/recall is null; F1 is zero when gold exists but no true positive; a completely unobserved label has null F1. Macro F1 averages only labels represented in gold. This evaluates detection spans, not irreversible anonymization or legal compliance. Partial full-address recognition is a strict miss, even when some location text was removed.

## Latency and robustness

Measure model load separately, then one fixed synthetic warm-up. Per-document `perf_counter_ns` surrounds `DeidEngine.deidentify`, including transformations; record p50/p95 nearest-rank, maximum and all 500 timings. One CPU process, no concurrency throughput claim.

Separate engineering stress cases repeat an authored block containing an emoji, Greek, an accented character, a combining mark, Japanese and `demo@example.org`, 1/100/1000/4000 times. Check exact EMAIL offsets, all spans in codepoint bounds, source email removal and latency. These are authored stress cases, not independent accuracy data. Also verify rejection of 500,001 codepoints. No raw dataset text or detected strings enter published reports.

## Reproduction

Fetch the exact public fixture to a local scratch directory, validate its hash, and install the pinned model/runtime. Freeze once, then run with a fresh output directory:

```sh
python scripts/evaluate_external.py --dataset /local/dataset.json --freeze /local/frozen.json
python scripts/evaluate_external.py --dataset /local/dataset.json --run /local/frozen.json --output /local/results
```

The evaluator refuses changed dataset, sample, source or protocol hashes. Published results must retain unfavorable outcomes and limitations. Follow-up improvements require a new version and separate evaluation data rather than changing this frozen run.
