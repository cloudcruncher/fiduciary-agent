from unittest.mock import MagicMock, patch

from fiduciary.agent.llm_client import LLMClient


def test_llm_client_status_local_detection():
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": [{"id": "meta-llama-3.1-8b"}]
        }
        client = LLMClient(provider="auto", gemini_key="fake-key")
        status = client.get_status()
        assert status["mode"] == "local"
        assert status["is_100_percent_private"] is True
        assert status["local_server_online"] is True
        assert "Local LM Studio" in status["privacy_badge"]

def test_llm_client_status_gemini_fallback():
    with patch("requests.get") as mock_get:
        mock_get.side_effect = Exception("Connection refused")
        client = LLMClient(provider="auto", gemini_key="valid-gemini-key")
        status = client.get_status()
        assert status["mode"] == "gemini"
        assert status["is_100_percent_private"] is False
        assert "Gemini Cloud API" in status["privacy_badge"]

def test_llm_client_status_none():
    with patch("requests.get") as mock_get:
        mock_get.side_effect = Exception("Connection refused")
        client = LLMClient(provider="auto", gemini_key="")
        status = client.get_status()
        assert status["mode"] == "none"
        assert status["local_server_online"] is False
        assert "No LLM Active" in status["privacy_badge"]

def test_llm_generate_local_mocked():
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": [{"id": "local-model"}]
        }
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "Fiduciary advice delivered locally."}}]
        }
        client = LLMClient(provider="local")
        ans = client.generate("What is my burn rate?")
        assert "Fiduciary advice delivered locally." in ans

def test_llm_client_ollama_detection():
    def mock_get(url, timeout=0.8):
        m = MagicMock()
        if "1234" in url:
            raise Exception("LM Studio offline")
        elif "11434" in url:
            m.status_code = 200
            m.json.return_value = {"models": [{"name": "qwen3.5:4b"}]}
            return m
        raise Exception("Unknown url")

    with patch("requests.get", side_effect=mock_get):
        client = LLMClient(provider="auto", gemini_key="")
        status = client.get_status()
        assert status["mode"] == "local"
        assert status["local_provider"] == "ollama"
        assert status["local_model"] == "qwen3.5:4b"
        assert "Local Ollama" in status["privacy_badge"]

def test_llm_generate_ollama_fast_chat():
    def mock_get(url, timeout=0.8):
        m = MagicMock()
        if "1234" in url:
            raise Exception("LM Studio offline")
        elif "11434" in url:
            m.status_code = 200
            m.json.return_value = {"models": [{"name": "qwen3.5:4b"}]}
            return m
        raise Exception("Unknown url")

    with patch("requests.get", side_effect=mock_get), patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "message": {"content": "Fast Ollama local response in 250ms."}
        }
        client = LLMClient(provider="local")
        ans = client.generate("What is my liquid runway?")
        assert "Fast Ollama local response in 250ms." in ans
        # Verify think: False and keep_alive: 0 were passed
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["think"] is False
        assert payload["keep_alive"] == 0

def test_llm_strict_privacy_no_cloud_fallback():
    # If provider is "local", failed local call must NEVER send client data to Gemini
    def mock_get(url, timeout=0.8):
        m = MagicMock()
        m.status_code = 200
        m.json.return_value = {"data": [{"id": "local-model"}]}
        return m

    with patch("requests.get", side_effect=mock_get), patch("requests.post") as mock_post, patch.object(LLMClient, "_generate_gemini") as mock_gemini:
        mock_post.side_effect = Exception("Local server timeout")
        client = LLMClient(provider="local", gemini_key="real-gemini-key")
        ans = client.generate("Classified financial balance £50,000")
        assert "Local Generation Error" in ans
        mock_gemini.assert_not_called()


def test_llm_client_gateway_detection():
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": [{"id": "litellm-routed-model"}]
        }
        client = LLMClient(
            provider="gateway",
            gateway_url="http://localhost:4000/v1",
            gateway_api_key="sk-test-proxy",
            gateway_model="litellm-routed-model"
        )
        status = client.get_status()
        assert status["mode"] == "gateway"
        assert status["gateway_server_online"] is True
        assert status["gateway_model"] == "litellm-routed-model"
        assert "AI Gateway" in status["privacy_badge"]


def test_llm_generate_gateway_mocked():
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": [{"id": "litellm-router-qwen"}]
        }
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "Response routed via LiteLLM Enterprise Gateway."}}]
        }
        client = LLMClient(
            provider="gateway",
            gateway_url="http://localhost:4000/v1",
            gateway_api_key="sk-litellm-secret-key"
        )
        ans = client.generate("What is my uncommitted monthly income?")
        assert "Response routed via LiteLLM Enterprise Gateway." in ans

        # Verify endpoint and Authorization Bearer header
        assert mock_post.called
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:4000/v1/chat/completions"
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer sk-litellm-secret-key"
        payload = call_args[1]["json"]
        assert payload["messages"][-1]["content"] == "What is my uncommitted monthly income?"


def test_llm_response_caching_zero_token_savings():
    from fiduciary.storage.db import clear_llm_cache, init_db

    init_db()
    clear_llm_cache()

    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"data": [{"id": "cached-test-model"}]}
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "Your emergency buffer is £4,500.00."}}]
        }

        client = LLMClient(provider="local")
        prompt = "What is my emergency buffer?"

        # 1. First invocation: Cache miss -> calls requests.post
        ans1 = client.generate(prompt)
        assert ans1 == "Your emergency buffer is £4,500.00."
        assert mock_post.call_count == 1

        # 2. Second invocation: Exact match on same DB state -> Cache HIT -> NO requests.post call!
        ans2 = client.generate(prompt)
        assert ans2 == "Your emergency buffer is £4,500.00."
        assert mock_post.call_count == 1  # call count stayed at 1!

        # 3. Third invocation with bypass_cache=True -> ignores cache -> calls requests.post
        ans3 = client.generate(prompt, bypass_cache=True)
        assert ans3 == "Your emergency buffer is £4,500.00."
        assert mock_post.call_count == 2


def test_llm_gateway_offline_falls_back_to_local_ollama():
    def mock_get(url, timeout=0.8, headers=None):
        m = MagicMock()
        if "4000" in url:
            raise Exception("Gateway connection refused")
        elif "11434" in url:
            m.status_code = 200
            m.json.return_value = {"models": [{"name": "qwen3.5:4b"}]}
            return m
        raise Exception("Offline")

    with patch("requests.get", side_effect=mock_get), patch("fiduciary.agent.llm_client.ensure_gateway_running", return_value=False):
        client = LLMClient(
            provider="gateway",
            gateway_url="http://localhost:4000/v1"
        )
        status = client.get_status()
        assert status["mode"] == "local"
        assert status["gateway_server_online"] is False
        assert status["local_server_online"] is True
        assert "Gateway Failover" in status["privacy_badge"]


def test_llm_gateway_failure_falls_back_to_local_generation():
    with patch.object(LLMClient, "get_status", return_value={"mode": "gateway", "gateway_model": "qwen3.5:4b"}):
        with patch.object(LLMClient, "_generate_gateway", return_value=None):
            with patch.object(LLMClient, "is_local_server_running", return_value=(True, "ollama", "qwen3.5:4b")):
                with patch.object(LLMClient, "_generate_local", return_value="Local fallback advice delivered."):
                    client = LLMClient(provider="gateway")
                    ans = client.generate("What is my cash runway?", bypass_cache=True)
                    assert ans == "Local fallback advice delivered."


