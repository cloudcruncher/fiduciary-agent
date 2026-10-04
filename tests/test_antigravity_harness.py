from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.antigravity import LocalAgentConfig, LocalOpenAIAgentConfig

from fiduciary.agent.antigravity_harness import (
    AntigravityCostAuditor,
    AntigravityOptimizedHarness,
)
from fiduciary.storage.db import clear_llm_cache, init_db


def test_antigravity_cost_auditor_cache_hit():
    audit = AntigravityCostAuditor.calculate_audit(None, cache_hit=True)
    assert audit["is_cache_hit"] is True
    assert audit["billed_cost_usd"] == 0.0
    assert audit["tokens_billed"] == 0
    assert "100% Token Savings" in audit["summary"]


def test_antigravity_cost_auditor_local():
    usage = MagicMock(total_token_count=1200)
    audit = AntigravityCostAuditor.calculate_audit(usage, is_local=True)
    assert audit["is_local"] is True
    assert audit["billed_cost_usd"] == 0.0
    assert audit["tokens_billed"] == 0
    assert "Zero-Cost Local Inference" in audit["summary"]


def test_antigravity_cost_auditor_cloud_with_caching():
    usage = MagicMock(
        prompt_token_count=40000,
        cached_content_token_count=35000,
        candidates_token_count=500,
        thoughts_token_count=0
    )
    audit = AntigravityCostAuditor.calculate_audit(usage, is_local=False)
    assert audit["is_cache_hit"] is False
    assert audit["cached_tokens"] == 35000
    assert audit["prompt_tokens"] == 40000
    assert audit["billed_cost_usd"] > 0
    assert audit["saved_from_caching_usd"] > 0


def test_create_agent_config_local():
    with patch.object(AntigravityOptimizedHarness, "detect_local_server", return_value=(True, "ollama", "qwen3.5:4b")):
        config = AntigravityOptimizedHarness.create_agent_config(mode="local")
        assert isinstance(config, LocalOpenAIAgentConfig)
        assert config.model == "qwen3.5:4b"


def test_create_agent_config_cloud_guardrails():
    with patch.object(AntigravityOptimizedHarness, "detect_local_server", return_value=(False, None, None)):
        config = AntigravityOptimizedHarness.create_agent_config(
            mode="gemini",
            max_total_tokens=20000,
            max_output_tokens=600,
            compaction_threshold=12000
        )
        assert isinstance(config, LocalAgentConfig)
        assert config.model == "gemini-2.5-flash"
        assert config.budget_config.max_output_tokens == 600
        assert config.budget_config.max_total_tokens == 20000
        assert config.compaction_config.token_threshold == 12000


@pytest.mark.anyio
async def test_run_optimized_turn_caching():
    init_db()
    clear_llm_cache()

    mock_agent = MagicMock()
    mock_agent.chat = AsyncMock(return_value="Action plan: 1. Maximize ISA allowance. 2. Cut subscription drag.")
    mock_agent.config = LocalAgentConfig(model="gemini-2.5-flash", api_key="fake-key")
    mock_usage = MagicMock(
        prompt_token_count=1500,
        cached_content_token_count=0,
        candidates_token_count=50,
        thoughts_token_count=0,
        total_token_count=1550
    )
    mock_agent.conversation = MagicMock(total_usage=mock_usage)

    prompt = "What should I do with my surplus cash?"

    # 1. First run: cache miss -> calls agent.chat
    res1 = await AntigravityOptimizedHarness.run_optimized_turn(mock_agent, prompt)
    assert res1["cache_hit"] is False
    assert "Maximize ISA allowance" in res1["response"]
    assert mock_agent.chat.call_count == 1

    # 2. Second run: exact prompt on same DB state -> cache HIT -> 0 calls to agent.chat
    res2 = await AntigravityOptimizedHarness.run_optimized_turn(mock_agent, prompt)
    assert res2["cache_hit"] is True
    assert "Maximize ISA allowance" in res2["response"]
    assert res2["tokens_billed"] == 0
    assert mock_agent.chat.call_count == 1  # Did NOT call agent.chat again!
