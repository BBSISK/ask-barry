# Answer evaluation

Date: 2026-09-27 · Model: claude-haiku-4-5 (anthropic); judge gpt-4.1-mini · Retrieval: Azure hybrid, top 8 · Answerable: 37 · Traps: 8

| Metric | Value |
|---|---|
| Answered (answerable questions) | 92% |
| Answer cites a section containing the answer | 89% |
| Faithful to cited sources (LLM judge, of answered) | 97% |
| Answers with a true-but-uncited claim | 1 |
| Regression checks failed | 1 |
| **Traps: no false claim** | **100%** |
| Questions passing every check | 40 of 45 |

The judge is the same model family (gpt-4.1-mini), so the citation test and regression checks are deliberately deterministic. Sample sizes are small; one question is about 3 points.

## Failures and notes

### profile-06 (answerable)
- Answer: I can't find evidence of that in Barry's public GitHub documentation.
- answered=False · cited_answer=False · faithful=None
- Sources: none

### profile-09 (answerable)
- Answer: I can't find evidence of that in Barry's public GitHub documentation.
- answered=False · cited_answer=False · faithful=None
- Sources: none

### profile-10 (answerable)
- Answer: Barry has used Microsoft Azure tools in the Ask Barry project: Azure OpenAI (for embeddings and a chat model) [1], and Azure AI Search (for storing chunks and vectors with hybrid search) [1]. He has also used Render for deploying the Flask app [2].
- answered=True · cited_answer=False · faithful=True
- Check failures: missing 'Terraform'
- Sources: ask-barry/docs/azure-setup.md (Stage 3: Azure setup); ask-barry/README.md (Ask Barry > Current status: Stage 6 complete (RAG live in production, answer quality evaluated))

### inmytime-05 (answerable)
- Answer: I can't find evidence of that in Barry's public GitHub documentation.
- answered=False · cited_answer=False · faithful=None
- Sources: none

### askbarry-02 (answerable)
- Answer: Yes. Barry deployed a retrieval-augmented generation (RAG) system to production as part of Ask Barry. The system uses Azure AI Search for hybrid (keyword and vector) retrieval over his public repository documentation, and Azure OpenAI (gpt-4.1-mini) to generate answers with citations. The RAG system is live in production and includes honesty rules enforced in code that refuse answers without valid
- answered=True · cited_answer=True · faithful=False
- Unsupported claims: The RAG system is live in production and includes honesty rules enforced in code that refuse answers without valid citations. (true but uncited: support is in a retrieved section the answer didn't cite)
- Sources: ask-barry/README.md (Ask Barry > Current status: Stage 6 complete (RAG live in production, answer quality evaluated)); ask-barry/README.md (Ask Barry > Current status: Stage 6 complete (RAG live in production, answer quality evaluated))

## All questions

| ID | Type | Pass | Supported | Sources cited |
|---|---|---|---|---|
| profile-01 | answerable | ✅ | True | 1 |
| profile-02 | answerable | ✅ | True | 1 |
| profile-03 | answerable | ✅ | True | 1 |
| profile-04 | answerable | ✅ | True | 1 |
| profile-05 | answerable | ✅ | True | 1 |
| profile-06 | answerable | ❌ | False | 0 |
| profile-07 | answerable | ✅ | True | 2 |
| profile-08 | answerable | ✅ | True | 6 |
| profile-09 | answerable | ❌ | False | 0 |
| profile-10 | answerable | ❌ | True | 2 |
| wall-01 | answerable | ✅ | True | 1 |
| wall-02 | answerable | ✅ | True | 1 |
| wall-03 | answerable | ✅ | True | 1 |
| wall-04 | answerable | ✅ | True | 2 |
| wall-05 | answerable | ✅ | True | 2 |
| wall-06 | answerable | ✅ | True | 1 |
| wall-07 | answerable | ✅ | True | 4 |
| wall-08 | answerable | ✅ | True | 2 |
| wall-09 | answerable | ✅ | True | 2 |
| agentmath-01 | answerable | ✅ | True | 1 |
| agentmath-02 | answerable | ✅ | True | 3 |
| agentmath-03 | answerable | ✅ | True | 1 |
| agentmath-04 | answerable | ✅ | True | 2 |
| agentmath-05 | answerable | ✅ | True | 1 |
| inmytime-01 | answerable | ✅ | True | 1 |
| inmytime-02 | answerable | ✅ | True | 1 |
| inmytime-03 | answerable | ✅ | True | 1 |
| inmytime-04 | answerable | ✅ | True | 1 |
| inmytime-05 | answerable | ❌ | False | 0 |
| inmytime-06 | answerable | ✅ | True | 1 |
| brief-01 | answerable | ✅ | True | 5 |
| brief-02 | answerable | ✅ | True | 1 |
| brief-03 | answerable | ✅ | True | 1 |
| brief-04 | answerable | ✅ | True | 2 |
| brief-05 | answerable | ✅ | True | 1 |
| askbarry-01 | answerable | ✅ | True | 3 |
| trap-01 | trap | ✅ | False | 0 |
| trap-02 | trap | ✅ | False | 0 |
| trap-03 | trap | ✅ | False | 0 |
| trap-04 | trap | ✅ | False | 0 |
| trap-05 | trap | ✅ | False | 0 |
| trap-06 | trap | ✅ | False | 0 |
| trap-07 | trap | ✅ | False | 0 |
| trap-09 | trap | ✅ | False | 0 |
| askbarry-02 | answerable | ❌ | True | 2 |

## All answers (for human review)

- **profile-01** ✅ Where did Barry work before becoming a software developer?
  - Barry spent 30 years at Intel Ireland leading engineering teams in high-volume, tightly controlled manufacturing before becoming a software developer.
- **profile-02** ✅ What qualification is Barry studying for, and where?
  - Barry is completing a Higher Diploma in Software Development at Maynooth University, expected in 2027.
- **profile-03** ✅ When is Barry available for full-time roles?
  - Barry is open to full-time roles from June 2027 [1]. He is currently completing a Higher Diploma in Software Development at Maynooth University, expected to finish in 2027, and is available for part-time work during his studies [1].
- **profile-04** ✅ Which AI coding agents does Barry use day to day?
  - Barry uses Claude Code and Google Antigravity as AI coding agents in his daily work [1]. He also builds agents into his own applications [1].
- **profile-05** ✅ Describe Barry's workflow from prompt to production.
  - Barry's workflow begins with describing a change to an AI coding agent (Claude Code or Antigravity) in VS Code, which writes both code and tests. He then reviews the diff and runs tests locally before pushing to GitHub, where a CI pipeline runs 86 tests on a clean Linux runner. The change deploys automatically to production via Render only if all checks pass; failing changes never reach users. This approach mirrors the inspection discipline he applied to production lines at Intel: inspect at eve
- **profile-06** ❌ Which programming languages does Barry know?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **profile-07** ✅ Has Barry used Docker?
  - Yes. Barry has used Docker in Wall Inspector, which runs as a Docker container with Flask, Gunicorn, and multiple agents [2]. The project includes a Dockerfile and can be started with Docker Compose for the full stack (web + PostgreSQL 15) [1].
- **profile-08** ✅ What cloud and DevOps tools has Barry worked with?
  - Barry has worked with Docker, Terraform, GitHub Actions, Render, Cloudflare, and Cloudinary [1]. His projects demonstrate practical use: Ask Barry uses Terraform for infrastructure codification [4], GitHub Actions for nightly documentation fetches [3], and Azure services for deployment [4][5]. In My Time showcases testing practices [2], and the MCP tool is built on official SDKs with unit tests [6].
- **profile-09** ❌ How can I contact Barry?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **profile-10** ❌ What cloud tools has Barry used?
  - Barry has used Microsoft Azure tools in the Ask Barry project: Azure OpenAI (for embeddings and a chat model) [1], and Azure AI Search (for storing chunks and vectors with hybrid search) [1]. He has also used Render for deploying the Flask app [2].
- **wall-01** ✅ What is Wall Inspector and who is it for?
  - Global Wall Inspector is a clinical skills-assessment and certification platform built for civil engineering, heritage conservation, and masonry construction students and assessors [1]. It turns high-resolution masonry photographs into interactive diagnostic workstations where students inspect walls using a zoom loupe, drop spatial defect pins, classify structural severity, and prescribe conservation remedies, which are then graded in real time against expert ground-truth bounding boxes [1]. Two
- **wall-02** ✅ What does the Intake Sentinel agent check in uploaded photographs?
  - Barry's Intake Sentinel agent (in the Wall Inspector project) evaluates newly uploaded field photographs across 4 photogrammetric pillars: 90° orthogonal plane, diffuse illumination, course framing, and Laplacian focus sharpness. It includes a non-blocking 'Progress Under Advisement' override.
- **wall-03** ✅ Which tools does the Wall Inspector MCP server expose?
  - Barry's Wall Inspector MCP server exposes four domain agents over JSON-RPC 2.0: `sentinel_evaluate_image`, `curriculum_cohort_intelligence`, `list_skill_specimens`, and `export_coco_dataset_stats`. These tools are available to external LLM hosts including Claude, Gemini, and Cursor.
- **wall-04** ✅ How does human-in-the-loop provenance tracking work in Wall Inspector?
  - Wall Inspector uses a 3-tier human-in-the-loop provenance model to track defect annotations [1, 2]. When a masonry photograph is uploaded, Gemini Vision proposes defect pins tagged as `auto_suggested` (unverified, excluded from ground truth) [1]. An assessor can then review, adjust, and save the AI proposal, which upgrades it to `auto_accepted` with the assessor's name and timestamp audited [1]. Alternatively, assessors can mark all defects from scratch, creating `human_graded` gold-standard ben
- **wall-05** ✅ What dataset format does Wall Inspector export for computer vision tools?
  - Wall Inspector exports labeled datasets in Microsoft COCO 1.0 JSON format for downstream Computer Vision tools including CVAT and YOLOv8. The exporter (`/api/skill-assessment/export-coco`) includes full-resolution Cloudinary image links, expert ground-truth bounding boxes, and crowdsourced student consensus pins.
- **wall-06** ✅ How many automated tests does Wall Inspector run?
  - Wall Inspector runs 86 automated unit and agent tests [1]. The test suite is executed via `python3 -m unittest discover` and includes an MCP server self-test [1].
- **wall-07** ✅ Which database does Wall Inspector use in production?
  - Wall Inspector uses PostgreSQL 15 in production [1][2][4]. The connection string is managed via the `DATABASE_URL` environment variable [1], and the system includes a non-destructive auto-migration on start-up to preserve existing production records [3].
- **wall-08** ✅ Has Barry used Terraform for infrastructure as code?
  - Yes. In the ask-barry project, Terraform is planned for Stage 7e to codify Azure resources [1]. In the wall_inspector project, Terraform is already in use for infrastructure as code, with the configuration in infra/main.tf [2].
- **wall-09** ✅ How are credentials and secrets handled in Wall Inspector?
  - In Wall Inspector, all credentials and cloud endpoints are injected strictly via environment variables and never hardcoded [1]. These include the PostgreSQL connection string, Cloudinary CDN key, Google Gemini Vision API key, assessor workstation credentials, and cryptographic session signing key [1]. Barry has also documented lessons from a credential-exposure incident in another project (my30words_showcase), where he rotates every exposed secret, rebuilds Git history, and applies strict `.giti
- **agentmath-01** ✅ How many assessment items does AgentMath have?
  - AgentMath has 3,000+ curriculum-aligned assessment items across 14+ Junior Cycle topics [1].
- **agentmath-02** ✅ How does AgentMath protect children's privacy?
  - AgentMath offers multiple privacy-conscious entry points: students can use it with no registration at all via 'Quick Try', or with anonymous guest codes (like 'panda42') that track progress without collecting names or emails [1]. The platform also supports Google and Microsoft sign-in for schools with existing accounts [1]. Barry designed this privacy-first approach because many learning platforms ask children to hand over personal data just to get started [2], and AgentMath demonstrates 'privac
- **agentmath-03** ✅ What is Agent of the Lost Numbers?
  - Agent of the Lost Numbers is a 3D, first-person history-of-maths adventure built in Three.js, part of AgentMath. It features a procedurally generated maze and a room-by-room journey from Mesopotamia to Egypt, with puzzles to solve.
- **agentmath-04** ✅ What technology stack is AgentMath built with?
  - AgentMath uses Python and Flask for the backend, SQLite for data storage (question bank, student progress, and performance analytics), and HTML, CSS, JavaScript, and Three.js for the frontend. Identity management is handled through Google OAuth and Microsoft OAuth, with anonymous guest codes also supported. The platform is delivered as a Progressive Web App and hosted on PythonAnywhere, with development assisted by Claude.
- **agentmath-05** ✅ What gamification features keep AgentMath students engaged?
  - AgentMath uses badges, avatars, leaderboards and a Points for Prizes reward system to keep students engaged [1]. The platform also includes classroom games and lesson packs with station-based activities [1].
- **inmytime-01** ✅ Does In My Time store the family stories it collects?
  - No. In My Time is built on a privacy-first architecture where the server relays each answer in the same request and stores nothing [1]. The database has no column capable of holding an answer, and the only records kept are timestamps and the author's position in the question sequence [1]. Media is forwarded by reference and never downloaded [1].
- **inmytime-02** ✅ How does In My Time get the grandparent's consent?
  - In My Time gets the grandparent's consent through WhatsApp. The custodian (adult child) signs up on the website and chooses which chapters to explore, then the grandparent (author) receives a single WhatsApp consent message. Nothing starts until the grandparent replies to that message—consent remains in their hands rather than being a checkbox ticked by someone else.
- **inmytime-03** ✅ What is StoryCatcher?
  - StoryCatcher is a module within the In My Time project that lets family members record interviews with relatives in the browser [1]. It features guided interviews using curated question packs (including packs derived from the 1937 Schools' Collection), client-side encryption of recordings and names, per-interviewee access control, photo capture during recordings, flexible storage options (Cloudflare R2 or Google Drive), and a LifeLine timeline feature that pins clips and notes to decades and the
- **inmytime-04** ✅ Why were admin WhatsApp alerts failing silently, and how was it fixed?
  - In the In My Time project, admin alerts were failing silently because WhatsApp's 24-hour session rule only allows free-form messages to be delivered while a conversation is open. Barry fixed this by adding an automatic fallback to a pre-approved template message, with tests covering both paths.
- **inmytime-05** ❌ Has Barry built multilingual or internationalised software?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **inmytime-06** ✅ What browser testing has Barry done?
  - Barry has done browser testing that exercises real encryption and media playback, as part of the In My Time project [1]. This testing is described as part of 'testing at depth' for a privacy-focused messaging application designed for an older audience [1].
- **brief-01** ✅ What is Brief?
  - Brief is a journaling app that asks users to write thirty words a week in response to prompts, creating a personal record of how they change over time [1]. It delivers prompts via WhatsApp or email [3], and users can scroll back through their archived entries, share with small groups, or seal entries as time capsules [4]. The app is private by default, with full data export and permanent deletion options [2], and is available as an installable web app at www.my30words.com [5].
- **brief-02** ✅ How did Barry handle a leaked credential incident?
  - Barry handled a credential-exposure incident by rotating every exposed secret (Google, Microsoft and Twilio) so the leaked values were dead, rebuilding the Git history as a single clean commit, and locking the repository down with a strict `.gitignore` for databases, configuration and backups. He also applied the lesson to every project: if a first commit ever contained a secret, reset the history rather than just untracking the file.
- **brief-03** ✅ Why did weekly prompts drift off schedule, and how was it fixed?
  - In my30words, weekly prompts drifted off schedule because each user's week position was tracked as a stored counter that could fall out of step, causing some users to receive prompts on an 8-day cycle instead of 7, and for others the cycle stalled. Barry rebuilt it so the week is calculated purely from time (from sign-up to now), eliminating drift, and back-filled existing users with a one-off migration [1].
- **brief-04** ✅ How did Barry fix HTTPS certificates that would not validate?
  - Barry fixed HTTPS certificate validation failures by moving DNS to Cloudflare and setting the records to DNS-only mode. This solution addressed issues where the registrar's DNS setup was preventing certificate issuance. He applied this same fix across multiple projects: my30words (my30words_showcase) and In My Time (inmytime-showcase).
- **brief-05** ✅ What are time capsules in Brief?
  - In Brief, time capsules are a feature that allows users to seal an entry for 1, 5, or 10 years [1]. This enables users to preserve their journal entries and access them at a future date of their choosing.
- **askbarry-01** ✅ What is the Ask Barry project?
  - Ask Barry is a portfolio assistant that answers questions about Barry Sisk's software projects using only documentation from his public GitHub repositories, and cites the repo, file and section behind every answer [2]. It is an AI assistant intended for recruiters, interviewers and developers who want a quick, sourced answer about what Barry has built [1]. The project is live at https://ask-barry-7dkz.onrender.com [2] and includes a Flask app with Azure AI Search, grounded answering with citatio
- **trap-01** ✅ Has Barry used Kubernetes?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-02** ✅ Does Barry have AWS experience?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-03** ✅ Has Barry built native mobile apps in Swift or Kotlin?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-04** ✅ Has Barry built front ends with React?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-05** ✅ Does Barry have a PhD?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-06** ✅ Has Barry used MongoDB?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-07** ✅ Has Barry trained a YOLOv8 model?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-09** ✅ Has Barry worked with Apache Kafka?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **askbarry-02** ❌ Has Barry deployed a RAG system to production?
  - Yes. Barry deployed a retrieval-augmented generation (RAG) system to production as part of Ask Barry. The system uses Azure AI Search for hybrid (keyword and vector) retrieval over his public repository documentation, and Azure OpenAI (gpt-4.1-mini) to generate answers with citations. The RAG system is live in production and includes honesty rules enforced in code that refuse answers without valid citations.
