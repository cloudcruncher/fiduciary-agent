# Interactive Architecture & System Explainers

This directory contains standalone interactive explainers and technical architectural specifications for the Personal Fiduciary Agent.

| Document / Tool | Format | Purpose & Contents |
|---|---|---|
| [**enterprise-walkthrough.html**](enterprise-walkthrough.html) | Interactive HTML Application | Comprehensive deep-dive covering institutional solution design, production vs. PoC differences, bank-grade compliance (FCA Consumer Duty, ISO 27001), real-time telemetry, and technical alternative evaluations. |
| [**credit-explorer.html**](credit-explorer.html) | Interactive HTML Simulator | Client-side UK statutory creditworthiness & affordability simulator mirroring the deterministic Python engine in `fiduciary/analysis/credit.py`. |
| [**gateway.md**](gateway.md) | Architectural Specification | Mermaid flowchart and step-by-step breakdown of query lifecycle, Prompt Guard validation, MCP context grounding, caching, and multi-tier LLM failover. |
