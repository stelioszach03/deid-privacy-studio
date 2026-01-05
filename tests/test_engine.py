"""End-to-end coverage for the DeidEngine + policy wiring (US/CA)."""
from hashlib import sha256

from app.deid.policies import mask_value, redact_value, hash_value
from app.deid.regex_rules import SSN_US, PHONE_US
from app.deid.recognizers import detect_entities
from app.core.config import get_settings


# ─── Policy helpers ──────────────────────────────────────────────

def test_policy_mask_preserves_length():
    original = "Sensitive123"
    masked = mask_value(original)
    assert masked == "*" * len(original)


def test_policy_redact_uses_label():
    assert redact_value("EMAIL") == "[REDACTED:EMAIL]"


def test_policy_hash_uses_salt_and_value():
    salt = "salt-xyz"
    value = "john@example.com"
    expected = sha256((salt + value).encode("utf-8")).hexdigest()
    hashed = hash_value(value, salt, "EMAIL")
    assert hashed.endswith(expected)
    assert hashed.startswith("EMAIL_HASH:")


# ─── Regex sanity ────────────────────────────────────────────────

def test_regex_ssn_matches_valid_format():
    assert SSN_US.search("412-55-7891")


def test_regex_phone_us_matches_multiple_formats():
    cases = [
        "(617) 555-0134",
        "617-555-0134",
        "617.555.0134",
        "6175550134",
    ]
    for c in cases:
        assert PHONE_US.search(c) is not None, c


# ─── Recognizer / dedupe integration ─────────────────────────────

def test_dedup_overlapping_phone_picks_one_span():
    text = "Call me at (617) 555-0134 today"
    ents = detect_entities(text, lang_hint="en")
    phones = [e for e in ents if e.label.startswith("PHONE")]
    assert len(phones) == 1


def test_mrn_no_overdetects_simple_english():
    txt = (
        "Patient Eleanor Whitfield was seen on 03/14/2026 in Boston.\n"
        "Contact: (617) 555-0134, e.whitfield@example.org\n"
        "Record: MRN: BWH-47882910\n"
        "Refer: https://hospital.example.org/cases/7788\n"
        "Client IP: 192.168.10.25\n"
    )
    ents = detect_entities(txt, lang_hint="en")
    labels = {e.label for e in ents}
    assert "EMAIL" in labels
    assert "URL" in labels
    assert "IP" in labels
    assert "PHONE_US" in labels
    mrns = [e for e in ents if e.label == "MRN"]
    assert len(mrns) == 1
    assert "47882910" in mrns[0].text


# ─── API integration ─────────────────────────────────────────────

def test_engine_changes_text_and_actions(api_client):
    txt = "Email me at alice@example.com and call (617) 555-0134"
    r = api_client.post("/api/v1/deid", json={"text": txt, "lang_hint": "en"})
    assert r.status_code == 200
    body = r.json()
    assert body["result_text"] != txt
    actions = {e["label"]: e["action"] for e in body["entities"]}
    assert actions.get("EMAIL") == "hash"
    assert actions.get("PHONE_US") == "mask"


def test_max_text_size_guard(api_client):
    settings = get_settings()
    too_long = "A" * (settings.max_text_size + 1)
    r = api_client.post("/api/v1/deid", json={"text": too_long, "lang_hint": "en"})
    assert r.status_code == 413


def test_hash_deterministic(api_client):
    settings = get_settings()
    email = "bob@example.com"
    r = api_client.post("/api/v1/deid", json={"text": email, "lang_hint": "en"})
    assert r.status_code == 200
    body = r.json()
    exp = sha256((settings.deid_salt + email).encode("utf-8")).hexdigest()
    assert f"EMAIL_HASH:{exp}" in body["result_text"]
