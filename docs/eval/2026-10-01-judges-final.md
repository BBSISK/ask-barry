# Two judges vs human labels (Stage 9a, final)

Two views of the same judge answers. **Blind** = my labels after two blind passes and a review with full sources, done without seeing the judges' answers. **Adjudicated** = the same labels with the claims below corrected after the judges disagreed with them, each settled by the source text. The adjudication saw the judges' answers, so it can favour them: read the two together.

| Judge | Labels | Accuracy | **False support** | Missed support | Cohen's kappa |
|---|---|---|---|---|---|
| gpt-4.1-mini (LLM judge) | blind | 89% | **1** | 5 | 0.66 |
| gpt-4.1-mini (LLM judge) | adjudicated | 98% | **1** | 0 | 0.95 |
| Jev (threshold 0.5) | blind | 87% | **1** | 6 | 0.62 |
| Jev (threshold 0.5) | adjudicated | 100% | **0** | 0 | 1.00 |

Barry's labelling passes against the blind labels: pass 1 85% (7 false support); pass 2 95% (0 false support)

Barry's labelling passes against the adjudicated labels: pass 1 76% (12 false support); pass 2 85% (5 false support)

## Adjudication (2026-10-01, Barry, after seeing the judges' answers; each change settled by the quoted source text)

| Claim | Blind label | Adjudicated | Why (from the sources) |
|---|---|---|---|
| c15: Barry held multiple leadership roles at Intel Ireland, Leixlip, including 300mm CMP Group Leader (July 2009 –  | supported | not_supported | Claim: Implant Group Leader until December 2019. career.md: October 2016 – August 2019. |
| c21: Barry fixed this by rebuilding the system so the week is calculated purely from the number of user interaction | supported | not_supported | Claim: week calculated from the number of user interactions. Brief README: calculated purely from time (sign-up to now). |
| c26: Barry's projects that include an MCP server are Ask Barry and Sentinel Agent. | supported | not_supported | Claim: MCP projects are Ask Barry and Sentinel Agent. Sources: Ask Barry and Wall Inspector; Sentinel is an agent inside Wall Inspector, not a project. |
| c28: Barry fixed this by adding an automatic fallback to a custom free-form message, with tests covering both paths | supported | not_supported | Claim: fallback to a custom free-form message. Source: fallback to a pre-approved template message. |
| c34: The Ask Barry project also deploys Docker containers automatically via Azure after passing CI tests. | supported | not_supported | Claim: deploys via Azure. Flowchart: Render auto-deploys the Docker container after CI passes. |
| c44: Barry has used Terraform for infrastructure as code in a single project. | supported | not_supported | Claim: Terraform in a single project. Sources: Ask Barry infra/ and Wall Inspector infra/main.tf (two projects). Not in the blind review sample; pass 2 label used. |
| c29: Agent of the Lost Numbers is a 3D, first-person history-of-maths adventure built in Three.js, featuring a proc | not_supported | supported | Review note said 'My error - should have been yes' but n was keyed; the description matches the source. |

---

# Full report, adjudicated labels

Date: 2026-10-01 · 55 claims labelled by hand (41 supported, 14 not) · same claim and labelled sources for both judges

| Judge | Accuracy | **False support** | Missed support | Cohen's kappa | Errors | Median time | Cost per 1,000 judgements |
|---|---|---|---|---|---|---|---|
| gpt-4.1-mini (LLM judge) | 98% | **1** | 0 | 0.95 | 0 | 0.8s | $0.335 |
| Jev (threshold 0.5) | 100% | **0** | 0 | 1.00 | 0 | 0.5s | $0.049 |

**Labels used:** reviewed final labels (27 claims re-checked with full sources: every disputed claim plus a random sample of the rest). The human passes, scored against them:

| Labeller | Accuracy | False support |
|---|---|---|
| Barry, pass 1 | 76% | 12 |
| Barry, pass 2 | 85% | 5 |

**Human self-agreement (two blind passes):** 43 of 54 claims labelled the same (80%), kappa 0.10; 11 changed. Scores above use the second pass.

False support = the judge accepted a claim you marked unsupported (the error that would let a wrong claim through). Kappa corrects agreement for chance.

## Jev threshold

| Threshold | Accuracy | False support | Missed support | Kappa |
|---|---|---|---|---|
| 0.3 | 98% | 1 | 0 | 0.95 |
| 0.4 | 98% | 1 | 0 | 0.95 |
| 0.5 | 100% | 0 | 0 | 1.00 |
| 0.6 | 98% | 0 | 1 | 0.95 |
| 0.7 | 98% | 0 | 1 | 0.95 |
| 0.8 | 96% | 0 | 2 | 0.91 |

**Uncertain band 0.35-0.65 sent to a human:** 2 of 55 claims (4%); on the rest Jev scores 100% with 0 false support.

## Where a judge disagreed with you

| Claim | Your label | LLM | Jev p | Origin |
|---|---|---|---|---|
| c44: Barry has used Terraform for infrastructure as code in a single project. | not_supported | True | 0.05 | near-miss |
