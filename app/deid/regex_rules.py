"""
US / CA-focused PHI/PII pattern library for DeID Privacy Studio.

Patterns are prioritized (higher wins on overlap). Each rule returns a label
that maps to a policy (hash / mask / redact) in the engine. All patterns
target North American healthcare and financial record formats — HIPAA Safe
Harbor categories, Canadian equivalents, and common identifiers.
"""
from __future__ import annotations

import re
from typing import List, Tuple


# ─────────────────────────────────────────────────────────────
# Contact information
# ─────────────────────────────────────────────────────────────

# RFC-lite email
EMAIL = re.compile(
    r"\b[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b"
)

# US / Canadian phone numbers: 10-digit NANP
# Accepts: (555) 123-4567, 555-123-4567, 555.123.4567, 5551234567, +1 555 123 4567
PHONE_US = re.compile(
    r"(?:\+?1[\s.\-]?)?(?:\(\d{3}\)|\d{3})[\s.\-]?\d{3}[\s.\-]?\d{4}\b"
)

# International phones starting with + (excluding US/CA, for completeness)
PHONE_INTL = re.compile(r"\+(?:[2-9]\d{1,3})[\s.\-]?\d{4,14}\b")


# ─────────────────────────────────────────────────────────────
# Government identifiers
# ─────────────────────────────────────────────────────────────

# US Social Security Number: AAA-GG-SSSS (prevents obvious-invalid 000, 666, 9xx prefixes)
SSN_US = re.compile(
    r"\b(?!000|666|9\d{2})\d{3}[\s\-]?(?!00)\d{2}[\s\-]?(?!0000)\d{4}\b"
)

# Canadian SIN (9 digits, typically grouped as 3-3-3)
SIN_CA = re.compile(r"\b\d{3}[\s\-]\d{3}[\s\-]\d{3}\b")

# US National Provider Identifier (NPI): 10 digits
NPI = re.compile(r"\bNPI[:\s#]*\d{10}\b|\b\d{10}\b(?=\s*(?:NPI|provider))")

# US DEA number (for controlled substance prescribers): 2 letters + 7 digits
DEA = re.compile(r"\b[A-Z]{2}\d{7}\b")

# US passport: 1 letter + 8 digits, or 9 digits
PASSPORT_US = re.compile(r"\b(?:[A-Z]\d{8}|\d{9})\b(?=\s*(?:passport))", re.IGNORECASE)


# ─────────────────────────────────────────────────────────────
# Healthcare identifiers
# ─────────────────────────────────────────────────────────────

# Medical Record Number — labeled or structured
# Matches: MRN: 1234567, MRN#ABC-12345, BWH-12345678
MRN = re.compile(
    r"\b(?:MRN[:\s#]*[A-Z0-9\-]{5,12}|[A-Z]{2,6}[-_][0-9]{4,10}|[A-Z]{2,6}[0-9]{5,10})\b"
)

# Medicare Beneficiary Identifier (MBI / HICN successor).
# 11 chars: digit + alpha + alnum + digit + alpha + alnum + digit + alpha + alpha + 2 digits.
# Tolerates "-" or " " separators after positions 4 and 7.
HICN = re.compile(
    r"\b[1-9][A-Z][A-Z0-9][0-9][\s\-]?[A-Z][A-Z0-9][0-9][\s\-]?[A-Z][A-Z][0-9]{2}\b"
)

# Canadian provincial health card (Ontario format: 1234-567-890-XX)
HEALTH_CARD_CA = re.compile(r"\b\d{4}[\s\-]\d{3}[\s\-]\d{3}[\s\-]?[A-Z]{0,2}\b")


# ─────────────────────────────────────────────────────────────
# Financial
# ─────────────────────────────────────────────────────────────

# Credit card: 13-19 digits, with common grouping (Luhn not enforced)
CREDIT_CARD = re.compile(
    r"\b(?:\d{4}[\s\-]?){3}\d{1,4}\b"
)

# US bank routing number (ABA): 9 digits, labeled
ROUTING = re.compile(r"\b(?:ABA|routing)[:\s#]*\d{9}\b", re.IGNORECASE)

# IBAN (international bank account)
IBAN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")


# ─────────────────────────────────────────────────────────────
# Addresses
# ─────────────────────────────────────────────────────────────

# US street address: number + street name + suffix
US_STREET = re.compile(
    r"\b\d{1,6}\s+(?:[NSEW]\.?\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}"
    r"\s+(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|Drive|Dr\.?|"
    r"Lane|Ln\.?|Way|Court|Ct\.?|Place|Pl\.?|Parkway|Pkwy\.?|Square|Sq\.?|Highway|Hwy\.?)\b"
)

# US ZIP: 5 digits or ZIP+4
ZIP_US = re.compile(r"\b\d{5}(?:-\d{4})?\b")

# Canadian postal code: A1A 1A1
POSTAL_CA = re.compile(r"\b[A-Z]\d[A-Z][\s]?\d[A-Z]\d\b")


# ─────────────────────────────────────────────────────────────
# Dates
# ─────────────────────────────────────────────────────────────

# Dates of birth / admission: MM/DD/YYYY, MM-DD-YYYY, YYYY-MM-DD
DATE = re.compile(
    r"\b(?:(?:0?[1-9]|1[0-2])[/\-](?:0?[1-9]|[12]\d|3[01])[/\-](?:19|20)\d{2}"
    r"|(?:19|20)\d{2}[/\-](?:0?[1-9]|1[0-2])[/\-](?:0?[1-9]|[12]\d|3[01]))\b"
)


# ─────────────────────────────────────────────────────────────
# Technical identifiers
# ─────────────────────────────────────────────────────────────

URL = re.compile(r"\bhttps?://[^\s<>\"]+\b")
IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


# ─────────────────────────────────────────────────────────────
# Priority list — higher wins on overlap
# ─────────────────────────────────────────────────────────────

PATTERNS: List[Tuple[str, re.Pattern, int]] = [
    ("EMAIL", EMAIL, 100),
    ("SSN", SSN_US, 98),
    ("SIN_CA", SIN_CA, 97),
    ("NPI", NPI, 96),
    ("DEA", DEA, 95),
    ("PASSPORT_US", PASSPORT_US, 94),
    ("HICN", HICN, 93),
    ("HEALTH_CARD_CA", HEALTH_CARD_CA, 92),
    ("MRN", MRN, 91),
    ("CREDIT_CARD", CREDIT_CARD, 88),
    ("ROUTING", ROUTING, 87),
    ("IBAN", IBAN, 86),
    ("PHONE_US", PHONE_US, 80),
    ("PHONE_INTL", PHONE_INTL, 75),
    ("DATE", DATE, 70),
    ("US_STREET", US_STREET, 65),
    ("POSTAL_CA", POSTAL_CA, 60),
    ("ZIP_US", ZIP_US, 55),
    ("URL", URL, 40),
    ("IP", IP, 35),
]

# Backwards-compatible dict form
RULES = {label: pattern for label, pattern, _ in PATTERNS}
