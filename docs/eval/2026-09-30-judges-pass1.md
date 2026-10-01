# Two judges vs human labels (Stage 9a)

Date: 2026-09-30 · 54 claims labelled by hand (52 supported, 2 not) · same claim and labelled sources for both judges

| Judge | Accuracy | **False support** | Missed support | Cohen's kappa | Errors | Median time | Cost per 1,000 judgements |
|---|---|---|---|---|---|---|---|
| gpt-4.1-mini (LLM judge) | 78% | **1** | 11 | 0.08 | 0 | 0.9s | $0.338 |
| Jev (threshold 0.5) | 74% | **1** | 13 | 0.06 | 0 | 0.5s | $0.049 |

False support = the judge accepted a claim you marked unsupported (the error that would let a wrong claim through). Kappa corrects agreement for chance.

## Jev threshold

| Threshold | Accuracy | False support | Missed support | Kappa |
|---|---|---|---|---|
| 0.3 | 78% | 1 | 11 | 0.08 |
| 0.4 | 78% | 1 | 11 | 0.08 |
| 0.5 | 74% | 1 | 13 | 0.06 |
| 0.6 | 74% | 1 | 13 | 0.06 |
| 0.7 | 74% | 1 | 13 | 0.06 |
| 0.8 | 70% | 1 | 15 | 0.05 |

**Uncertain band 0.35-0.65 sent to a human:** 2 of 54 claims (4%); on the rest Jev scores 77% with 1 false support.

## Where a judge disagreed with you

| Claim | Your label | LLM | Jev p | Origin |
|---|---|---|---|---|
| c01: The platform is delivered as a Progressive Web App hosted on Heroku, with development assisted by AI tools like Claude. | supported | False | 0.02 | near-miss |
| c14: Wall Inspector uses a managed PostgreSQL 14 database in production, connected via the DATABASE_URL environment variable. | supported | False | 0.02 | near-miss |
| c15: Barry held multiple leadership roles at Intel Ireland, Leixlip, including 300mm CMP Group Leader (July 2009 – September 2016), 200mm CMP Gro | supported | False | 0.04 | near-miss |
| c19: It is a retrieval-augmented generation (RAG) assistant deployed as a live web app and accessible via an API and a RESTful server. | supported | False | 0.44 | near-miss |
| c21: Barry fixed this by rebuilding the system so the week is calculated purely from the number of user interactions, eliminating drift. | supported | False | 0.02 | near-miss |
| c24: It demonstrates product thinking, reliable scheduled systems, real-world messaging integration, and advanced AI integration. | supported | False | 0.02 | near-miss |
| c26: Barry's projects that include an MCP server are Ask Barry and Sentinel Agent. | supported | False | 0.11 | near-miss |
| c28: Barry fixed this by adding an automatic fallback to a custom free-form message, with tests covering both paths. | supported | False | 0.08 | near-miss |
| c34: The Ask Barry project also deploys Docker containers automatically via Azure after passing CI tests. | supported | False | 0.05 | near-miss |
| c44: Barry has used Terraform for infrastructure as code in a single project. | supported | True | 0.06 | near-miss |
| c46: Barry fixed HTTPS certificate validation failures caused by the registrar's DNS handling by moving the DNS to AWS Route 53 and setting the r | supported | False | 0.01 | near-miss |
| c52: StoryCatcher is a module within the In My Time project that allows family members to record interviews with relatives directly on WhatsApp. | supported | False | 0.05 | near-miss |
| c53: This solution was applied in both the In My Time and my30words projects. | not_supported | True | 0.84 | answer |
| c54: These tests are automated and include API test suites, ensuring thorough testing of the application's security and functionality in a browse | supported | True | 0.49 | answer |
