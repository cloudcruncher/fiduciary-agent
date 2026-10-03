import json
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fiduciary.storage.db import get_connection


class GroundingAuditor:
    """
    Real-time Grounding & Hallucination Auditor.
    Scans LLM completions to verify that financial figures, interest yields,
    and cash metrics originate directly from the verified deterministic data
    injected in the system context.
    """

    ALLOWED_SYSTEM_CONSTANTS = {
        "0", "0.0", "0.00", "1", "1.0", "2", "3", "4", "5", "6", "7", "12",
        "14", "30", "60", "90", "100", "365", "2024", "2025", "2026", "2027"
    }

    @classmethod
    def audit(cls, response: str, system_prompt: Optional[str] = None, user_prompt: Optional[str] = None) -> Dict[str, Any]:
        if not response:
            return {
                "status": "EMPTY",
                "grounding_score": 1.0,
                "verified_figures": [],
                "unverified_figures": [],
                "summary": "Empty response."
            }

        context_text = f"{system_prompt or ''} {user_prompt or ''}".lower()

        # Extract currency patterns like £27.26, £1,540.80, £18.00
        currency_pattern = re.compile(r"£\s*[0-9,]+(?:\.[0-9]{1,2})?")
        response_currencies = currency_pattern.findall(response)

        # Extract percentage yields like 4.87%, 20%, 40%
        pct_pattern = re.compile(r"\b\d+(?:\.\d+)?%")
        response_pcts = pct_pattern.findall(response)

        total_claims = len(response_currencies) + len(response_pcts)
        if total_claims == 0:
            return {
                "status": "VERIFIED_GROUNDED",
                "grounding_score": 1.0,
                "verified_figures": [],
                "unverified_figures": [],
                "summary": "100% Grounded. No ungrounded financial claims or figures detected."
            }

        verified = []
        unverified = []

        # Check currencies
        for curr in response_currencies:
            clean_val = curr.replace("£", "").replace(",", "").strip()
            # Check if formatted string or raw number exists in context
            norm_curr = curr.lower().replace(" ", "")
            if norm_curr in context_text or clean_val in context_text:
                verified.append(curr)
            else:
                # Allow rounding / integer approximations if present (e.g. £510 from £513.60 or £1,541 from £1,540.80)
                try:
                    num = float(clean_val)
                    if str(int(num)) in context_text or f"{num:.2f}" in context_text or clean_val in cls.ALLOWED_SYSTEM_CONSTANTS:
                        verified.append(curr)
                    else:
                        unverified.append(curr)
                except ValueError:
                    unverified.append(curr)

        # Check percentages
        for pct in response_pcts:
            if pct.lower() in context_text:
                verified.append(pct)
            else:
                clean_pct = pct.replace("%", "").strip()
                if clean_pct in cls.ALLOWED_SYSTEM_CONSTANTS or clean_pct in context_text:
                    verified.append(pct)
                else:
                    unverified.append(pct)

        score = len(verified) / total_claims if total_claims > 0 else 1.0

        if not unverified:
            status = "VERIFIED_GROUNDED"
            summary = f"100% Grounded ({len(verified)}/{total_claims} verified data points cited from live financial context)."
        elif score >= 0.70:
            status = "PARTIALLY_GROUNDED"
            summary = f"Partially Grounded ({len(verified)}/{total_claims} verified). Unverified figures: {', '.join(unverified[:4])}."
        else:
            status = "UNVERIFIED_FIGURES_DETECTED"
            summary = f"Audit Warning: {len(unverified)} ungrounded figures detected ({', '.join(unverified[:4])})."

        return {
            "status": status,
            "grounding_score": round(score, 2),
            "verified_figures": list(set(verified)),
            "unverified_figures": list(set(unverified)),
            "summary": summary
        }


def record_llm_trace(
    caller: str,
    provider: str,
    model: str,
    latency_ms: float,
    user_prompt: str,
    system_prompt: Optional[str],
    response: str,
    tools_used: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Records an immutable structured trace of an LLM invocation."""
    trace_id = f"tr_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now().isoformat()

    audit_result = GroundingAuditor.audit(
        response=response,
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO llm_traces (
            id, timestamp, caller, provider, model, latency_ms,
            user_prompt, system_prompt, response,
            grounding_status, grounding_score, unverified_tokens_json,
            tools_used_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trace_id,
            now_iso,
            caller,
            provider,
            model or "unknown",
            round(latency_ms, 1),
            user_prompt,
            system_prompt or "",
            response,
            audit_result["status"],
            audit_result["grounding_score"],
            json.dumps(audit_result["unverified_figures"]),
            json.dumps(tools_used or [])
        ))
        conn.commit()
        conn.close()
    except Exception:
        # Observability should never crash core agent operations
        pass

    return {
        "trace_id": trace_id,
        "timestamp": now_iso,
        "caller": caller,
        "provider": provider,
        "model": model,
        "latency_ms": latency_ms,
        "tools_used": tools_used or [],
        "audit": audit_result
    }


def get_recent_traces(limit: int = 30) -> List[Dict[str, Any]]:
    """Retrieves recent traces for UI and CLI inspection."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM llm_traces
        ORDER BY timestamp DESC
        LIMIT ?
        """, (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        # Parse unverified tokens, judge evaluation, and tools used
        for r in rows:
            try:
                r["unverified_figures"] = json.loads(r.get("unverified_tokens_json") or "[]")
            except Exception:
                r["unverified_figures"] = []

            if r.get("judge_result_json"):
                try:
                    r["judge_evaluation"] = json.loads(r["judge_result_json"])
                except Exception:
                    r["judge_evaluation"] = None
            else:
                r["judge_evaluation"] = None

            if r.get("tools_used_json"):
                try:
                    r["tools_used"] = json.loads(r["tools_used_json"])
                except Exception:
                    r["tools_used"] = []
            else:
                r["tools_used"] = []

        return rows
    except Exception:
        return []


def clear_all_traces():
    """Purges the trace log."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM llm_traces")
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_observability_metrics() -> Dict[str, Any]:
    """Computes summary metrics across all historical traces."""
    traces = get_recent_traces(limit=100)
    if not traces:
        return {
            "total_invocations": 0,
            "avg_latency_ms": 0.0,
            "grounding_pass_rate_pct": 100.0,
            "local_share_pct": 100.0,
            "judged_count": 0,
            "judge_pass_rate_pct": 100.0,
            "latest_trace": None
        }

    total = len(traces)
    avg_latency = sum(t.get("latency_ms", 0.0) for t in traces) / total
    grounded_count = sum(1 for t in traces if t.get("grounding_status") == "VERIFIED_GROUNDED")
    local_count = sum(1 for t in traces if t.get("provider") == "local")
    judged = [t for t in traces if t.get("judge_evaluation")]
    judged_count = len(judged)
    passed_count = sum(1 for t in judged if (t.get("judge_evaluation") or {}).get("verdict") == "PASSED")
    judge_pass_rate_pct = round((passed_count / judged_count) * 100, 1) if judged_count > 0 else 100.0

    return {
        "total_invocations": total,
        "avg_latency_ms": round(avg_latency, 1),
        "grounding_pass_rate_pct": round((grounded_count / total) * 100, 1),
        "local_share_pct": round((local_count / total) * 100, 1),
        "judged_count": judged_count,
        "judge_pass_rate_pct": judge_pass_rate_pct,
        "latest_trace": traces[0] if traces else None
    }

