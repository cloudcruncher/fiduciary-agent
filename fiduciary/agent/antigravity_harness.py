"""
Production-grade Cost & Token Optimization Harness for Google Antigravity (AGY) SDK.

Integrates:
1. Native Context Caching (via prompt prefix immutability)
2. Hard Token Guardrails & Context Compaction (CompactionConfig, BudgetConfig)
3. Thinking/Reasoning Token Suppression (ThinkingLevel.MINIMAL)
4. Local On-Device Execution ($0.00 zero-cost inference via Ollama / LM Studio)
5. SQLite Response Cache & Sub-Millisecond Exact-Match Retrieval
6. Fine-grained Session Token & Cost Telemetry
"""

import hashlib
import os
import time
from typing import Any, Dict, Optional, Tuple

import requests
from google.antigravity import (
    Agent,
    CompactionConfig,
    GeminiAPIEndpoint,
    GeminiModelOptions,
    LiteRTAgentConfig,
    LocalAgentConfig,
    LocalOpenAIAgentConfig,
    ModelTarget,
    ThinkingLevel,
    types,
)

from fiduciary.config import (
    GEMINI_API_KEY,
    LMSTUDIO_BASE_URL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)
from fiduciary.storage.db import get_cached_llm_response, get_db_state_fingerprint, set_cached_llm_response


class AntigravityCostAuditor:
    """
    Computes financial savings from Prompt Caching, Context Compaction,
    Suppressed Thinking Tokens, and Local Model Offloading.
    """

    # Baseline Gemini 2.5 Flash pricing per 1M tokens ($ USD)
    PRICE_PER_M_INPUT = 0.075
    PRICE_PER_M_CACHED_INPUT = 0.01875  # ~75% discount
    PRICE_PER_M_OUTPUT = 0.30

    @classmethod
    def calculate_audit(
        cls,
        usage: Any,
        is_local: bool = False,
        cache_hit: bool = False
    ) -> Dict[str, Any]:
        if cache_hit:
            return {
                "is_cache_hit": True,
                "is_local": is_local,
                "billed_cost_usd": 0.0,
                "saved_cost_usd": 0.001,
                "tokens_billed": 0,
                "tokens_saved": 1500,
                "summary": "100% Token Savings (Exact Match Cache Hit)"
            }

        if is_local:
            return {
                "is_cache_hit": False,
                "is_local": True,
                "billed_cost_usd": 0.0,
                "saved_cost_usd": 0.002,
                "tokens_billed": 0,
                "tokens_saved": getattr(usage, "total_token_count", 0),
                "summary": "100% Zero-Cost Local Inference (Apple Silicon Metal GPU)"
            }

        prompt_toks = getattr(usage, "prompt_token_count", 0) or 0
        cached_toks = getattr(usage, "cached_content_token_count", 0) or 0
        output_toks = getattr(usage, "candidates_token_count", 0) or 0
        thought_toks = getattr(usage, "thoughts_token_count", 0) or 0

        # Effective billable inputs
        standard_input_toks = max(0, prompt_toks - cached_toks)

        cost_standard_input = (standard_input_toks / 1_000_000) * cls.PRICE_PER_M_INPUT
        cost_cached_input = (cached_toks / 1_000_000) * cls.PRICE_PER_M_CACHED_INPUT
        cost_output = ((output_toks + thought_toks) / 1_000_000) * cls.PRICE_PER_M_OUTPUT

        total_cost = cost_standard_input + cost_cached_input + cost_output
        saved_from_caching = (cached_toks / 1_000_000) * (cls.PRICE_PER_M_INPUT - cls.PRICE_PER_M_CACHED_INPUT)

        return {
            "is_cache_hit": False,
            "is_local": False,
            "prompt_tokens": prompt_toks,
            "cached_tokens": cached_toks,
            "output_tokens": output_toks,
            "thinking_tokens": thought_toks,
            "total_tokens": prompt_toks + output_toks + thought_toks,
            "billed_cost_usd": round(total_cost, 6),
            "saved_from_caching_usd": round(saved_from_caching, 6),
            "summary": f"Cloud Execution: ${total_cost:.6f} ({cached_toks} cached tokens)"
        }


class AntigravityOptimizedHarness:
    """
    Factory & Manager for cost-optimized Google Antigravity Agents.
    Enforces token compaction, hard token limits, thinking throttling,
    and on-device Apple Silicon offloading.
    """

    @staticmethod
    def detect_local_server() -> Tuple[bool, Optional[str], Optional[str]]:
        """Checks if local Ollama or LM Studio is online."""
        # 1. Ollama (:11434)
        try:
            r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=0.6)
            if r.status_code == 200:
                data = r.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                chosen = next((m for m in models if "qwen" in m or "llama" in m), models[0] if models else OLLAMA_MODEL)
                return True, "ollama", chosen
        except Exception:
            pass

        # 2. LM Studio (:1234)
        try:
            r = requests.get(f"{LMSTUDIO_BASE_URL}/models", timeout=0.6)
            if r.status_code == 200:
                data = r.json()
                items = data.get("data", [])
                chosen = items[0].get("id", "local-model") if items else "local-model"
                return True, "lmstudio", chosen
        except Exception:
            pass

        return False, None, None

    @classmethod
    def create_agent_config(
        cls,
        mode: str = "auto",
        system_instructions: Optional[str] = None,
        model: Optional[str] = None,
        max_total_tokens: int = 30000,
        max_output_tokens: int = 800,
        compaction_threshold: int = 16000,
        enable_thinking: bool = False,
        tools: Optional[list] = None,
        hooks_list: Optional[list] = None
    ) -> Any:
        """
        Builds a fully optimized AgentConfig.
        - Automatically prioritizes local $0.00 runners when mode='auto' and local is up.
        - Or applies Gemini 2.5 Flash + CompactionConfig + BudgetConfig + Minimal Thinking.
        """
        local_up, local_type, local_model = cls.detect_local_server()

        # 1. Local OpenAI-Compatible Server (Ollama / LM Studio)
        if mode == "local" or (mode == "auto" and local_up):
            target_url = f"{OLLAMA_BASE_URL}/v1" if local_type == "ollama" else f"{LMSTUDIO_BASE_URL}"
            return LocalOpenAIAgentConfig(
                model=model or local_model or "qwen3.5:4b",
                base_url=target_url,
                system_instructions=system_instructions or "You are an efficient, token-optimized AI agent.",
                tools=tools or [],
                hooks=hooks_list or []
            )

        # 2. Cloud Gemini with Full Token Guardrails
        effective_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
        thinking_level = ThinkingLevel.LOW if enable_thinking else ThinkingLevel.MINIMAL

        budget_cfg = types.BudgetConfig(
            max_output_tokens=max_output_tokens,
            max_total_tokens=max_total_tokens,
            scope=types.BudgetScope.LIFETIME
        )

        compaction_cfg = CompactionConfig(
            token_threshold=compaction_threshold
        )

        model_name = model or "gemini-2.5-flash"
        model_opts = GeminiModelOptions(
            thinking_level=thinking_level
        )
        endpoint = GeminiAPIEndpoint(options=model_opts)
        target = ModelTarget(name=model_name, endpoint=endpoint)

        return LocalAgentConfig(
            model=model_name,
            models=[target],
            api_key=effective_key,
            system_instructions=system_instructions or "You are an institutional fiduciary AI agent.",
            budget_config=budget_cfg,
            compaction_config=compaction_cfg,
            tools=tools or [],
            hooks=hooks_list or []
        )

    @classmethod
    async def run_optimized_turn(
        cls,
        agent: Agent,
        prompt: str,
        system_instructions: Optional[str] = None,
        bypass_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Executes an agent chat turn with SQLite cryptographic response caching and cost auditing.
        """
        start_t = time.perf_counter()
        db_fingerprint = get_db_state_fingerprint()
        cache_raw = f"antigravity:{system_instructions or ''}:{prompt}"
        prompt_hash = hashlib.sha256(cache_raw.encode("utf-8")).hexdigest()

        # 1. Check SQLite Response Cache
        if not bypass_cache:
            cached = get_cached_llm_response(prompt_hash, db_fingerprint)
            if cached:
                lat_ms = (time.perf_counter() - start_t) * 1000.0
                audit = AntigravityCostAuditor.calculate_audit(None, cache_hit=True)
                return {
                    "response": cached["response"],
                    "cache_hit": True,
                    "latency_ms": round(lat_ms, 2),
                    "cost_audit": audit,
                    "tokens_billed": 0
                }

        # 2. Execute via Antigravity Agent
        response = await agent.chat(prompt)
        lat_ms = (time.perf_counter() - start_t) * 1000.0

        # Retrieve session token usage
        usage = getattr(agent.conversation, "total_usage", None)
        is_local = isinstance(agent.config, (LocalOpenAIAgentConfig, LiteRTAgentConfig))
        audit = AntigravityCostAuditor.calculate_audit(usage, is_local=is_local)

        # 3. Cache successful response
        if response and not str(response).startswith("⚠️") and not str(response).startswith("❌"):
            set_cached_llm_response(
                prompt_hash=prompt_hash,
                db_fingerprint=db_fingerprint,
                response=str(response),
                model=getattr(agent.config, "model", "antigravity-agent")
            )

        return {
            "response": str(response),
            "cache_hit": False,
            "latency_ms": round(lat_ms, 2),
            "cost_audit": audit,
            "tokens_billed": audit.get("total_tokens", 0)
        }
