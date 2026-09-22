import pytest
from app.deid.engine import DeidEngine
from app.deid.policies import apply_policy_span


def test_unknown_entity_policy_is_rejected_before_processing():
    with pytest.raises(ValueError, match="policy"):
        DeidEngine({"EMAIL": "hasH-typo"}, "synthetic-salt", "redact")


def test_unknown_default_policy_is_rejected():
    with pytest.raises(ValueError, match="policy"):
        DeidEngine({}, "synthetic-salt", "keep")


def test_unknown_span_policy_never_returns_original_identifier():
    with pytest.raises(ValueError, match="policy"):
        apply_policy_span("a@example.invalid", 0, 17, "EMAIL", "hasH-typo")


def test_policy_update_schema_rejects_unknown_action():
    from app.api.v1 import PolicyUpdate

    with pytest.raises(ValueError):
        PolicyUpdate(policy_map={"EMAIL": "hasH-typo"})
