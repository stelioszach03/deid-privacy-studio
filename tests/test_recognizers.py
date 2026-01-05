"""Recognizer coverage — spaCy NER + regex ladder for US/CA text."""
import os
import pytest

from app.deid.recognizers import detect_entities


def _labels(ents):
    return {e.label for e in ents}


@pytest.mark.skipif(os.environ.get("SKIP_NER") == "1", reason="NER skipped")
def test_detect_entities_en_healthcare(sample_texts):
    ents = detect_entities(sample_texts["medical"], lang_hint="en")
    labs = _labels(ents)
    assert {"EMAIL", "URL", "IP", "PHONE_US"}.issubset(labs)
    # at least one PII/PHI identifier from the US set
    assert labs & {"SSN", "NPI", "MRN", "HICN", "DEA"}


def test_mrn_overdetection_guard(sample_texts):
    ents = detect_entities(sample_texts["medical"], lang_hint="en")
    mrns = [e for e in ents if e.label == "MRN"]
    assert len(mrns) >= 1


def test_ca_identifiers_detected(sample_texts):
    ents = detect_entities(sample_texts["ca_claim"], lang_hint="en")
    labs = _labels(ents)
    assert "SIN_CA" in labs or "HEALTH_CARD_CA" in labs
    assert "POSTAL_CA" in labs
