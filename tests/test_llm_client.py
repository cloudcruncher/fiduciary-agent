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

