"""API-level smoke tests against the FastAPI app."""
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_settings


client = TestClient(app)


def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    assert "version" in body


def test_deid_endpoint_text_and_config_roundtrip(tmp_path):
    text = (
        "Patient Eleanor Whitfield, DOB 03/14/1968, contacted on (617) 555-0134. "
        "Email: e.whitfield@example.org, MRN BWH-47882910"
    )
    # Check current config
    cfg = client.get("/api/v1/config").json()
    assert "policy_map" in cfg and "default_policy" in cfg

    # Update default policy to mask (in-memory)
    r = client.put("/api/v1/config", json={"default_policy": "mask"})
    assert r.status_code == 200
    assert r.json()["default_policy"] == "mask"

    # De-identify
    payload = {"text": text, "lang_hint": "en"}
    r = client.post("/api/v1/deid", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "result_text" in data
    assert "e.whitfield@example.org" not in data["result_text"]
    labels = {ent.get("label") for ent in data.get("entities", [])}
    assert "EMAIL" in labels


def test_deid_file_upload(tmp_path):
    content = b"Patient John, SSN 412-55-7891, phone (617) 555-0134"
    files = [
        ("files", ("doc1.txt", content, "text/plain")),
        ("files", ("doc2.txt", content, "text/plain")),
    ]
    r = client.post("/api/v1/deid/file", files=files)
    assert r.status_code == 200
    arr = r.json()
    assert isinstance(arr, list) and len(arr) == 2
    for item in arr:
        assert "result_text" in item
        assert "entities" in item


def test_oversized_input_returns_413():
    settings = get_settings()
    too_long = "A" * (settings.max_text_size + 1)
    r = client.post("/api/v1/deid", json={"text": too_long})
    assert r.status_code == 413
