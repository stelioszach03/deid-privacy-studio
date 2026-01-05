from time import perf_counter
from typing import Dict, List, Optional, Tuple

from app.core.config import get_settings
from .recognizers import detect_entities, recognize
from .policies import apply_policies, hash_value, mask_value, redact_value


# Default US / CA-focused policy mapping — HIPAA Safe Harbor + PIPEDA aligned
POLICY_MAP: Dict[str, str] = {
    # Named entities (spaCy NER)
    "PERSON": "redact",
    "GPE": "redact",
    "ORG": "redact",
    "LOC": "redact",
    "ADDRESS": "redact",

    # Contact
    "EMAIL": "hash",
    "PHONE_US": "mask",
    "PHONE_INTL": "mask",

    # US / CA government identifiers
    "SSN": "hash",
    "SIN_CA": "hash",
    "PASSPORT_US": "hash",
    "DEA": "hash",
    "NPI": "hash",

    # Healthcare
    "MRN": "hash",
    "HICN": "hash",
    "HEALTH_CARD_CA": "hash",

    # Financial
    "CREDIT_CARD": "mask",
    "ROUTING": "mask",
    "IBAN": "mask",

    # Location / postal
    "US_STREET": "redact",
    "ZIP_US": "redact",
    "POSTAL_CA": "redact",

    # Temporal
    "DATE": "mask",

    # Technical
    "URL": "redact",
    "IP": "redact",
}


# Human-readable display names for compound labels. Used for the
# `redact` action output (so `US_STREET` renders as `[REDACTED:ADDRESS]`)
# and for `PHONE` fallback inside `_resolve_policy`.
_DISPLAY: Dict[str, str] = {
    "US_STREET":      "ADDRESS",
    "ZIP_US":         "ZIP",
    "POSTAL_CA":      "POSTAL_CODE",
    "SIN_CA":         "SIN",
    "HEALTH_CARD_CA": "HEALTH_CARD",
    "PASSPORT_US":    "PASSPORT",
    "PHONE_US":       "PHONE",
    "PHONE_INTL":     "PHONE",
}


def _canonical_label(label: str) -> str:
    """Normalize a detector label into a stable display name."""
    if label in _DISPLAY:
        return _DISPLAY[label]
    if label.startswith("ADDRESS"):
        return "ADDRESS"
    if label.startswith("PHONE"):
        return "PHONE"
    return label


class DeidEngine:
    def __init__(self, policy_map: Dict[str, str], salt: str, default_policy: str) -> None:
        self.policy_map = dict(policy_map or {})
        self.salt = salt or ""
        self.default_policy = default_policy

    def _resolve_policy(self, label: str) -> str:
        # Exact match
        if label in self.policy_map:
            return self.policy_map[label]
        # Variant normalization
        base = _canonical_label(label)
        if base in self.policy_map:
            return self.policy_map[base]
        # Phone fallback: any PHONE_* -> first PHONE_* policy defined
        if base == "PHONE":
            for k in ("PHONE_US", "PHONE_INTL"):
                if k in self.policy_map:
                    return self.policy_map[k]
        return self.default_policy

    def deidentify(self, text: str, lang_hint: Optional[str] = None) -> Dict:
        settings = get_settings()
        if text is None:
            text = ""
        if len(text) > settings.max_text_size:
            raise ValueError(
                f"Text too long: {len(text)} chars (max {settings.max_text_size})"
            )

        t0 = perf_counter()
        entities = detect_entities(text, lang_hint=lang_hint)

        # Ensure non-overlapping spans, sorted by start
        spans = sorted(((e.start, e.end, e.label, e.text) for e in entities), key=lambda x: x[0])
        merged: List[Tuple[int, int, str, str]] = []
        last_end = -1
        for s, e, label, txt in spans:
            if s >= last_end:
                merged.append((s, e, label, txt))
                last_end = e
            else:
                # Overlap: skip lower-priority span (detect_entities already resolves priority)
                continue

        # Build result text while applying per-entity policy
        result_parts: List[str] = []
        last = 0
        results_meta: List[Dict] = []
        for start, end, label, value in merged:
            result_parts.append(text[last:start])
            action = self._resolve_policy(label)
            canon = _canonical_label(label)
            if action == "mask":
                replacement = mask_value(value)
            elif action == "redact":
                replacement = redact_value(canon)
            elif action == "hash":
                replacement = hash_value(value, self.salt, canon)
            else:
                replacement = value  # unknown action -> passthrough

            result_parts.append(replacement)
            results_meta.append({
                "label": label,
                "span": [start, end],
                "action": action,
            })
            last = end

        result_parts.append(text[last:])
        result_text = "".join(result_parts)
        elapsed_ms = int((perf_counter() - t0) * 1000)

        return {
            "original_len": len(text),
            "result_text": result_text,
            "entities": results_meta,
            "time_ms": elapsed_ms,
        }


# Backward-compatible function kept for current API/tests
def deidentify(text: str, lang: str = "en") -> Tuple[str, List[Dict]]:
    matches = recognize(text, lang)
    sanitized, entities = apply_policies(text, matches)
    return sanitized, entities
