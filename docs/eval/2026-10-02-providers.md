# Answer quality by model provider

Date: 2026-10-03 · Same questions, same retrieved sections (Azure hybrid, top 8), same prompt and honesty rules; only the answering model changes. Judge: gpt-4.1-mini (azure-openai).

| Provider | Model | Passing | Faithful | True-but-uncited | Regression fails | Traps: no false claim | Errors | Median latency | Avg tokens in / out |
|---|---|---|---|---|---|---|---|---|---|
| azure-openai | `gpt-4.1-mini` | 45 of 47 | 95% | 2 | 0 | 100% | 0 | 1.2s | 2315 / 77 |
| bedrock-claude | `eu.anthropic.claude-haiku-4-5-20251001-v1:0` | 45 of 47 | 95% | 1 | 0 | 100% | 0 | 1.8s | 2654 / 112 |
| bedrock-nova | `eu.amazon.nova-2-lite-v1:0` | 45 of 47 | 95% | 2 | 0 | 100% | 0 | 0.7s | 2288 / 76 |

## Where the providers disagree

| ID | azure-openai | bedrock-claude | bedrock-nova |
|---|---|---|---|
| agentmath-03 | ❌ | ✅ | ✅ |
| inmytime-05 | ✅ | ✅ | ❌ |
| askbarry-01 | ✅ | ❌ | ✅ |

Notes:
- One run per provider; single runs vary by a few questions, so treat small gaps as noise.
- The judge is one fixed model for every provider. It may favour answers in its own style, especially from its own family; the citation test and regression checks are deterministic and unaffected.
- Per-provider reports with every answer are saved next to this file.
