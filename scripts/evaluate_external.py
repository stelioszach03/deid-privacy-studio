#!/usr/bin/env python3
"""Frozen aggregate-only evaluation on a pinned external synthetic fixture."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import platform
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA_SHA = "ec08a771ba8135314cafb60752b2295212222ba3a4cd75d73811839c699e0012"
REVISION = "6db3769a3388b4075b93ab2229c5e0b9c30137f7"
GOLD_MAP = {"STREET_ADDRESS": "ADDRESS", "ORGANIZATION": "ORG", "PERSON": "PERSON",
    "GPE": "GPE", "DATE_TIME": "DATE", "CREDIT_CARD": "CREDIT_CARD", "US_SSN": "SSN",
    "ZIP_CODE": "ZIP", "EMAIL_ADDRESS": "EMAIL", "PHONE_NUMBER": "PHONE",
    "IBAN_CODE": "IBAN", "IP_ADDRESS": "IP"}
PRED_MAP = {"US_STREET": "ADDRESS", "ADDRESS": "ADDRESS", "ORG": "ORG", "PERSON": "PERSON",
    "GPE": "GPE", "DATE": "DATE", "CREDIT_CARD": "CREDIT_CARD", "SSN": "SSN",
    "ZIP_US": "ZIP", "EMAIL": "EMAIL", "PHONE_US": "PHONE", "PHONE_INTL": "PHONE",
    "IBAN": "IBAN", "IP": "IP"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    files = list((ROOT / "app/deid").glob("*.py")) + [ROOT / "app/core/config.py", Path(__file__), ROOT / "docs/evaluation/EXTERNAL_SYNTHETIC_PROTOCOL.md"]
    return {str(p.relative_to(ROOT)): file_sha(p) for p in sorted(files)}


def selection(total):
    return sorted(range(total), key=lambda i: hashlib.sha256(f"deid-external-v1:17:{i}".encode()).digest())[:500]


def load_dataset(path):
    if file_sha(path) != DATA_SHA:
        raise ValueError("Pinned dataset hash mismatch")
    data = json.loads(path.read_text())
    if len(data) != 1500:
        raise ValueError("Unexpected dataset count")
    for record in data:
        text = record["full_text"]
        for span in record["spans"]:
            start, end = span["start_position"], span["end_position"]
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text) or text[start:end] != span["entity_value"]:
                raise ValueError("Invalid annotation; do not silently discard it")
    return data


def freeze(path, data):
    selected = selection(len(data))
    document = {"protocol": "deid-external-synthetic-v1", "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_sha256": source_hashes(), "dataset_revision": REVISION, "dataset_sha256": DATA_SHA,
        "dataset_rows": len(data), "sample_rows": len(selected), "sample_indices": selected,
        "sample_sha256": digest([data[i] for i in selected]), "sampling_seed": 17,
        "gold_mapping": GOLD_MAP, "prediction_mapping": PRED_MAP,
        "spacy_version": "3.8.7", "model": "en_core_web_sm", "model_version": "3.8.0",
        "maximum_runtime_seconds": 600, "long_unicode_repetitions": [1, 100, 1000, 4000],
        "scoring": "Exact Unicode-codepoint start/end and mapped label; no trimming, overlap credit, threshold tuning or sample exclusions",
        "training": "No training/tuning; fixed external fixture sample; unknown pretrained-model contamination",
        "licenses": {"repository": "MIT", "fake_name_generator_identities": "CC-BY-SA-3.0-US"}}
    document["sha256"] = digest(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(document, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return document


def prf(tp, fp, fn):
    return {"tp": tp, "fp": fp, "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None}


def score(gold, predictions):
    matched = gold & predictions
    labels = {s[2] for s in gold | predictions}
    return {label: prf(sum(s[2] == label for s in matched), sum(s[2] == label for s in predictions - matched), sum(s[2] == label for s in gold - matched)) for label in sorted(labels)}


def percentile(values, quantile):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(quantile * len(ordered)) - 1)] if ordered else None


def run(data, frozen_path, output):
    frozen = json.loads(frozen_path.read_text())
    unsigned = {k: v for k, v in frozen.items() if k != "sha256"}
    if digest(unsigned) != frozen["sha256"] or source_hashes() != frozen["source_sha256"]:
        raise ValueError("Frozen protocol/source hash changed")
    indices = frozen["sample_indices"]
    if indices != selection(len(data)) or digest([data[i] for i in indices]) != frozen["sample_sha256"]:
        raise ValueError("Frozen sample changed")
    for package, version in (("spacy", "3.8.7"), ("en-core-web-sm", "3.8.0")):
        if importlib.metadata.version(package) != version:
            raise ValueError("Runtime model/package version differs from freeze")
    output.mkdir(parents=True, exist_ok=False)
    started_at = datetime.now(timezone.utc)
    if started_at <= datetime.fromisoformat(frozen["frozen_at_utc"]):
        raise ValueError("Execution must start after the protocol freeze")
    start = time.perf_counter()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("600-second bounded CPU evaluation exceeded")))
    signal.alarm(600)
    # Model loading and all text inference are local. No model/API clients exist here.
    from app.deid.engine import DeidEngine, POLICY_MAP
    from app.deid import recognizers
    from app.core.config import get_settings
    settings = get_settings()
    settings.max_text_size = 500000
    load_start = time.perf_counter()
    nlp = recognizers._get_nlp("en")
    if nlp is None:
        raise RuntimeError("The full NER pipeline must load; regex-only fallback is forbidden for this study")
    model_load_ms = (time.perf_counter() - load_start) * 1000
    model_root = Path(importlib.util.find_spec("en_core_web_sm").origin).parent
    model_hashes = {str(p.relative_to(model_root)): file_sha(p) for p in sorted(model_root.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}
    engine = DeidEngine(POLICY_MAP, salt="synthetic-evaluation-only", default_policy="mask")
    engine.deidentify("A fictional demonstration sentence.")
    totals = defaultdict(Counter)
    unsupported_gold, unscored_predictions = Counter(), Counter()
    timings, doc_rows = [], []
    gold_count = supported_count = 0
    with (output / "documents.jsonl").open("w") as stream:
        for index in indices:
            record = data[index]
            text = record["full_text"]
            gold = {(s["start_position"], s["end_position"], GOLD_MAP[s["entity_type"]]) for s in record["spans"] if s["entity_type"] in GOLD_MAP}
            gold_count += len(record["spans"])
            supported_count += len(gold)
            unsupported_gold.update(s["entity_type"] for s in record["spans"] if s["entity_type"] not in GOLD_MAP)
            started = time.perf_counter_ns()
            result = engine.deidentify(text, lang_hint="en")
            elapsed = (time.perf_counter_ns() - started) / 1e6
            timings.append(elapsed)
            predictions = {(e["span"][0], e["span"][1], PRED_MAP[e["label"]]) for e in result["entities"] if e["label"] in PRED_MAP}
            unscored_predictions.update(e["label"] for e in result["entities"] if e["label"] not in PRED_MAP)
            if any(not 0 <= e["span"][0] < e["span"][1] <= len(text) for e in result["entities"]):
                raise ValueError("Engine emitted an invalid Unicode span")
            per = score(gold, predictions)
            for label, counts in per.items():
                totals[label].update({k: counts[k] for k in ("tp", "fp", "fn")})
            row = {"dataset_index": index, "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "characters": len(text), "template_id": record["template_id"], "latency_ms": elapsed,
                "supported_gold_spans": len(gold), "all_gold_spans": len(record["spans"]),
                "scored_predictions": len(predictions), "unscored_predictions": len(result["entities"]) - len(predictions),
                "tp": sum(c["tp"] for c in per.values()), "fp": sum(c["fp"] for c in per.values()), "fn": sum(c["fn"] for c in per.values())}
            doc_rows.append(row)
            stream.write(json.dumps(row, sort_keys=True) + "\n")
            stream.flush()
    stress = []
    block = "🙂 Καλημέρα — café e\u0301 東京. Contact demo@example.org.\n"
    for repetitions in frozen["long_unicode_repetitions"]:
        text = block * repetitions
        started = time.perf_counter_ns()
        result = engine.deidentify(text, lang_hint="en")
        elapsed = (time.perf_counter_ns() - started) / 1e6
        expected = {(i * len(block) + block.index("demo@example.org"), i * len(block) + block.index("demo@example.org") + len("demo@example.org")) for i in range(repetitions)}
        actual = {tuple(e["span"]) for e in result["entities"] if e["label"] == "EMAIL"}
        valid = all(0 <= e["span"][0] < e["span"][1] <= len(text) for e in result["entities"])
        stress.append({"repetitions": repetitions, "unicode_codepoints": len(text), "utf8_bytes": len(text.encode()),
            "latency_ms": elapsed, "expected_emails": len(expected), "exact_email_matches": len(expected & actual),
            "extra_email_spans": len(actual - expected), "all_output_spans_in_bounds": valid,
            "source_email_removed": "demo@example.org" not in result["result_text"]})
    limit_rejected = False
    try:
        engine.deidentify("x" * 500001)
    except ValueError:
        limit_rejected = True
    per_label = {label: prf(totals[label]["tp"], totals[label]["fp"], totals[label]["fn"]) for label in sorted(set(GOLD_MAP.values()))}
    micro = prf(sum(c["tp"] for c in totals.values()), sum(c["fp"] for c in totals.values()), sum(c["fn"] for c in totals.values()))
    supported = [r for r in per_label.values() if r["tp"] + r["fn"]]
    report = {"protocol": frozen["protocol"], "freeze_sha256": frozen["sha256"], "status": "complete",
        "started_at_utc": started_at.isoformat(), "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine_commit": frozen["engine_commit"], "sample_rows": len(doc_rows), "templates": len({r["template_id"] for r in doc_rows}),
        "gold_spans_all_labels": gold_count, "gold_spans_supported_mapping": supported_count,
        "supported_gold_coverage": supported_count / gold_count, "unsupported_gold_counts": dict(unsupported_gold),
        "unscored_prediction_counts": dict(unscored_predictions), "per_label": per_label, "micro": micro,
        "macro_f1_gold_supported_labels": sum(r["f1"] or 0 for r in supported) / len(supported),
        "latency_ms": {"model_load": model_load_ms, "p50_nearest_rank": percentile(timings, 0.5), "p95_nearest_rank": percentile(timings, 0.95), "max": max(timings)},
        "long_unicode_stress": stress, "rejects_500001_characters": limit_rejected,
        "total_elapsed_seconds": time.perf_counter() - start,
        "runtime": {"python": platform.python_version(), "os": platform.system(), "architecture": platform.machine(), "machine": platform.processor(),
            "spacy": importlib.metadata.version("spacy"), "model": importlib.metadata.version("en-core-web-sm"), "model_files_sha256": model_hashes,
            "dependencies": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}},
        "limitations": ["External synthetic template fixture; not clinical, representative production or compliance evidence.",
            "Exact label/boundary convention penalizes partial addresses and names; no overlap credit.",
            "Unsupported gold labels and engine-only labels are separately counted, not silently scored as supported.",
            "No tuning, training, bootstrap CI or new model contribution; pretrained-model contamination unknown.",
            "Measurements cover the library engine, not the separately deployed HTTP adapter or browser workflow.",
            "Single local CPU process; inference latency includes transformations and excludes model load/warm-up."]}
    (output / "results.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    (output / "protocol.json").write_bytes(frozen_path.read_bytes())
    signal.alarm(0)
    print(json.dumps({"docs": len(doc_rows), "micro": micro, "elapsed_seconds": report["total_elapsed_seconds"]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--freeze", type=Path)
    operation.add_argument("--run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = load_dataset(args.dataset)
    if args.freeze:
        frozen = freeze(args.freeze, data)
        print(json.dumps({"frozen": True, "sha256": frozen["sha256"], "rows": frozen["sample_rows"]}))
    else:
        if args.output is None:
            parser.error("--output is required for --run")
        run(data, args.run, args.output)


if __name__ == "__main__":
    main()
