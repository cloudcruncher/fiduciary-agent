from fiduciary.agent.pii_anonymizer import PIIAnonymizer


def test_pii_anonymizer_sort_code_and_account():
    raw = "My sort code is 20-45-78 and account number is 87654321 at Barclays."
    anonymized, mapping = PIIAnonymizer.anonymize(raw)

    assert "20-45-78" not in anonymized
    assert "87654321" not in anonymized
    assert "[SORT_CODE_1]" in anonymized
    assert "[ACCOUNT_NUM_1]" in anonymized

    # Roundtrip deanonymization
    restored = PIIAnonymizer.deanonymize(anonymized, mapping)
    assert restored == raw


def test_pii_anonymizer_email_and_phone():
    raw = "Contact alex.smith@example.co.uk or call +44 7123 456789 for queries."
    anonymized, mapping = PIIAnonymizer.anonymize(raw)

    assert "alex.smith@example.co.uk" not in anonymized
    assert "+44 7123 456789" not in anonymized
    assert "[EMAIL_1]" in anonymized
    assert "[PHONE_1]" in anonymized

    restored = PIIAnonymizer.deanonymize(anonymized, mapping)
    assert restored == raw


def test_pii_anonymizer_custom_entities():
    raw = "My employer Acme Global Tech pays my salary into my account."
    anonymized, mapping = PIIAnonymizer.anonymize(raw, custom_entities=["Acme Global Tech"])

    assert "Acme Global Tech" not in anonymized
    assert "[ENTITY_1]" in anonymized

    restored = PIIAnonymizer.deanonymize(anonymized, mapping)
    assert restored == raw


def test_pii_mask_one_way():
    raw = "Sort 12-34-56, Acc 12345678, user@domain.com"
    masked = PIIAnonymizer.mask_pii_one_way(raw)

    assert "••-••-56" in masked
    assert "••••5678" in masked
    assert "@domain.com" in masked
    assert "12-34-56" not in masked
    assert "12345678" not in masked
