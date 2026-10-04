"""
Prompt Guard: Security & Prompt Injection Defense Layer for Personal Fiduciary Agent.
Detects and neutralizes jailbreaks, instruction overrides, delimiter attacks,
and unauthorized data exfiltration attempts before queries reach the LLM.
"""

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PromptGuardResult:
    is_safe: bool
    risk_score: float
    flagged_patterns: List[str]
    sanitized_query: str
    guard_response: Optional[str] = None


class PromptGuard:
    """Production-grade Prompt Guard defense engine for LLM inputs."""

    # 1. System Prompt Override & Jailbreak Patterns
    OVERRIDE_PATTERNS = [
        (r"ignore\s+(?:all\s+)?(?:previous|prior|above|existing|system|\s+)*\s*(?:instructions|rules|directives|prompts|commands)", "INSTRUCTION_OVERRIDE"),
        (r"disregard\s+(?:all\s+)?(?:previous|prior|above|system|\s+)*\s*(?:instructions|rules|directives|prompts)", "INSTRUCTION_DISREGARD"),
        (r"forget\s+(?:all\s+)?(?:your\s+)?(?:previous|prior|system|\s+)*\s*(?:rules|instructions|directives|prompts|commands)", "RULE_FORGET"),
        (r"bypass\s+(?:all\s+)?(?:safety|security|ethics|guardrails|protocols)", "SAFETY_BYPASS"),
        (r"\b(?:dan\s+mode|jailbreak|unrestricted\s+mode|developer\s+mode)\b", "JAILBREAK_MODE"),
        (r"(?:reveal|print|show|output|leak|dump)\s+(?:the|your\s+)?(?:(?:system|initial|base|hidden)\s+)?(?:prompt|instructions|rules)", "SYSTEM_PROMPT_EXTRACTION"),
        (r"(?:you\s+are\s+now|act\s+as)\s+(?:an?\s+)?(?:evil|unrestricted|unfiltered|malicious|dark\s+web)\b", "ROLE_HIJACKING"),
        (r"output\s+[\"']?(?:hacked|pwned|bypassed)[\"']?", "CANARY_INJECTION"),
    ]

    # 2. Control Delimiter & Token Escapes
    DELIMITER_PATTERNS = [
        (r"<\|(?:im_start|im_end|endoftext)\|>", "CHATML_CONTROL_TOKEN"),
        (r"\[/?(?:INST|SYS)\]", "LLAMA_CONTROL_TOKEN"),
        (r"<\/?(?:system|instruction|prompt_context|verified_financial_state)>", "XML_BOUNDARY_ESCAPE"),
        (r"={3,}\s*(?:END|SYSTEM|BEGIN)\s*(?:PROMPT|CONTEXT|RULES)\s*={3,}", "DELIMITER_BREAKOUT"),
    ]

    # 3. Database & Secret Exfiltration Probes
    EXFILTRATION_PATTERNS = [
        (r"\b(?:drop\s+table|delete\s+from\s+transactions|insert\s+into\s+sqlite_master)\b", "SQL_INJECTION_PROBE"),
        (r"(?:show|print|leak|dump)\s+(?:me\s+)?(?:all\s+)?(?:api[_\s]?keys?|private[_\s]?keys?|database\s+passwords?|secret\s+tokens?)", "SECRET_EXFILTRATION_PROBE"),
    ]

    @classmethod
    def inspect(cls, raw_query: str) -> PromptGuardResult:
        """
        Inspects query for prompt injection and security risks.
        Returns safety verdict, risk score, list of flags, and sanitized text.
        """
        if not raw_query or not raw_query.strip():
            return PromptGuardResult(
                is_safe=True,
                risk_score=0.0,
                flagged_patterns=[],
                sanitized_query=""
            )

        flagged: List[str] = []
        score = 0.0

        clean_text = raw_query.strip()

        # Check Overrides
        for pattern, label in cls.OVERRIDE_PATTERNS:
            if re.search(pattern, clean_text, re.IGNORECASE):
                flagged.append(label)
                score += 0.55

        # Check Delimiters
        for pattern, label in cls.DELIMITER_PATTERNS:
            if re.search(pattern, clean_text, re.IGNORECASE):
                flagged.append(label)
                score += 0.55

        # Check Exfiltration
        for pattern, label in cls.EXFILTRATION_PATTERNS:
            if re.search(pattern, clean_text, re.IGNORECASE):
                flagged.append(label)
                score += 0.60

        # Sanitize query by neutralizing control characters and boundary tags
        sanitized = clean_text
        sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", sanitized)
        sanitized = re.sub(r"<\|.*?\|>", "", sanitized)
        sanitized = re.sub(r"\[/?(?:INST|SYS)\]", "", sanitized, flags=re.IGNORECASE)

        is_safe = score < 0.50

        guard_msg = None
        if not is_safe:
            labels_str = ", ".join(dict.fromkeys(flagged))
            guard_msg = (
                f"🛡️ **Prompt Guard Notice**\n\n"
                f"The submitted query was flagged for an unauthorized prompt directive or security anomaly (`{labels_str}`).\n\n"
                f"As an independent personal fiduciary agent, my operating boundaries are strictly confined to analyzing "
                f"and reporting on your verified financial state, bank balances, and tax calculations.\n\n"
                f"Please submit an inquiry regarding your accounts, spending, or cash runway."
            )

        return PromptGuardResult(
            is_safe=is_safe,
            risk_score=min(score, 1.0),
            flagged_patterns=flagged,
            sanitized_query=sanitized,
            guard_response=guard_msg
        )

    @classmethod
    def wrap_context_boundaries(cls, ground_truth_context: str) -> str:
        """
        Wraps verified client context in secure boundary tags that prevent
        user query text from masquerading as system context.
        """
        return (
            "<verified_financial_context>\n"
            f"{ground_truth_context}\n"
            "</verified_financial_context>"
        )
