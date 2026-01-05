import json
from pathlib import Path

from app.deid.recognizers import detect_entities


def test_golden_small_dataset_counts():
    data_path = Path(__file__).resolve().parents[1] / "data" / "dataset_small.jsonl"
    texts = []
    with data_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                texts.append(json.loads(line))

    assert len(texts) >= 2

    # Each record must surface at minimum these labels
    expected_min = [
        {"EMAIL": 1, "URL": 1, "IP": 1, "MRN": 1, "SSN": 1, "PHONE_US": 1},
        {"EMAIL": 1, "SIN_CA": 1, "HEALTH_CARD_CA": 1, "POSTAL_CA": 1},
    ]

    for rec, exp in zip(texts, expected_min):
        ents = detect_entities(rec["text"], lang_hint=rec.get("lang"))
        counts = {}
        for e in ents:
            counts[e.label] = counts.get(e.label, 0) + 1
        for label, c in exp.items():
            assert counts.get(label, 0) >= c, f"missing {label}: got {counts}"
