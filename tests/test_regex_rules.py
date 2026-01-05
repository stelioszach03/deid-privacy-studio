"""Unit coverage for the US/CA pattern ladder."""
from app.deid.regex_rules import (
    EMAIL, PHONE_US, SSN_US, SIN_CA, NPI, DEA, PASSPORT_US,
    MRN, HICN, HEALTH_CARD_CA, CREDIT_CARD, ROUTING, IBAN,
    US_STREET, ZIP_US, POSTAL_CA, DATE, URL, IP,
)


def test_email_varieties():
    cases = [
        "john@example.com",
        "jane.doe@example.com",
        "user_name+tag@example.co.uk",
        "x@y.z",
    ]
    for c in cases:
        assert EMAIL.search(c), c
    assert EMAIL.search("not-an-email") is None


def test_phone_us_variants_and_rejects():
    positives = [
        "(617) 555-0134",
        "617-555-0134",
        "617.555.0134",
        "6175550134",
        "+1 617 555 0134",
    ]
    for p in positives:
        assert PHONE_US.search(p), p
    # 8 digits is not a valid NANP phone
    assert PHONE_US.search("12345678") is None


def test_ssn_valid_and_invalid_prefixes():
    assert SSN_US.search("412-55-7891")
    assert SSN_US.search("412 55 7891")
    assert SSN_US.search("412557891")
    # 000 / 666 / 9xx prefixes are invalid
    assert SSN_US.search("000-12-3456") is None
    assert SSN_US.search("666-12-3456") is None
    assert SSN_US.search("923-12-3456") is None


def test_sin_ca_matches_grouped_format():
    assert SIN_CA.search("046 454 286")
    assert SIN_CA.search("046-454-286")
    # unbroken 9 digits shouldn't trigger the grouped SIN rule
    assert SIN_CA.search("046454286") is None


def test_npi_labeled_and_contextual():
    assert NPI.search("NPI# 1538296472")
    assert NPI.search("NPI: 1538296472")
    assert NPI.search("1538296472 provider")


def test_dea_two_letters_seven_digits():
    assert DEA.search("AC9137284")
    assert DEA.search("BO4872913")
    assert DEA.search("A1234567") is None


def test_passport_us_context_anchor():
    assert PASSPORT_US.search("518294776 passport")
    assert PASSPORT_US.search("N12345678 passport")


def test_mrn_strict_accept_reject():
    accepts = ["BWH-47882910", "MRN: ABCD778899", "NYU_1245678"]
    for a in accepts:
        assert MRN.search(a), a
    rejects = ["Boston", "Patient", "ABC"]
    for r in rejects:
        assert MRN.search(r) is None, r


def test_hicn_medicare_format():
    assert HICN.search("1EG4-TE5-MK73")


def test_health_card_ca_format():
    assert HEALTH_CARD_CA.search("4532-281-947-AB")
    assert HEALTH_CARD_CA.search("4532 281 947 AB")


def test_credit_card_groupings():
    assert CREDIT_CARD.search("4532 8827 1104 9951")
    assert CREDIT_CARD.search("4532-8827-1104-9951")
    assert CREDIT_CARD.search("4532882711049951")


def test_routing_iban():
    assert ROUTING.search("ABA: 026009593")
    assert ROUTING.search("routing 072000096")
    assert IBAN.search("GB29 NWBK 60161331926819".replace(" ", ""))
    assert IBAN.search("DE89370400440532013000")


def test_us_street_and_postal():
    assert US_STREET.search("482 Commonwealth Avenue")
    assert US_STREET.search("1420 West Lafayette Blvd")
    assert ZIP_US.search("02215")
    assert ZIP_US.search("94111-1234")
    assert POSTAL_CA.search("M5S 2V6")
    assert POSTAL_CA.search("M5S2V6")


def test_date_mdy_and_iso():
    assert DATE.search("03/14/1968")
    assert DATE.search("2026-04-02")


def test_url_and_ip():
    assert URL.search("https://example.org/path?q=1")
    assert IP.search("Client 192.168.1.10 end")
    assert URL.search("no url here") is None
