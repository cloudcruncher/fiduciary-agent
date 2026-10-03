import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(BASE_DIR / ".env")

# Enable Banking credentials
ENABLE_BANKING_APP_ID = os.getenv("ENABLE_BANKING_APP_ID", "")
ENABLE_BANKING_KEY_PATH = os.getenv("ENABLE_BANKING_KEY_PATH", str(BASE_DIR / "secrets" / "private_key.pem"))
REDIRECT_URL = os.getenv("REDIRECT_URL", "http://localhost:8080/callback")

# Wise direct token
WISE_API_TOKEN = os.getenv("WISE_API_TOKEN", "")

# Gemini API Key (for Live Search & Autonomous AI Advisor)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")

# LLM Provider Configuration:
# "local" (strictly 100% offline via Ollama / LM Studio on Apple Silicon - Default)
# "gateway" (enterprise AI Gateway / LiteLLM Proxy / Portkey via OpenAI-compatible endpoint)
# "auto" (prioritizes local Ollama/LM Studio or AI Gateway if running, else Gemini)
# "gemini" (cloud API - dormant/opt-in only)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local").lower()
LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "local-llama")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")

# Enterprise AI Gateway / LiteLLM Proxy / Portkey:
# e.g., "http://localhost:4000/v1" or "https://gateway.ai.cloudflare.com/v1/..."
AI_GATEWAY_URL = os.getenv("AI_GATEWAY_URL", os.getenv("OPENAI_BASE_URL", "")).rstrip("/")
AI_GATEWAY_API_KEY = os.getenv("AI_GATEWAY_API_KEY", os.getenv("OPENAI_API_KEY", ""))
AI_GATEWAY_MODEL = os.getenv("AI_GATEWAY_MODEL", "qwen3.5:4b")

# TrueLayer Open Banking Credentials (from https://console.truelayer.com)
TRUELAYER_CLIENT_ID = os.getenv("TRUELAYER_CLIENT_ID", "")
TRUELAYER_CLIENT_SECRET = os.getenv("TRUELAYER_CLIENT_SECRET", "")
TRUELAYER_USE_SANDBOX = os.getenv("TRUELAYER_USE_SANDBOX", "false").lower() == "true"

# Server configuration
PORT = int(os.getenv("PORT", "8080"))

# Database path
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = Path(os.getenv("FIDUCIARY_DB_PATH", str(DATA_DIR / "financial.db")))


# Supported target institutions in UK
SUPPORTED_BANKS = {
    "chase": {"name": "Chase", "country": "GB", "displayName": "Chase UK"},
    "hsbc": {"name": "HSBC", "country": "GB", "displayName": "HSBC UK"},
    "natwest": {"name": "NatWest", "country": "GB", "displayName": "NatWest"},
    "lloyds": {"name": "Lloyds Bank", "country": "GB", "displayName": "Lloyds Bank"},
    "revolut": {"name": "Revolut", "country": "GB", "displayName": "Revolut UK"},
    "zopa": {"name": "Zopa", "country": "GB", "displayName": "Zopa Bank"},
    "wise": {"name": "Wise", "country": "GB", "displayName": "Wise"},
}
