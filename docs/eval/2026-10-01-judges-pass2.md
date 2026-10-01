# Two judges vs human labels (Stage 9a)

Date: 2026-10-01 · 55 claims labelled by hand (43 supported, 12 not) · same claim and labelled sources for both judges

| Judge | Accuracy | **False support** | Missed support | Cohen's kappa | Errors | Median time | Cost per 1,000 judgements |
|---|---|---|---|---|---|---|---|
| gpt-4.1-mini (LLM judge) | 87% | **3** | 4 | 0.64 | 0 | 0.7s | $0.335 |
| Jev (threshold 0.5) | 84% | **3** | 6 | 0.56 | 0 | 0.5s | $0.049 |

**Human self-agreement (two blind passes):** 43 of 54 claims labelled the same (80%), kappa 0.10; 11 changed. Scores above use the second pass.

False support = the judge accepted a claim you marked unsupported (the error that would let a wrong claim through). Kappa corrects agreement for chance.

## Jev threshold

| Threshold | Accuracy | False support | Missed support | Kappa |
|---|---|---|---|---|
| 0.3 | 84% | 4 | 5 | 0.53 |
| 0.4 | 84% | 4 | 5 | 0.53 |
| 0.5 | 84% | 3 | 6 | 0.56 |
| 0.6 | 84% | 3 | 6 | 0.56 |
| 0.7 | 84% | 3 | 6 | 0.56 |
| 0.8 | 80% | 3 | 8 | 0.49 |

**Uncertain band 0.35-0.65 sent to a human:** 2 of 55 claims (4%); on the rest Jev scores 85% with 3 false support.

## Where a judge disagreed with you

| Claim | Your label | LLM | Jev p | Origin |
|---|---|---|---|---|
| c13: These tools include `sentinel_evaluate_image`, `curriculum_cohort_intelligence`, `list_skill_specimens`, and `export_coco_dataset_stats`. | not_supported | True | 0.97 | answer |
| c15: Barry held multiple leadership roles at Intel Ireland, Leixlip, including 300mm CMP Group Leader (July 2009 – September 2016), 200mm CMP Gro | supported | False | 0.04 | near-miss |
| c17: The RAG system is live, evaluated for answer quality, and includes a job-ad evidence agent built with the Microsoft Agent Framework. | not_supported | True | 0.98 | answer |
| c21: Barry fixed this by rebuilding the system so the week is calculated purely from the number of user interactions, eliminating drift. | supported | False | 0.02 | near-miss |
| c26: Barry's projects that include an MCP server are Ask Barry and Sentinel Agent. | supported | False | 0.14 | near-miss |
| c28: Barry fixed this by adding an automatic fallback to a custom free-form message, with tests covering both paths. | supported | False | 0.09 | near-miss |
| c29: Agent of the Lost Numbers is a 3D, first-person history-of-maths adventure built in Three.js, featuring a procedurally generated maze and a  | not_supported | True | 0.99 | answer |
| c44: Barry has used Terraform for infrastructure as code in a single project. | supported | True | 0.06 | near-miss |
| c54: These tests are automated and include API test suites, ensuring thorough testing of the application's security and functionality in a browse | supported | True | 0.47 | answer |
