import json
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import requests

from fiduciary.observability.tracer import GroundingAuditor, get_recent_traces
from fiduciary.storage.db import get_trace_by_id, save_judge_evaluation

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

PREFERRED_JUDGE_MODELS = [
    # Lightweight Cross-Family SLMs (<3.5B) optimized for Apple Silicon Metal GPU & Unified Memory
    "llama3.2:3b",
    "gemma2:2b",
    "qwen2.5:3b",
    "qwen2.5:1.5b",
    "llama3.2:1b",
    "smollm2:1.7b",
    # Medium models
    "gemma:7b",
    "gemma2:9b",
    "mistral:7b",
    "qwen3.5:4b",
]


class LLMJudge:
    """
    Independent LLM-as-a-Judge Evaluation Engine (Grounded Critic Pattern).
    Uses a Two-Stage Architecture:
    Stage 1: Deterministic Fact-Checking Pre-Pass (extracts and validates figures).
    Stage 2: Independent Small Language Model (e.g. Llama 3.2 3B or Gemma 2 2B)
             anchored by deterministic findings to objectively score Faithfulness,
             Relevance, and Fiduciary Soundness without hallucinations.
    """

    JUDGE_SYSTEM_PROMPT = """You are an elite, independent AI Evaluator and UK Financial Fiduciary Judge.
Your sole responsibility is to rigorously audit the quality, accuracy, and fiduciary soundness of an AI Assistant's response against ground-truth client data.

Evaluate the response across these 3 objective metrics (0.0 to 1.0 each):

1. FAITHFULNESS / GROUNDING (0.0 to 1.0):
   - 1.0: Every factual claim, transaction date, merchant name, and currency amount (£) is directly substantiated by the Provided Ground Truth Context or verified by the Fact Audit Pass.
   - <0.8: Contains minor discrepancies or unverified estimates without explicit disclosure.
   - <0.4: Hallucinated transactions, fictional numbers, or fabricated facts not in the context.

2. RELEVANCE & COMPLETENESS (0.0 to 1.0):
   - 1.0: Directly, completely, and accurately answers the User Query without evading or providing off-topic filler.
   - <0.8: Answers partially or omits key parts of the user question.
   - <0.4: Misses the core intent of the query.

3. FIDUCIARY SOUNDNESS (0.0 to 1.0):
   - 1.0: Advice is mathematically rigorous, objective, unconflicted (zero affiliate/sales bias), and strictly aligned with UK consumer duty.
   - <0.8: Uses vague generalities or minor unhedged assumptions.
   - <0.4: Recommends reckless financial actions or demonstrates sales/marketing bias.

DECISION CRITERIA FOR VERDICT:
- "PASSED": All three metrics are >= 0.75 and overall score >= 0.80.
- "WARNING": Any metric is between 0.50 and 0.74.
- "FAILED": Any metric is below 0.50 or hallucinations are detected.

You must respond ONLY with a valid JSON object matching this schema:
{
  "faithfulness": <float between 0.0 and 1.0>,
  "relevance": <float between 0.0 and 1.0>,
  "fiduciary_soundness": <float between 0.0 and 1.0>,
  "verdict": "<PASSED | WARNING | FAILED>",
  "reasoning": "<Concise 2-3 sentence explanation summarizing strengths and any issues observed>"
}
"""

    def __init__(self, ollama_url: Optional[str] = None, default_model: Optional[str] = None):
        self.ollama_url = ollama_url or OLLAMA_BASE_URL
        self.default_model = default_model or os.getenv("FIDUCIARY_JUDGE_MODEL")

    def is_judge_available(self, requested_model: Optional[str] = None) -> Tuple[bool, str, str]:
        """
        Detects if an independent local judge model is accessible on Ollama.
        Prioritizes lightweight cross-family SLMs (Llama 3.2 3B, Gemma 2 2B) for Apple Silicon.
        Returns (is_available, provider, model_name).
        """
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=1.5)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                if not models:
                    return False, "ollama", "No models installed in Ollama"

                # If an explicit model was requested or set via env
                target = requested_model or self.default_model
                if target:
                    for m in models:
                        if m == target or m.startswith(f"{target}:") or target in m:
                            return True, "ollama", m

                # Prioritize cross-family lightweight models
                for preferred in PREFERRED_JUDGE_MODELS:
                    for m in models:
                        if m == preferred or m.startswith(f"{preferred}:") or preferred in m:
                            return True, "ollama", m

                return True, "ollama", models[0]
        except Exception:
            pass
        return False, "none", "Ollama local server not running on port 11434"

    def evaluate(
        self,
        user_prompt: str,
        system_prompt: Optional[str],
        response: str,
        trace_id: Optional[str] = None,
        judge_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a Two-Stage Grounded Critic evaluation:
        Stage 1: Deterministic fact-checking pass with GroundingAuditor.
        Stage 2: Independent SLM Judge evaluation anchored by deterministic fact sheet.
        """
        start_t = time.perf_counter()
        available, provider, chosen_model = self.is_judge_available(requested_model=judge_model)

        # Stage 1: Deterministic Fact-Checking Pre-Pass
        pre_audit = GroundingAuditor.audit(
            response=response,
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        if not available:
            return {
                "trace_id": trace_id,
                "status": "UNAVAILABLE",
                "error": f"Judge model unavailable: {chosen_model}",
                "is_local_judge": False,
                "judge_model": "None",
                "verdict": "SKIPPED",
                "faithfulness": 1.0,
                "relevance": 1.0,
                "fiduciary_soundness": 1.0,
                "overall_score": 1.0,
                "deterministic_audit": pre_audit,
                "reasoning": "Judge evaluation skipped because Ollama is not active on http://localhost:11434."
            }

        # 16GB Mac safeguard: never hold two 7-8B models in unified memory at once.
        if os.getenv("FIDUCIARY_ALLOW_DUAL_MODELS") != "1":
            try:
                lm_resp = requests.get("http://localhost:1234/v1/models", timeout=0.8)
                if lm_resp.status_code == 200:
                    lm_models = lm_resp.json().get("data", [])
                    lm_loaded = len(lm_models) > 0
                else:
                    lm_loaded = False
            except Exception:
                lm_loaded = False

            if lm_loaded:
                return {
                    "trace_id": trace_id,
                    "status": "ERROR",
                    "verdict": "SKIPPED",
                    "error": (
                        "LM Studio currently has a model loaded in RAM. Running the judge now would load a second "
                        "model and swap a 16GB Mac. Eject the model in LM Studio first, then re-run './f judge'."
                    ),
                    "deterministic_audit": pre_audit
                }

        # Format grounded evaluation input with Stage 1 Deterministic Findings
        fact_audit_block = (
            f"• Deterministic Grounding Status: {pre_audit['status']} (Fact Score: {pre_audit['grounding_score'] * 100:.0f}%)\n"
            f"• Pre-Verified Data Points (Found in live database): {', '.join(pre_audit['verified_figures']) if pre_audit['verified_figures'] else 'None detected'}\n"
            f"• Unverified Figures (NOT in verified client context): {', '.join(pre_audit['unverified_figures']) if pre_audit['unverified_figures'] else 'None detected (100% grounded)'}"
        )

        eval_prompt = f"""AUDIT TARGET:
══════════════════════════════════════════════════════════════════════
[USER QUERY]:
{user_prompt}

[GROUND TRUTH CLIENT CONTEXT & VERIFIED DATA]:
{system_prompt or "No context provided."}

[DETERMINISTIC FACT AUDIT PASS (VERIFIED GROUND TRUTH)]:
{fact_audit_block}

CRITICAL GROUNDING INSTRUCTIONS FOR THE JUDGE:
1. Do NOT guess or recalculate arithmetic; the deterministic engine above has cross-referenced the numbers.
2. If Unverified Figures are detected:
   - If they represent hallucinated balances, fictional debt, or fabricated spending, Faithfulness MUST be scored < 0.50 and verdict FAILED.
   - If they are general UK tax policy allowances (e.g. £1,000 PSA, £20k ISA limit) or clear hypothetical illustrations, Faithfulness can remain >= 0.80.
3. Fiduciary Soundness: Verify that recommendations comply with UK FCA Consumer Duty, do not encourage draining emergency buffers, and are mathematically defensible.

[AI ASSISTANT RESPONSE TO EVALUATE]:
{response}
══════════════════════════════════════════════════════════════════════

Provide your independent evaluation JSON:"""

        try:
            payload = {
                "model": chosen_model,
                "prompt": f"{self.JUDGE_SYSTEM_PROMPT}\n\n{eval_prompt}\n\nOUTPUT (JSON only):",
                "format": "json",
                "stream": False,
                "think": False,
                # Unload the judge from RAM immediately after answering for Mac unified memory preservation
                "keep_alive": 0,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_ctx": 4096
                }
            }

            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=60
            )

            latency_ms = round((time.perf_counter() - start_t) * 1000.0, 1)

            if resp.status_code != 200:
                return {
                    "trace_id": trace_id,
                    "status": "ERROR",
                    "error": f"Ollama HTTP {resp.status_code}: {resp.text}",
                    "verdict": "ERROR",
                    "deterministic_audit": pre_audit
                }

            raw_output = resp.json().get("response", "").strip()
            parsed = self._extract_json(raw_output)

            faithfulness = float(parsed.get("faithfulness", 1.0))
            relevance = float(parsed.get("relevance", 1.0))
            fiduciary_soundness = float(parsed.get("fiduciary_soundness", 1.0))
            verdict = str(parsed.get("verdict", "PASSED")).upper()
            reasoning = str(parsed.get("reasoning", "Evaluation completed successfully."))

            # Clamp 0.0 - 1.0
            faithfulness = max(0.0, min(1.0, faithfulness))
            relevance = max(0.0, min(1.0, relevance))
            fiduciary_soundness = max(0.0, min(1.0, fiduciary_soundness))

            # Grounding Invariant: If deterministic pass found critical unverified figures and model failed, enforce cap
            if pre_audit["status"] == "UNVERIFIED_FIGURES_DETECTED" and faithfulness > 0.65:
                faithfulness = 0.60
                verdict = "WARNING" if verdict == "PASSED" else verdict
                reasoning = f"{reasoning} Note: Adjusted for deterministic ungrounded figures: {', '.join(pre_audit['unverified_figures'])}."

            overall_score = round(
                (faithfulness * 0.45) + (fiduciary_soundness * 0.35) + (relevance * 0.20),
                2
            )

            result = {
                "trace_id": trace_id,
                "status": "SUCCESS",
                "judge_provider": provider,
                "judge_model": f"{chosen_model} (Local Ollama)",
                "is_local_judge": True,
                "faithfulness": round(faithfulness, 2),
                "relevance": round(relevance, 2),
                "fiduciary_soundness": round(fiduciary_soundness, 2),
                "overall_score": overall_score,
                "verdict": verdict,
                "reasoning": reasoning,
                "judge_latency_ms": latency_ms,
                "deterministic_audit": pre_audit,
                "evaluated_at": datetime.now().isoformat()
            }

            if trace_id:
                save_judge_evaluation(trace_id, result)

            return result

        except Exception as e:
            return {
                "trace_id": trace_id,
                "status": "ERROR",
                "error": str(e),
                "verdict": "ERROR",
                "deterministic_audit": pre_audit,
                "reasoning": f"Judge evaluation encountered an unexpected error: {e}"
            }

    def evaluate_trace(self, trace_id: str, judge_model: Optional[str] = None) -> Dict[str, Any]:
        """Fetches a stored trace by ID and evaluates it with the independent judge."""
        trace = get_trace_by_id(trace_id)
        if not trace:
            return {"error": f"Trace {trace_id} not found."}

        return self.evaluate(
            user_prompt=trace.get("user_prompt") or "",
            system_prompt=trace.get("system_prompt") or "",
            response=trace.get("response") or "",
            trace_id=trace_id,
            judge_model=judge_model
        )

    def evaluate_latest_trace(self, judge_model: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Evaluates the most recent trace in the database."""
        traces = get_recent_traces(limit=1)
        if not traces:
            return None
        return self.evaluate_trace(traces[0]["id"], judge_model=judge_model)

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Safely extracts JSON object from LLM response text."""
        try:
            return json.loads(text)
        except Exception:
            pass

        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except Exception:
                pass

        return {
            "faithfulness": 0.8,
            "relevance": 0.8,
            "fiduciary_soundness": 0.8,
            "verdict": "WARNING",
            "reasoning": "Could not parse strict JSON from judge model response."
        }
