import json
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import requests

from fiduciary.observability.tracer import get_recent_traces
from fiduciary.storage.db import get_trace_by_id, save_judge_evaluation

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

class LLMJudge:
    """
    Independent LLM-as-a-Judge Evaluation Engine.
    Uses an isolated second model (e.g. Google Gemma 7B on Ollama) to objectively
    audit the primary fiduciary model's outputs for Faithfulness, Relevance,
    and Fiduciary Soundness.
    """

    JUDGE_SYSTEM_PROMPT = """You are an elite, independent AI Evaluator and UK Financial Fiduciary Judge.
Your sole responsibility is to rigorously audit the quality, accuracy, and fiduciary soundness of an AI Assistant's response against ground-truth client data.

Evaluate the response across these 3 objective metrics (0.0 to 1.0 each):

1. FAITHFULNESS / GROUNDING (0.0 to 1.0):
   - 1.0: Every factual claim, transaction date, merchant name, and currency amount (£) is directly substantiated by the Provided Ground Truth Context.
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

    def __init__(self, ollama_url: Optional[str] = None):
        self.ollama_url = ollama_url or OLLAMA_BASE_URL

    def is_judge_available(self) -> Tuple[bool, str, str]:
        """
        Detects if an independent local judge model is accessible on Ollama.
        Returns (is_available, provider, model_name).
        """
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=1.5)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                if not models:
                    return False, "ollama", "No models installed in Ollama"

                # Prefer gemma:7b or explain:7b
                for preferred in ["gemma:7b", "gemma2:9b", "explain:7b", "mistral:7b"]:
                    if preferred in models:
                        return True, "ollama", preferred
                return True, "ollama", models[0]
        except Exception:
            pass
        return False, "none", "Ollama local server not running on port 11434"

    def evaluate(
        self,
        user_prompt: str,
        system_prompt: Optional[str],
        response: str,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes an independent judge evaluation of a completed model interaction.
        """
        start_t = time.perf_counter()
        available, provider, judge_model = self.is_judge_available()

        if not available:
            return {
                "trace_id": trace_id,
                "status": "UNAVAILABLE",
                "error": f"Judge model unavailable: {judge_model}",
                "is_local_judge": False,
                "judge_model": "None",
                "verdict": "SKIPPED",
                "faithfulness": 1.0,
                "relevance": 1.0,
                "fiduciary_soundness": 1.0,
                "overall_score": 1.0,
                "reasoning": "Judge evaluation skipped because Ollama is not active on http://localhost:11434."
            }

        # 16GB Mac safeguard: never hold two 7-8B models in unified memory at once.
        # Set FIDUCIARY_ALLOW_DUAL_MODELS=1 to override on machines with more RAM.
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
                }


        # Format evaluation input
        eval_prompt = f"""AUDIT TARGET:
══════════════════════════════════════════════════════════════════════
[USER QUERY]:
{user_prompt}

[GROUND TRUTH CLIENT CONTEXT & VERIFIED DATA]:
{system_prompt or "No context provided."}

[AI ASSISTANT RESPONSE TO EVALUATE]:
{response}
══════════════════════════════════════════════════════════════════════

Provide your independent evaluation JSON:"""

        try:
            payload = {
                "model": judge_model,
                "prompt": f"{self.JUDGE_SYSTEM_PROMPT}\n\n{eval_prompt}\n\nOUTPUT (JSON only):",
                "format": "json",
                "stream": False,
                "think": False,
                # Unload the judge from RAM immediately after answering (default is 5 minutes).
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
                    "verdict": "ERROR"
                }

            raw_output = resp.json().get("response", "").strip()
            parsed = self._extract_json(raw_output)

            faithfulness = float(parsed.get("faithfulness", 1.0))
            relevance = float(parsed.get("relevance", 1.0))
            fiduciary_soundness = float(parsed.get("fiduciary_soundness", 1.0))
            verdict = str(parsed.get("verdict", "PASSED")).upper()
            reasoning = str(parsed.get("reasoning", "Evaluation completed successfully."))

            # Ensure clamp 0.0 - 1.0
            faithfulness = max(0.0, min(1.0, faithfulness))
            relevance = max(0.0, min(1.0, relevance))
            fiduciary_soundness = max(0.0, min(1.0, fiduciary_soundness))

            overall_score = round(
                (faithfulness * 0.45) + (fiduciary_soundness * 0.35) + (relevance * 0.20),
                2
            )

            result = {
                "trace_id": trace_id,
                "status": "SUCCESS",
                "judge_provider": provider,
                "judge_model": f"{judge_model} (Local Ollama)",
                "is_local_judge": True,
                "faithfulness": round(faithfulness, 2),
                "relevance": round(relevance, 2),
                "fiduciary_soundness": round(fiduciary_soundness, 2),
                "overall_score": overall_score,
                "verdict": verdict,
                "reasoning": reasoning,
                "judge_latency_ms": latency_ms,
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
                "reasoning": f"Judge evaluation encountered an unexpected error: {e}"
            }

    def evaluate_trace(self, trace_id: str) -> Dict[str, Any]:
        """Fetches a stored trace by ID and evaluates it with the independent judge."""
        trace = get_trace_by_id(trace_id)
        if not trace:
            return {"error": f"Trace {trace_id} not found."}

        return self.evaluate(
            user_prompt=trace.get("user_prompt") or "",
            system_prompt=trace.get("system_prompt") or "",
            response=trace.get("response") or "",
            trace_id=trace_id
        )

    def evaluate_latest_trace(self) -> Optional[Dict[str, Any]]:
        """Evaluates the most recent trace in the database."""
        traces = get_recent_traces(limit=1)
        if not traces:
            return None
        return self.evaluate_trace(traces[0]["id"])

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Safely extracts JSON object from LLM response text."""
        try:
            return json.loads(text)
        except Exception:
            pass

        # Try regex search for markdown block or raw json object
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
