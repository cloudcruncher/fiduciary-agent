"""
Multi-Step ReAct (Reasoning + Acting) Agent Engine for Fiduciary AI.
Orchestrates autonomous multi-tool reasoning trajectories:
  Thought -> Action -> Action Input -> Observation -> Thought ... -> Final Answer
Emits comprehensive step-by-step telemetry and integrates reversible PII anonymization.
"""

import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from fiduciary.agent.llm_client import LLMClient
from fiduciary.agent.mcp_gateway import MCPGateway
from fiduciary.agent.pii_anonymizer import PIIAnonymizer
from fiduciary.agent.prompt_guard import PromptGuard
from fiduciary.observability.tracer import record_llm_trace


class ReActFiduciaryAgent:
    """
    Autonomous multi-step ReAct agent.
    Iteratively plans, executes tools from MCPGateway, observes outputs,
    and synthesizes rigorous fiduciary answers with step-by-step trace observability.
    """

    MAX_STEPS = 4

    def __init__(self, llm: Optional[LLMClient] = None, enable_pii_anonymization: bool = True):
        self.llm = llm or LLMClient()
        self.enable_pii_anonymization = enable_pii_anonymization

    def _build_tools_prompt(self) -> str:
        """Formats available MCP tools into the ReAct system prompt."""
        tools = MCPGateway.list_tools()
        lines = []
        for t in tools:
            lines.append(f"- **{t['name']}**: {t['description']}")
            props = t.get("parameters", {}).get("properties", {})
            if props:
                prop_str = ", ".join(f"{k} ({v.get('type')})" for k, v in props.items())
                lines.append(f"  Arguments: {prop_str}")
        return "\n".join(lines)

    def run(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes the autonomous ReAct loop for a user query.
        Returns:
            Dict containing:
                - "answer": str
                - "steps": List of step traces (thought, action, input, observation, duration_ms)
                - "total_duration_ms": float
                - "tools_used": List[str]
        """
        start_total = time.perf_counter()

        # 1. Prompt Injection Defense
        guard_result = PromptGuard.inspect(query)
        if not guard_result.is_safe:
            return {
                "answer": guard_result.guard_response or "⚠️ Request blocked by Fiduciary Prompt Guard.",
                "steps": [],
                "total_duration_ms": 0.0,
                "tools_used": []
            }
        clean_query = guard_result.sanitized_query

        # 2. Reversible PII Anonymization
        deanonymize_map: Dict[str, str] = {}
        processed_query = clean_query
        if self.enable_pii_anonymization:
            processed_query, deanonymize_map = PIIAnonymizer.anonymize(clean_query)

        tools_desc = self._build_tools_prompt()

        system_prompt = (
            "You are an expert UK Personal Fiduciary AI Agent operating with strict autonomous ReAct reasoning.\n"
            "You help clients manage money, audit taxes, reduce burn, and plan investments.\n"
            "You have access to the following tools via MCP:\n"
            f"{tools_desc}\n\n"
            "To use a tool, use the exact format:\n"
            "Thought: <reasoning about what information you need>\n"
            "Action: <tool_name>\n"
            "Action Input: <JSON object containing arguments>\n\n"
            "When you have collected all required information to answer the client, use the exact format:\n"
            "Thought: I now have sufficient verified information.\n"
            "Final Answer: <your complete, authoritative fiduciary answer in GitHub markdown>\n"
        )

        history_trajectory = f"Question: {processed_query}\n"
        if context:
            history_trajectory += f"Baseline Ground Truth Context:\n{context}\n\n"

        steps_trace: List[Dict[str, Any]] = []
        tools_executed: List[str] = []
        final_answer: Optional[str] = None

        for step_idx in range(self.MAX_STEPS):
            step_start = time.perf_counter()

            # Generate thought + next action from LLM
            response = self.llm.generate(
                prompt=history_trajectory + "\nThought:",
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=600,
                caller="react_agent"
            )

            response_full = "Thought: " + response.strip()

            # Check if model arrived at Final Answer
            if "Final Answer:" in response_full:
                parts = response_full.split("Final Answer:", 1)
                final_answer = parts[1].strip()
                thought_text = parts[0].replace("Thought:", "").strip()
                steps_trace.append({
                    "step": step_idx + 1,
                    "thought": thought_text,
                    "action": "Final Answer",
                    "action_input": {},
                    "observation": "Answer ready",
                    "duration_ms": round((time.perf_counter() - step_start) * 1000, 2)
                })
                break

            # Parse Action and Action Input
            thought, action, action_input = self._parse_react_response(response_full)

            if not action or action not in MCPGateway.TOOLS_REGISTRY:
                # If model failed to call a valid tool or finished reasoning, synthesize final answer
                final_answer = response.strip()
                steps_trace.append({
                    "step": step_idx + 1,
                    "thought": thought or "Synthesizing answer from context",
                    "action": "Synthesize",
                    "action_input": {},
                    "observation": "Direct completion",
                    "duration_ms": round((time.perf_counter() - step_start) * 1000, 2)
                })
                break

            # Execute tool via MCPGateway
            tool_start = time.perf_counter()
            tool_res = MCPGateway.call_tool(action, action_input)
            tool_duration = round((time.perf_counter() - tool_start) * 1000, 2)
            tools_executed.append(action)

            # Observation format for trajectory
            obs_str = json.dumps(tool_res.get("result", {}), default=str)
            if len(obs_str) > 1200:
                obs_str = obs_str[:1200] + "... [truncated]"

            steps_trace.append({
                "step": step_idx + 1,
                "thought": thought,
                "action": action,
                "action_input": action_input,
                "observation": obs_str,
                "tool_duration_ms": tool_duration,
                "duration_ms": round((time.perf_counter() - step_start) * 1000, 2)
            })

            # Append to prompt trajectory
            history_trajectory += f"\nThought: {thought}\nAction: {action}\nAction Input: {json.dumps(action_input)}\nObservation: {obs_str}\n"

        # If loop exited without explicit Final Answer, synthesize directly
        if not final_answer:
            synth_prompt = (
                f"{history_trajectory}\n"
                "Thought: I now have sufficient verified information.\n"
                "Final Answer:"
            )
            final_answer = self.llm.generate(
                prompt=synth_prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=800,
                caller="react_agent"
            )

        # 3. Deanonymize output if PII anonymization was applied
        if deanonymize_map:
            final_answer = PIIAnonymizer.deanonymize(final_answer, deanonymize_map)

        total_duration = round((time.perf_counter() - start_total) * 1000, 2)

        # 4. Record trace to observability database
        try:
            status = self.llm.get_status()
            record_llm_trace(
                caller="react_agent",
                provider=status.get("mode", "local"),
                model=status.get("model", "qwen3.5:4b"),
                latency_ms=total_duration,
                user_prompt=clean_query,
                system_prompt=system_prompt,
                response=final_answer,
                tools_used=[{"name": t} for t in tools_executed]
            )
        except Exception:
            pass

        return {
            "answer": final_answer,
            "steps": steps_trace,
            "total_duration_ms": total_duration,
            "tools_used": tools_executed,
            "pii_anonymized": bool(deanonymize_map)
        }

    @staticmethod
    def _parse_react_response(text: str) -> Tuple[str, Optional[str], Dict[str, Any]]:
        """Parses Thought, Action, and Action Input from model response."""
        thought = ""
        action = None
        action_input: Dict[str, Any] = {}

        # Extract Thought
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|\nFinal Answer:|$)", text, re.DOTALL | re.IGNORECASE)
        if thought_match:
            thought = thought_match.group(1).strip()

        # Extract Action
        action_match = re.search(r"Action:\s*([a-zA-Z0-9_\-]+)", text, re.IGNORECASE)
        if action_match:
            action = action_match.group(1).strip()

        # Extract Action Input
        input_match = re.search(r"Action Input:\s*(\{.*?\})", text, re.DOTALL | re.IGNORECASE)
        if input_match:
            raw_json = input_match.group(1).strip()
            try:
                action_input = json.loads(raw_json)
            except Exception:
                # Simple regex fallback for query: "..."
                q_m = re.search(r'["\']query["\']:\s*["\'](.*?)["\']', raw_json)
                if q_m:
                    action_input = {"query": q_m.group(1)}

        return thought, action, action_input
