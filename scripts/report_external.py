#!/usr/bin/env python3
"""Regenerate the aggregate-only external synthetic evaluation report."""
import argparse
import json
from pathlib import Path


def percent(value):
    return "unmeasured" if value is None else f"{100 * value:.2f}%"


def report(directory):
    result = json.loads((directory / "results.json").read_text())
    docs = [json.loads(line) for line in (directory / "documents.jsonl").read_text().splitlines()]
    if len(docs) != result["sample_rows"] or len({r["dataset_index"] for r in docs}) != len(docs):
        raise ValueError("Document inventory does not reconcile")
    for key in ("tp", "fp", "fn"):
        if sum(row[key] for row in docs) != result["micro"][key] or sum(row[key] for row in result["per_label"].values()) != result["micro"][key]:
            raise ValueError("Recorded metric totals do not reconcile")
    m, latency = result["micro"], result["latency_ms"]
    lines = ["# DeID external synthetic evaluation — 24 September 2026", "",
        f"**Strict exact-span and mapped-label F1: {percent(m['f1'])}** on {result['sample_rows']} fixed external synthetic records. Precision {percent(m['precision'])}; recall {percent(m['recall'])}. This is a measured limitation of the current library engine, not a claim of production readiness.", "",
        f"The run completed at `{result['completed_at_utc']}`, after frozen protocol `{result['freeze_sha256']}`. Engine source commit: `{result['engine_commit']}`. No engine parameters or labels were tuned against this sample.", "",
        "## Coverage and scoring", "",
        f"The sample spans {result['templates']} templates and {result['gold_spans_all_labels']} gold entities. {result['gold_spans_supported_mapping']} entities ({percent(result['supported_gold_coverage'])}) map to the 12 scored categories. Counts: TP={m['tp']}, FP={m['fp']}, FN={m['fn']}. Macro F1 over gold-supported categories: {percent(result['macro_f1_gold_supported_labels'])}.", "",
        "Exact Unicode-codepoint boundaries and mapped labels are required. A partial address or differently bounded name is an error under this protocol, even if some sensitive characters were removed. These scores are not a character-removal rate or clinical privacy guarantee.", "",
        "| Mapped category | Gold spans | TP | FP | FN | Precision | Recall | F1 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for label, row in sorted(result["per_label"].items()):
        lines.append(f"| {label} | {row['tp'] + row['fn']} | {row['tp']} | {row['fp']} | {row['fn']} | {percent(row['precision'])} | {percent(row['recall'])} | {percent(row['f1'])} |")
    lines.extend(["", "Unsupported gold categories, retained in the coverage ledger: " + ", ".join(f"{k}={v}" for k, v in sorted(result["unsupported_gold_counts"].items())) + ". US_DRIVER_LICENSE is also unsupported but has zero occurrences in this fixed sample.", "",
        "Engine categories without matching corpus annotation support, excluded from primary precision and separately counted: " + ", ".join(f"{k}={v}" for k, v in sorted(result["unscored_prediction_counts"].items())) + ". Their exclusion is prespecified; this is not evidence that these detections were correct.", "",
        "The clearest gaps are full-address recall and noisy DATE/ORG predictions. The corpus contains international address/phone formats while this engine emphasizes US/Canadian patterns. Exact aggregate address spans differ from component location detections. Small perfect-category results (EMAIL=21 gold, IBAN=4) do not establish general accuracy. No outcome-based record exclusions or relaxed boundary scoring were applied.", "",
        "## Local CPU timing and Unicode stress", "",
        f"Python {result['runtime']['python']}; spaCy {result['runtime']['spacy']}; en_core_web_sm {result['runtime']['model']}; {result['runtime']['os']} / {result['runtime']['architecture']}. One process; no GPU or paid API. Per-document latency includes detection and transformation, excluding model load and warm-up. p50={latency['p50_nearest_rank']:.3f} ms, p95={latency['p95_nearest_rank']:.3f} ms, max={latency['max']:.3f} ms. Model loading: {latency['model_load']:.3f} ms. These are this machine's measurements, not HTTP latency or a throughput guarantee.", "",
        "| Authored stress case length (codepoints) | Expected emails | Exact email matches | Latency (ms) | Valid spans / email removed |",
        "| ---: | ---: | ---: | ---: | --- |"])
    for case in result["long_unicode_stress"]:
        lines.append(f"| {case['unicode_codepoints']} | {case['expected_emails']} | {case['exact_email_matches']} | {case['latency_ms']:.3f} | {case['all_output_spans_in_bounds']} / {case['source_email_removed']} |")
    lines.extend(["", f"The 500,001-codepoint input was rejected: **{result['rejects_500001_characters']}**. Stress texts use authored repeated content; they assess offset handling and bounded processing, not independent language accuracy.", "",
        "## Provenance and limits", "",
        "- Dataset: [Presidio-research synthetic fixture at pinned revision](https://github.com/data-privacy-stack/presidio-research/blob/6db3769a3388b4075b93ab2229c5e0b9c30137f7/data/synth_dataset_v2.json). Repository MIT; upstream separately attributes Fake Name Generator identities to Fake Name Generator / Corban Works, LLC under CC BY-SA 3.0 US.",
        "- The raw corpus is not redistributed. Per-document artifacts contain row indices, text hashes, counts and timings only, without text, detected values or raw span annotations.",
        "- A first preflight failed before processing any record because the resolved environment omitted `click`; `click==8.1.8` was installed, then the same frozen engine/evaluator/sample ran once. The zero-record failure receipt is retained in the adjacent `external-synthetic-v1` directory.",
        "- Synthetic templates are correlated; this is a small convenience benchmark and not clinical, population-representative, legal-compliance or calibrated-privacy evidence. No confidence intervals or significance claims.",
        "- The engine combines pretrained spaCy with hand-written patterns. No new NER model was trained. Pretraining contamination is unknown.",
        "- This evaluates the repository library. The separately deployed adapter, HTTP service and browser review workflow were not benchmarked here.",
        "- Weak results remain in the record as measured. Improvements should use distinct development data and a new frozen evaluation, retaining this baseline.", "",
        "Full source/model hashes, package versions, sample indices and metrics: `protocol.json`, `results.json`, `documents.jsonl` in this directory. See the [frozen protocol](../../docs/evaluation/EXTERNAL_SYNTHETIC_PROTOCOL.md).", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    (args.directory / "REPORT.md").write_text(report(args.directory))
    print("Regenerated report; document and per-label counts reconcile.")
