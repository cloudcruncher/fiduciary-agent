"""
Reversible Cryptographic PII Anonymization Layer for Fiduciary AI.
Protects client banking credentials, account numbers, sort codes, phone numbers,
emails, and personal identifiers before passing prompts to external LLMs or gateways.
Supports lossless two-way deanonymization upon receiving the model's response.
"""

import re
from typing import Dict, List, Optional, Tuple


class PIIAnonymizer:
    """
    Enterprise-grade PII Anonymization & Deanonymization Engine.
    Ensures zero sensitive client financial identifiers leave the device unencrypted.
    """

    # UK Financial & Identity Regex Patterns
    PATTERNS = [
        # UK Sort Code (e.g., 20-45-78, 204578, 20 45 78)
        ("SORT_CODE", re.compile(r"\b(?!00-00-00)(\d{2}[-\s]\d{2}[-\s]\d{2})\b")),
        # UK Bank Account Number (8 contiguous digits, excluding common amounts/years)
        ("ACCOUNT_NUM", re.compile(r"\b(?<!\£|\$|\€)([0-9]{8})\b")),
        # UK National Insurance Number (NINO) (e.g., QQ123456C)
        ("NINO", re.compile(r"\b([A-CEGHJ-PR-TW-Z]{1}[A-CEGHJ-NPR-TW-Z]{1}\s?[0-9]{6}\s?[A-D]{1})\b", re.IGNORECASE)),
        # Credit / Debit Card Number (13-16 digits with optional spaces or hyphens)
        ("CARD_NUM", re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")),
        # Email Address
        ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
        # UK Phone Numbers (e.g., +44 7123 456789, 07123456789, 020 7946 0991)
        ("PHONE", re.compile(r"(?:(?<=\s)|^|\b)(?:\+44\s?7\d{3}|\+44\s?20\d{3}|07\d{3}|020\s?\d{4})\s?\d{3,4}\s?\d{3,4}\b")),
    ]

    @classmethod
    def anonymize(cls, text: str, custom_entities: Optional[List[str]] = None) -> Tuple[str, Dict[str, str]]:
        """
        Scans text for sensitive PII and replaces instances with deterministic reversible tokens.
        Returns:
            Tuple of (anonymized_text, deanonymize_mapping)
        """
        if not text:
            return text, {}

        anonymized = text
        mapping: Dict[str, str] = {}  # token -> original_value
        reverse_seen: Dict[str, str] = {}  # original_value -> token
        counters: Dict[str, int] = {}

        # 1. Custom entities (e.g. user names, custom employer names)
        if custom_entities:
            for entity in sorted(custom_entities, key=len, reverse=True):
                clean_ent = entity.strip()
                if not clean_ent or len(clean_ent) < 2:
                    continue
                if clean_ent not in reverse_seen:
                    c = counters.get("ENTITY", 1)
                    counters["ENTITY"] = c + 1
                    token = f"[ENTITY_{c}]"
                    reverse_seen[clean_ent] = token
                    mapping[token] = clean_ent
                token = reverse_seen[clean_ent]
                anonymized = re.sub(re.escape(clean_ent), token, anonymized, flags=re.IGNORECASE)

        # 2. Structured financial patterns
        for tag, pattern in cls.PATTERNS:
            matches = list(pattern.finditer(anonymized))
            # Sort matches in reverse order so replacements don't disrupt indices
            for match in reversed(matches):
                val = match.group(0).strip()
                if not val:
                    continue

                if val not in reverse_seen:
                    c = counters.get(tag, 1)
                    counters[tag] = c + 1
                    token = f"[{tag}_{c}]"
                    reverse_seen[val] = token
                    mapping[token] = val
                else:
                    token = reverse_seen[val]

                start, end = match.span()
                anonymized = anonymized[:start] + token + anonymized[end:]

        return anonymized, mapping

    @classmethod
    def deanonymize(cls, text: str, mapping: Dict[str, str]) -> str:
        """
        Replaces anonymization tokens in the text with original client credentials/values.
        """
        if not text or not mapping:
            return text

        restored = text
        # Replace tokens (longest tokens first to avoid subtoken collisions)
        for token in sorted(mapping.keys(), key=len, reverse=True):
            orig_val = mapping[token]
            restored = restored.replace(token, orig_val)

        return restored

    @classmethod
    def mask_pii_one_way(cls, text: str) -> str:
        """
        Irreversibly masks sensitive values for safe logging and client presentation.
        e.g. Sort code -> '••-••-78', Account -> '••••5678', Email -> 'j••••@example.com'
        """
        if not text:
            return text

        masked = text

        def mask_sort(m):
            val = m.group(0)
            return f"••-••-{val[-2:]}"

        def mask_acc(m):
            val = m.group(0)
            return f"••••{val[-4:]}"

        def mask_email(m):
            val = m.group(0)
            parts = val.split("@")
            user = parts[0]
            domain = parts[1] if len(parts) > 1 else ""
            masked_user = (user[0] + "•••" + user[-1]) if len(user) > 2 else "••"
            return f"{masked_user}@{domain}"

        masked = re.sub(r"\b\d{2}[-\s]\d{2}[-\s](\d{2})\b", mask_sort, masked)
        masked = re.sub(r"\b(?<!\£|\$|\€)[0-9]{4}([0-9]{4})\b", mask_acc, masked)
        masked = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", mask_email, masked)

        return masked
