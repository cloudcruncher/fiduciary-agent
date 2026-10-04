# Experiment: STE system prompt vs the current copilot prompt

Harness: `experiments/prompt_ab.py` (`uv run experiments/prompt_ab.py <ollama-model>`).
Setup: one fixed fake client context, 6 questions, temperature 0, fixed seed, local Ollama.

| Prompt | What it is |
|---|---|
| **A** | The current rules from `copilot.py`, trimmed to the topics in the test, with fixed numbers |
| **B** | Plain STE rewrite. Topic instructions are one bullet list |
| **C** | STE rewrite. Each topic rule has a label, and rule 4 says to use only the matching topic |

## Results (6 questions per cell)

| Model | Prompt | Answers with all expected facts | Avg words | Avg words per sentence |
|---|---|---|---|---|
| llama3.2:3b | A | 4/6 | 87 | 6.4 |
| llama3.2:3b | B | 2/6 | 30 | 6.1 |
| llama3.2:3b | C | 4/6 | 33 | 6.7 |
| qwen3.5:4b | A | 6/6 | 129 | 8.9 |
| qwen3.5:4b | B | 6/6 | 60 | 5.4 |
| qwen3.5:4b | C | 5/6 | 34 | 5.8 |

## What the results show

1. **STE prompts cut answer length by 55% to 75%.** The answers stay on topic. The current prompt makes both models write long working-out.
2. **Prompt structure matters more than prompt style.** Prompt B, with one list of topic bullets, made llama answer the mortgage question with the holiday template. Prompt C fixed that by labelling each rule and saying "use only the matching topic".
3. **The 3B model is the weak point.** llama refuses the "ignore all instructions" question with a vague "I can't provide that information" under every prompt. This is a model limit, not a prompt limit. The Prompt Guard would block this query before it reaches the model.
4. **qwen3.5:4b follows all three prompts well.** Its one "miss" on prompt C is a checker error. The answer was correct (£3,700 left, £1,700 shortfall, 62 days). The checker looked for the literal number 500.

## Limits of this test. Read before you trust it

- 6 questions and 1 run per cell. This is a smoke test. It is not evidence.
- The "facts" check is a substring match. It misses correct answers that use a different form of the number.
- The harness has an "invented numbers" count. It flags every derived number (for example a new runway). Ignore that count. Do not use it to compare prompts.
- Prompt A is trimmed. The real prompt has 12 rules and per-request f-string values. A fair test needs the real prompt builder.
- Temperature 0 with a fixed seed. The production call uses 0.2.

## Next step if you want to continue

Run 30 or more questions. Use the real `copilot.py` prompt builder. Replace the substring check with a numeric-tolerance check. Then compare A and C on answer length and correctness. Do not change the production prompt before that.
