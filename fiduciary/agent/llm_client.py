import os
from typing import Any, Dict, Optional, Tuple

import requests

from fiduciary.config import (
    AI_GATEWAY_API_KEY,
    AI_GATEWAY_MODEL,
    AI_GATEWAY_URL,
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


def ensure_gateway_running(gateway_url: Optional[str] = None) -> bool:
    """
    If the gateway is targeted to local port 4000 (e.g. 127.0.0.1:4000 / localhost:4000)
    and is not currently responding, automatically spawn the LiteLLM proxy in the background.
    """
    import shutil
    import subprocess
    import time

    from fiduciary.config import BASE_DIR

    target_url = (gateway_url or os.getenv("AI_GATEWAY_URL") or "http://localhost:4000/v1").rstrip("/")
    if "localhost:4000" not in target_url and "127.0.0.1:4000" not in target_url:
        return False

    api_key = os.getenv("AI_GATEWAY_API_KEY", "")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    def _is_alive() -> bool:
        try:
            resp = requests.get(f"{target_url}/models", timeout=0.8, headers=headers)
            if resp.status_code in (200, 401):
                return True
        except Exception:
            pass
        try:
            root_url = target_url.replace("/v1", "")
            if requests.get(f"{root_url}/health/liveliness", timeout=0.8).status_code == 200:
                return True
        except Exception:
            pass
        return False

    if _is_alive():
        return True

    litellm_bin = shutil.which("litellm")
    if not litellm_bin:
        venv_bin = BASE_DIR / ".venv" / "bin" / "litellm"
        if venv_bin.exists():
            litellm_bin = str(venv_bin)

    if not litellm_bin:
        return False

    config_path = BASE_DIR / "litellm_config.yaml"
    cmd = [
        litellm_bin,
        "--config", str(config_path),
        "--port", "4000",
        "--host", "127.0.0.1"
    ]
    try:
        subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        for _ in range(20):
            time.sleep(0.35)
            if _is_alive():
                return True
    except Exception:
        return False

    return False


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
        gemini_key: Optional[str] = None,
        gateway_url: Optional[str] = None,
        gateway_api_key: Optional[str] = None,
        gateway_model: Optional[str] = None,
    ):
        self.provider = provider if provider is not None else (_RUNTIME_PROVIDER or os.getenv("LLM_PROVIDER", LLM_PROVIDER))
        self.lmstudio_url = lmstudio_url if lmstudio_url is not None else os.getenv("LMSTUDIO_BASE_URL", LMSTUDIO_BASE_URL)
        self.ollama_url = ollama_url if ollama_url is not None else os.getenv("OLLAMA_BASE_URL", OLLAMA_BASE_URL)
        self.gemini_key = gemini_key if gemini_key is not None else (os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY)
        self.gateway_url = (
            gateway_url
            if gateway_url is not None
            else (os.getenv("AI_GATEWAY_URL") or os.getenv("OPENAI_BASE_URL") or AI_GATEWAY_URL)
        ).rstrip("/")
        self.gateway_api_key = (
            gateway_api_key
            if gateway_api_key is not None
            else (os.getenv("AI_GATEWAY_API_KEY") or os.getenv("OPENAI_API_KEY") or AI_GATEWAY_API_KEY)
        )
        self.gateway_model = (
            gateway_model
            if gateway_model is not None
            else (os.getenv("AI_GATEWAY_MODEL") or AI_GATEWAY_MODEL)
        )

    def _get_gateway_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.gateway_api_key:
            headers["Authorization"] = f"Bearer {self.gateway_api_key}"
        return headers

    def is_gateway_server_running(self, auto_start: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Probes configured AI Gateway (LiteLLM Proxy, Portkey, Cloudflare AI Gateway, etc.).
        Returns (is_running, model_name).
        """
        if not self.gateway_url:
            return False, None
        try:
            resp = requests.get(f"{self.gateway_url}/models", timeout=0.8, headers=self._get_gateway_headers())
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", [])
                if items:
                    chosen = items[0].get("id", self.gateway_model)
                    return True, chosen
                return True, self.gateway_model
        except Exception:
            pass

        if auto_start and self.provider == "gateway" and ("localhost:4000" in self.gateway_url or "127.0.0.1:4000" in self.gateway_url):
            if ensure_gateway_running(self.gateway_url):
                return self.is_gateway_server_running(auto_start=False)

        return False, None

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
        gateway_up, gateway_model = self.is_gateway_server_running()
        active_mode = "none"

        if self.provider == "gateway":
            if gateway_up:
                active_mode = "gateway"
            elif local_up:
                # Gateway configured but offline: automatically fall back to local Ollama / LM Studio
                active_mode = "local"
            elif self.gemini_key:
                active_mode = "gemini"
            else:
                active_mode = "gateway" if self.gateway_url else "none"
        elif self.provider == "local":
            active_mode = "local" if local_up else "none"
        elif self.provider == "gemini":
            active_mode = "gemini" if self.gemini_key else "none"
        else:  # "auto"
            # In auto mode, prioritize local-first on-device privacy, then AI gateway, then cloud
            if local_up:
                active_mode = "local"
            elif self.gateway_url and gateway_up:
                active_mode = "gateway"
            elif self.gemini_key:
                active_mode = "gemini"

        badge_text = "⚠️ No LLM Active"
        if active_mode == "gateway":
            badge_text = f"🔵 AI Gateway ({gateway_model or self.gateway_model or 'qwen3.5:4b'} • 100% Private Local)"
        elif active_mode == "local":
            if self.provider == "gateway" and not gateway_up:
                badge_text = "🟢 AI Gateway (Gateway Failover • 100% Private)"
            elif local_provider == "ollama":
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
            "gateway_server_online": gateway_up,
            "gateway_url": self.gateway_url,
            "gateway_model": gateway_model or self.gateway_model,
            "gemini_configured": bool(self.gemini_key),
            "is_100_percent_private": active_mode in ("local", "gateway"),
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
        tools_used: Optional[list] = None,
        bypass_cache: bool = False
    ) -> str:
        """Generates completion using the optimal local or cloud model with zero-token response caching."""
        import hashlib
        import time

        from fiduciary.observability.tracer import record_llm_trace
        from fiduciary.storage.db import (
            get_cached_llm_response,
            get_db_state_fingerprint,
            set_cached_llm_response,
        )

        start_t = time.perf_counter()
        status = self.get_status()
        mode = status["mode"]
        used_provider = mode
        used_model = status.get("local_model") or status.get("gateway_model") or self.gateway_model or "unknown"
        response_text = ""

        # Response Caching Check:
        # If model is active and cache is not bypassed, check for exact match on current DB state
        db_fingerprint = get_db_state_fingerprint()
        cache_raw = f"{mode}:{used_model}:{system_prompt or ''}:{prompt}"
        prompt_hash = hashlib.sha256(cache_raw.encode("utf-8")).hexdigest()

        if not bypass_cache and mode in ("local", "gemini", "gateway"):
            cached_entry = get_cached_llm_response(prompt_hash, db_fingerprint)
            if cached_entry:
                cached_resp = cached_entry["response"]
                cached_model = f"{cached_entry['model']} (cached)"
                latency_ms = (time.perf_counter() - start_t) * 1000.0
                cache_tool = {
                    "tool_name": "llm_response_cache",
                    "type": "cache_hit",
                    "source": "SQLite llm_response_cache (0 tokens billed)",
                    "latency_ms": round(latency_ms, 2),
                    "status": "CACHE_HIT",
                    "summary": "Instant cache hit: zero credit/token consumption."
                }
                record_llm_trace(
                    caller=caller,
                    provider=used_provider,
                    model=cached_model,
                    latency_ms=latency_ms,
                    user_prompt=prompt,
                    system_prompt=system_prompt,
                    response=cached_resp,
                    tools_used=(tools_used or []) + [cache_tool]
                )
                return cached_resp

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
            elif self.provider in ("local", "gateway"):
                # Strict 100% local privacy: NEVER fall back to Gemini cloud!
                prov_name = (status.get("local_provider") or "local").upper()
                response_text = (
                    f"⚠️ **{prov_name} Local Generation Error**\n\n"
                    f"The local server is online on `{used_model}`, but failed to respond to the completion request.\n"
                    f"Please check if memory pressure is high or restart the local model service."
                )
            elif self.gemini_key:
                used_provider = "gemini"
                used_model = "gemini-2.5-flash"
                response_text = self._generate_gemini(prompt, system_prompt, temperature)
            else:
                prov_name = (status.get("local_provider") or "local").upper()
                response_text = (
                    f"⚠️ **{prov_name} Local Generation Error**\n\n"
                    f"The local server failed to respond to the completion request on `{used_model}`."
                )
        elif mode == "gateway":
            used_provider = "gateway"
            used_model = status.get("gateway_model") or self.gateway_model or "gateway-model"
            gateway_ans = self._generate_gateway(
                prompt=prompt,
                system_prompt=system_prompt,
                model_name=used_model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout
            )
            if gateway_ans:
                response_text = gateway_ans
            else:
                # Gateway failed or returned None: automatically fall back to local Ollama / LM Studio
                local_up, local_prov, local_m = self.is_local_server_running()
                if local_up:
                    local_ans = self._generate_local(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        provider=local_prov or "ollama",
                        model_name=local_m,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=timeout
                    )
                    if local_ans:
                        response_text = local_ans
                        used_provider = f"gateway-fallback->{local_prov}"
                        used_model = local_m or used_model
                if not response_text:
                    response_text = (
                        f"⚠️ **AI Gateway Error**\n\n"
                        f"The configured AI Gateway at `{self.gateway_url}` failed to respond on model `{used_model}`.\n\n"
                        f"💡 *Tip*: Run `./f gateway` to start the LiteLLM proxy, or start Ollama (`ollama serve`) for native local inference."
                    )
        elif mode == "gemini":
            used_provider = "gemini"
            used_model = "gemini-2.5-flash"
            response_text = self._generate_gemini(prompt, system_prompt, temperature)
        else:
            response_text = (
                "⚠️ **No AI Model Configured**\n\n"
                "To run with **100% Local Privacy** on your Mac (zero confidential financial data sent outside):\n"
                "1. **Option A (Ollama - Fast & Native)**: Start Ollama (`ollama serve`) with `qwen3.5:4b`.\n"
                "2. **Option B (LM Studio)**: Open LM Studio and start the local server on port 1234.\n"
                "3. **Option C (AI Gateway)**: Set `AI_GATEWAY_URL` in `.env` to route through LiteLLM or an enterprise proxy.\n\n"
                "Local options run entirely offline on Apple Silicon Metal GPU."
            )

        latency_ms = (time.perf_counter() - start_t) * 1000.0

        # Cache successful response bound to current financial state
        if response_text and not response_text.startswith("⚠️") and not response_text.startswith("❌"):
            set_cached_llm_response(
                prompt_hash=prompt_hash,
                db_fingerprint=db_fingerprint,
                response=response_text,
                model=used_model
            )

        # Record observability trace with grounding audit and tools used
        if mode in ("local", "gemini", "gateway"):
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

    def _generate_gateway(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model_name: str,
        temperature: float = 0.2,
        max_tokens: int = 500,
        timeout: int = 60
    ) -> Optional[str]:
        """Calls OpenAI-compatible /chat/completions endpoint on the AI Gateway."""
        if not self.gateway_url:
            return None
        endpoint = f"{self.gateway_url}/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "extra_body": {"think": False}
        }

        try:
            resp = requests.post(endpoint, json=payload, headers=self._get_gateway_headers(), timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    content = msg.get("content", "").strip()
                    if not content and "reasoning_content" in msg:
                        content = msg.get("reasoning_content", "").strip()
                    return content if content else None
        except Exception:
            return None
        return None

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

        models_to_try = [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-1.5-flash",
            "gemini-3.8-flash",
        ]
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
