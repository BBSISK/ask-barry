# Answer quality by model provider

Date: 2026-09-27 · Same questions, same retrieved sections (Azure hybrid, top 8), same prompt and honesty rules; only the answering model changes. Judge: gpt-4.1-mini (azure-openai).

| Provider | Model | Passing | Faithful | True-but-uncited | Regression fails | Traps: no false claim | Errors | Median latency | Avg tokens in / out |
|---|---|---|---|---|---|---|---|---|---|
| azure-openai | `gpt-4.1-mini` | 43 of 46 | 92% | 3 | 0 | 100% | 0 | 1.2s | 2197 / 72 |
| anthropic | `claude-haiku-4-5` | 45 of 46 | 97% | 1 | 0 | 100% | 0 | 2.0s | 2539 / 111 |
| gemini | `gemini-3.5-flash` | 46 of 46 | 100% | 0 | 0 | 100% | 0 | 3.4s | 2318 / 704 |

## Where the providers disagree

| ID | azure-openai | anthropic | gemini |
|---|---|---|---|
| profile-07 | ✅ | ❌ | ✅ |
| agentmath-03 | ❌ | ✅ | ✅ |
| inmytime-06 | ❌ | ✅ | ✅ |
| askbarry-01 | ❌ | ✅ | ✅ |

Notes:
- One run per provider; single runs vary by a few questions, so treat small gaps as noise.
- The judge is one fixed model for every provider. It may favour answers in its own style, especially from its own family; the citation test and regression checks are deterministic and unaffected.
- Per-provider reports with every answer are saved next to this file.
