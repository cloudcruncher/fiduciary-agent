# Explain-formats experiments

Made with the `explain-formats` skill. Each file uses one step of its ladder: STE writing, diagram, HTML page, video.

| File | Format | Status |
|---|---|---|
| `gateway.md` | Mermaid diagram + STE table | Done. Not rendered here. View it on GitHub. |
| `credit-messages-ste.md` | STE rewrite of user-facing credit text | Proposal. The code strings are unchanged. |
| `credit-explorer.html` | Interactive page. Open it in a browser. | Done. Scoring checked against the Python engine on 300 random cases. |
| `enterprise-walkthrough.html` | Interactive enterprise design & architecture walkthrough | Done. Design rationale, PoC vs production, bank compliance, and alternatives. |
| `prompt-ste-ab.md` + `../../experiments/prompt_ab.py` | A/B test of the system prompt | Done as a smoke test. Read its limits. |
| `video/` | Script, Manim source, rendered `gateway-story.mp4` (80 s, narrated) | Rendered. Narration has long silent gaps. See `video/script.md`. |
