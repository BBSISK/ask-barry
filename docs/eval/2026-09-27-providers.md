# Answer quality by model provider

Date: 2026-09-27 · Same questions, same retrieved sections (Azure hybrid, top 8), same prompt and honesty rules; only the answering model changes. Judge: gpt-4.1-mini (azure-openai).

| Provider | Model | Passing | Faithful | True-but-uncited | Regression fails | Traps: no false claim | Errors | Median latency | Avg tokens in / out |
|---|---|---|---|---|---|---|---|---|---|
| azure-openai | `gpt-4.1-mini` | 43 of 46 | 92% | 3 | 0 | 100% | 0 | 1.2s | 2197 / 71 |
| anthropic | `claude-haiku-4-5` | 45 of 46 | 97% | 1 | 0 | 100% | 0 | 2.1s | 2539 / 112 |
| gemini | `gemini-3.5-flash` | 0 of 46 | 0% | 0 | 38 | 0% | 46 | 0.0s | 0 / 0 |

## Where the providers disagree

| ID | azure-openai | anthropic | gemini |
|---|---|---|---|
| profile-01 | ✅ | ✅ | ❌ |
| profile-02 | ✅ | ✅ | ❌ |
| profile-03 | ✅ | ✅ | ❌ |
| profile-04 | ✅ | ✅ | ❌ |
| profile-05 | ✅ | ✅ | ❌ |
| profile-06 | ✅ | ✅ | ❌ |
| profile-07 | ✅ | ❌ | ❌ |
| profile-08 | ✅ | ✅ | ❌ |
| profile-09 | ✅ | ✅ | ❌ |
| profile-10 | ✅ | ✅ | ❌ |
| wall-01 | ✅ | ✅ | ❌ |
| wall-02 | ✅ | ✅ | ❌ |
| wall-03 | ✅ | ✅ | ❌ |
| wall-04 | ✅ | ✅ | ❌ |
| wall-05 | ✅ | ✅ | ❌ |
| wall-06 | ✅ | ✅ | ❌ |
| wall-07 | ✅ | ✅ | ❌ |
| wall-08 | ✅ | ✅ | ❌ |
| wall-09 | ✅ | ✅ | ❌ |
| agentmath-01 | ✅ | ✅ | ❌ |
| agentmath-02 | ✅ | ✅ | ❌ |
| agentmath-03 | ❌ | ✅ | ❌ |
| agentmath-04 | ✅ | ✅ | ❌ |
| agentmath-05 | ✅ | ✅ | ❌ |
| inmytime-01 | ✅ | ✅ | ❌ |
| inmytime-02 | ✅ | ✅ | ❌ |
| inmytime-03 | ✅ | ✅ | ❌ |
| inmytime-04 | ✅ | ✅ | ❌ |
| inmytime-05 | ✅ | ✅ | ❌ |
| inmytime-06 | ❌ | ✅ | ❌ |
| brief-01 | ✅ | ✅ | ❌ |
| brief-02 | ✅ | ✅ | ❌ |
| brief-03 | ✅ | ✅ | ❌ |
| brief-04 | ✅ | ✅ | ❌ |
| brief-05 | ✅ | ✅ | ❌ |
| askbarry-01 | ❌ | ✅ | ❌ |
| trap-01 | ✅ | ✅ | ❌ |
| trap-02 | ✅ | ✅ | ❌ |
| trap-03 | ✅ | ✅ | ❌ |
| trap-04 | ✅ | ✅ | ❌ |
| trap-05 | ✅ | ✅ | ❌ |
| trap-06 | ✅ | ✅ | ❌ |
| trap-07 | ✅ | ✅ | ❌ |
| trap-09 | ✅ | ✅ | ❌ |
| mcp-01 | ✅ | ✅ | ❌ |
| askbarry-02 | ✅ | ✅ | ❌ |

Notes:
- One run per provider; single runs vary by a few questions, so treat small gaps as noise.
- The judge is one fixed model for every provider. It may favour answers in its own style, especially from its own family; the citation test and regression checks are deterministic and unaffected.
- Per-provider reports with every answer are saved next to this file.
