import os
from typing import Any, Dict, Optional, Tuple

import requests

from fiduciary.config import (
    GEMINI_API_KEY,
    LLM_PROVIDER,
    LMSTUDIO_BASE_URL,
    LMSTUDIO_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)

_RUNTIME_PROVIDER: Optional[str] = None

def set_runtime_provider(provider: str) -> None:
    global _RUNTIME_PROVIDER
    _RUNTIME_PROVIDER = provider

def get_runtime_provider() -> Optional[str]:
    return _RUNTIME_PROVIDER

class LLMClient:
    """
    Unified LLM Client supporting both 100% Local Offline Privacy (LM Studio / Ollama)
    and Cloud Gemini.
    Prioritizes local models on Apple Silicon so confidential financial data never leaves your laptop.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        lmstudio_url: Optional[str] = None,
        ollama_url: Optional[str] = None,
        gemini_key: Optional[str] = None
    ):
        self.provider = provider if provider is not None else (_RUNTIME_PROVIDER or os.getenv("LLM_PROVIDER", LLM_PROVIDER))
        self.lmstudio_url = lmstudio_url if lmstudio_url is not None else os.getenv("LMSTUDIO_BASE_URL", LMSTUDIO_BASE_URL)
        self.ollama_url = ollama_url if ollama_url is not None else os.getenv("OLLAMA_BASE_URL", OLLAMA_BASE_URL)
        self.gemini_key = gemini_key if gemini_key is not None else (os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY)

    def is_local_server_running(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Probes local model runners on Apple Silicon:
        1. LM Studio (:1234/v1/models)
        2. Ollama (:11434/api/tags)
        Returns (is_running, provider, model_name).
        """
        # 1. Probe Ollama (:11434) - Primary default local engine
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=0.8)
            if resp.status_code == 200:
                data = resp.json()
                if "models" in data:
                    models = [m.get("name", "") for m in data.get("models", [])]
                    if models:
                        chosen = next((m for m in models if "qwen" in m or "llama" in m), models[0])
                        return True, "ollama", chosen
                    return True, "ollama", OLLAMA_MODEL
        except Exception:
            pass

        # 2. Probe LM Studio (:1234) - Alternative local runner
        try:
            resp = requests.get(f"{self.lmstudio_url}/models", timeout=0.8)
            if resp.status_code == 200:
                data = resp.json()
                if "data" in data:
                    data_items = data.get("data", [])
                    if data_items:
                        return True, "lmstudio", data_items[0].get("id", LMSTUDIO_MODEL)
                    return True, "lmstudio", LMSTUDIO_MODEL
        except Exception:
            pass

        return False, None, None

    def get_status(self) -> Dict[str, Any]:
        """Returns the active provider and its privacy/offline status."""
        local_up, local_provider, local_model = self.is_local_server_running()
        active_mode = "none"

        if self.provider == "local":
            active_mode = "local" if local_up else "none"
        elif self.provider == "gemini":
            active_mode = "gemini" if self.gemini_key else "none"
        else:  # "auto"
            if local_up:
                active_mode = "local"
            elif self.gemini_key:
                active_mode = "gemini"

        badge_text = "⚠️ No LLM Active"
        if active_mode == "local":
            if local_provider == "ollama":
                badge_text = "🟢 Local Ollama (100% Private - On Device)"
            else:
                badge_text = "🟢 Local LM Studio (100% Private - On Device)"
        elif active_mode == "gemini":
            badge_text = "🟣 Gemini Cloud API"

        return {
            "mode": active_mode,
            "configured_provider": self.provider,
            "local_server_online": local_up,
            "local_provider": local_provider,
            "local_model": local_model,
            "gemini_configured": bool(self.gemini_key),
            "is_100_percent_private": active_mode == "local",
            "privacy_badge": badge_text
        }

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 500,
        timeout: int = 60,
        caller: str = "copilot",
        tools_used: Optional[list] = None
    ) -> str:
        """Generates completion using the optimal local or cloud model and records observability trace."""
        import time

        from fiduciary.observability.tracer import record_llm_trace

        start_t = time.perf_counter()
        status = self.get_status()
        mode = status["mode"]
        used_provider = mode
        used_model = status.get("local_model") or "unknown"
        response_text = ""

        if mode == "local":
            local_ans = self._generate_local(
                prompt=prompt,
                system_prompt=system_prompt,
                provider=status.get("local_provider") or "lmstudio",
                model_name=status.get("local_model"),
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout
            )
            if local_ans:
                response_text = local_ans
            elif self.provider == "local":
                # Strict 100% local privacy: NEVER fall back to Gemini cloud!
                prov_name = (status.get("local_provider") or "local").upper()
                response_text = (
                    f"⚠️ **{prov_name} Local Generation Error**\n\n"
                    f"The local server is online on `{used_model}`, but failed to respond to the completion request.\n"
                    f"Please check if memory pressure is high or restart the local model service."
                )
            elif self.gemini_key:
                used_provider = "gemini"
                used_model = "gemini-3.8-flash"
                response_text = self._generate_gemini(prompt, system_prompt, temperature)
            else:
                prov_name = (status.get("local_provider") or "local").upper()
                response_text = (
                    f"⚠️ **{prov_name} Local Generation Error**\n\n"
                    f"The local server failed to respond to the completion request on `{used_model}`."
                )
        elif mode == "gemini":
            used_provider = "gemini"
            used_model = "gemini-3.8-flash"
            response_text = self._generate_gemini(prompt, system_prompt, temperature)
        else:
            response_text = (
                "⚠️ **No AI Model Configured**\n\n"
                "To run with **100% Local Privacy** on your Mac (zero confidential financial data sent outside):\n"
                "1. **Option A (Ollama - Fast & Native)**: Start Ollama (`ollama serve`) with `qwen3.5:4b`.\n"
                "2. **Option B (LM Studio)**: Open LM Studio and start the local server on port 1234.\n\n"
                "Both options run entirely offline on Apple Silicon Metal GPU."
            )

        latency_ms = (time.perf_counter() - start_t) * 1000.0

        # Record observability trace with grounding audit and tools used
        if mode in ("local", "gemini"):
            record_llm_trace(
                caller=caller,
                provider=used_provider,
                model=used_model,
                latency_ms=latency_ms,
                user_prompt=prompt,
                system_prompt=system_prompt,
                response=response_text,
                tools_used=tools_used
            )

        return response_text

    def _generate_local(
        self,
        prompt: str,
        system_prompt: Optional[str],
        provider: str,
        model_name: Optional[str],
        temperature: float,
        max_tokens: int,
        timeout: int = 60
    ) -> Optional[str]:
        """Calls either Ollama native API or LM Studio OpenAI-compatible endpoint."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # 1. Ollama Native Endpoint
        if provider == "ollama":
            payload = {
                "model": model_name or OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                # Disable chain-of-thought thinking loops (crucial for Qwen 3.5 sub-second response)
                "think": False,
                # Free 16GB Mac unified memory immediately after generating response
                "keep_alive": 0,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            try:
                resp = requests.post(
                    f"{self.ollama_url}/api/chat",
                    json=payload,
                    timeout=timeout
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("message", {}).get("content", "").strip()
            except Exception:
                return None
            return None

        # 2. LM Studio OpenAI-compatible Endpoint
        payload = {
            "model": model_name or LMSTUDIO_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            resp = requests.post(
                f"{self.lmstudio_url}/chat/completions",
                json=payload,
                timeout=timeout
            )
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
        except Exception:
            return None
        return None

    def _generate_gemini(self, prompt: str, system_prompt: Optional[str], temperature: float) -> str:
        """Calls Gemini API."""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.gemini_key)
        full_content = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        models_to_try = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]
        last_err = None

        for model_name in models_to_try:
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=full_content,
                    config=types.GenerateContentConfig(temperature=temperature)
                )
                if resp.text:
                    return resp.text
            except Exception as e:
                last_err = e
                continue
        return f"❌ Error contacting Gemini: {last_err}"
