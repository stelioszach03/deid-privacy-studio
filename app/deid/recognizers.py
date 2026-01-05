"""
Entity recognition pipeline for US/CA healthcare and financial PHI/PII.

Layers:
  1. spaCy en_core_web_sm for PERSON / ORG / GPE / LOC / DATE.
  2. Regex rules from `regex_rules.py` for structured identifiers
     (SSN, NPI, MRN, credit card, IBAN, US street, ZIP, dates, etc.).
  3. Dedupe by (priority, length, position) so structured rules win
     over noisy NER spans on overlap.

Greek-language support has been removed — this recognizer is optimized
for HIPAA Safe Harbor and PIPEDA workloads.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

try:
    import spacy  # type: ignore
except Exception:  # pragma: no cover - spaCy optional at runtime
    spacy = None  # type: ignore

try:
    from .regex_rules import PATTERNS  # preferred: prioritized patterns
except Exception:  # fallback
    from .regex_rules import RULES as _RULES
    PATTERNS = [(k, v, 0) for k, v in _RULES.items()]


@dataclass
class Entity:
    start: int
    end: int
    text: str
    label: str
    detector: str  # "spacy" | "regex"


_NLP_EN = None


def _get_nlp(lang: str):
    """Load English spaCy pipeline lazily. Returns None if unavailable."""
    global _NLP_EN
    if spacy is None or lang != "en":
        return None
    if _NLP_EN is None:
        try:
            _NLP_EN = spacy.load(
                "en_core_web_sm",
                disable=["tagger", "lemmatizer", "textcat", "parser"],
            )
        except Exception:
            _NLP_EN = None
    return _NLP_EN


def _spacy_entities(text: str, lang_hint: Optional[str]) -> List[Entity]:
    ents: List[Entity] = []
    labels = {"PERSON", "ORG", "GPE", "LOC", "DATE"}
    nlp = _get_nlp("en")  # single-language pipeline
    if nlp is None:
        return ents
    doc = nlp(text)
    for e in doc.ents:
        if e.label_ in labels:
            ents.append(
                Entity(
                    start=e.start_char,
                    end=e.end_char,
                    text=e.text,
                    label=e.label_,
                    detector="spacy",
                )
            )
    return ents


def _regex_entities(text: str) -> List[Entity]:
    ents: List[Entity] = []
    for name, pattern, _prio in sorted(PATTERNS, key=lambda t: t[2], reverse=True):
        for m in pattern.finditer(text):
            ents.append(
                Entity(
                    start=m.start(),
                    end=m.end(),
                    text=m.group(0),
                    label=name,
                    detector="regex",
                )
            )
    return ents


# Higher numbers win on span overlap
PRIORITY: Dict[str, int] = {
    # Direct contact
    "EMAIL": 110,
    # Government IDs — always beat generic NER
    "SSN": 108,
    "SIN_CA": 107,
    "NPI": 106,
    "DEA": 105,
    "PASSPORT_US": 104,
    # Healthcare
    "HICN": 103,
    "HEALTH_CARD_CA": 102,
    "MRN": 100,
    # NER person name (before generic structured)
    "PERSON": 99,
    # Financial
    "CREDIT_CARD": 95,
    "ROUTING": 94,
    "IBAN": 93,
    # Phone
    "PHONE_US": 90,
    "PHONE_INTL": 88,
    # Technical
    "URL": 85,
    "IP": 85,
    # Temporal
    "DATE": 80,
    # Location
    "GPE": 78,
    "LOC": 77,
    "ADDRESS": 76,
    "US_STREET": 75,
    "POSTAL_CA": 70,
    "ZIP_US": 65,
    # Misc
    "ORG": 60,
}


def _priority(label: str) -> int:
    return PRIORITY.get(label, 10)


def _filter_mrn_overdetections(text: str, entities: List[Entity]) -> List[Entity]:
    """
    Drop MRN candidates that look like noise:
      * purely alphabetic (no digits),
      * shorter than 6 chars with no contextual hint,
      * OR lacking 'MRN'/'Record'/'Patient ID' context and no delimiter.
    """
    out: List[Entity] = []
    lowered = text.lower()
    CTX_KEYS = ("mrn", "record", "patient id", "medical record", "chart")
    for e in entities:
        if e.label != "MRN":
            out.append(e)
            continue
        span_txt = e.text
        has_digit = any(ch.isdigit() for ch in span_txt)
        if not has_digit or span_txt.isalpha():
            continue
        long_enough = len(span_txt) >= 6
        line_start = lowered.rfind("\n", 0, e.start) + 1
        left_ctx = lowered[max(line_start, e.start - 16):e.start]
        ctx_ok = any(k in left_ctx for k in CTX_KEYS)
        if not long_enough and not ctx_ok:
            continue
        alnum_mix = any(c.isalpha() for c in span_txt) and has_digit
        has_delim = ("-" in span_txt) or ("_" in span_txt)
        if not ctx_ok and not (alnum_mix and has_delim):
            continue
        out.append(e)
    return out


def _dedupe(entities: List[Entity]) -> List[Entity]:
    entities_sorted = sorted(
        entities,
        key=lambda e: (-_priority(e.label), -(e.end - e.start), e.start),
    )
    kept: List[Entity] = []
    for e in entities_sorted:
        if any(not (e.end <= k.start or e.start >= k.end) for k in kept):
            continue
        kept.append(e)
    return sorted(kept, key=lambda e: e.start)


def detect_entities(text: str, lang_hint: Optional[str] = None) -> List[Entity]:
    sp = _spacy_entities(text, lang_hint)
    rx = _regex_entities(text)
    combined = _filter_mrn_overdetections(text, sp + rx)
    return _dedupe(combined)


def recognize(text: str, lang: str = "en") -> List[Dict]:
    """Compatibility layer — returns dicts consumed by `apply_policies`."""
    ents = detect_entities(text, lang_hint=lang)
    return [
        {"type": e.label, "start": e.start, "end": e.end, "value": e.text}
        for e in ents
    ]
