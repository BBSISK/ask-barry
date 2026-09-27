# Answer evaluation

Date: 2026-09-27 · Model: claude-haiku-4-5 (anthropic); judge gpt-4.1-mini · Retrieval: Azure hybrid, top 8 · Answerable: 38 · Traps: 8

| Metric | Value |
|---|---|
| Answered (answerable questions) | 100% |
| Answer cites a section containing the answer | 100% |
| Faithful to cited sources (LLM judge, of answered) | 97% |
| Answers with a true-but-uncited claim | 1 |
| Regression checks failed | 0 |
| **Traps: no false claim** | **100%** |
| Questions passing every check | 45 of 46 |

The judge is the same model family (gpt-4.1-mini), so the citation test and regression checks are deliberately deterministic. Sample sizes are small; one question is about 3 points.

## Failures and notes

### profile-07 (answerable)
- Answer: Yes. Barry has used Docker in multiple projects. Wall Inspector runs with Docker Compose for its full stack [1], and its architecture includes a Docker container running Flask, Gunicorn, and AI agents [3]. Docker is also listed in his toolbox [2], and his deployment workflow uses GitHub Actions to build and deploy Docker containers to Render [4].
- answered=True · cited_answer=True · faithful=False
- Unsupported claims: Barry has used Docker in multiple projects. (true but uncited: support is in a retrieved section the answer didn't cite)
- Sources: wall_inspector/README.md (🏛️ Global Wall Inspector — AI Masonry Diagnostic & Skills Certification Platform > 🛠️ Quick Start & Verification > 1. Run with Docker Compose (Full Stack: Web + PostgreSQL 15)); BBSISK/README.md (🧰 Toolbox); wall_inspector/README.md (🏛️ Global Wall Inspector — AI Masonry Diagnostic & Skills Certification Platform > 🏗️ System & DevOps Architecture); BBSISK/README.md (⚙️ How I build: from prompt to production in minutes)

## All questions

| ID | Type | Pass | Supported | Sources cited |
|---|---|---|---|---|
| profile-01 | answerable | ✅ | True | 1 |
| profile-02 | answerable | ✅ | True | 1 |
| profile-03 | answerable | ✅ | True | 1 |
| profile-04 | answerable | ✅ | True | 2 |
| profile-05 | answerable | ✅ | True | 1 |
| profile-06 | answerable | ✅ | True | 1 |
| profile-07 | answerable | ❌ | True | 4 |
| profile-08 | answerable | ✅ | True | 8 |
| profile-09 | answerable | ✅ | True | 1 |
| profile-10 | answerable | ✅ | True | 5 |
| wall-01 | answerable | ✅ | True | 1 |
| wall-02 | answerable | ✅ | True | 1 |
| wall-03 | answerable | ✅ | True | 1 |
| wall-04 | answerable | ✅ | True | 2 |
| wall-05 | answerable | ✅ | True | 2 |
| wall-06 | answerable | ✅ | True | 1 |
| wall-07 | answerable | ✅ | True | 2 |
| wall-08 | answerable | ✅ | True | 3 |
| wall-09 | answerable | ✅ | True | 2 |
| agentmath-01 | answerable | ✅ | True | 1 |
| agentmath-02 | answerable | ✅ | True | 2 |
| agentmath-03 | answerable | ✅ | True | 1 |
| agentmath-04 | answerable | ✅ | True | 1 |
| agentmath-05 | answerable | ✅ | True | 1 |
| inmytime-01 | answerable | ✅ | True | 1 |
| inmytime-02 | answerable | ✅ | True | 1 |
| inmytime-03 | answerable | ✅ | True | 1 |
| inmytime-04 | answerable | ✅ | True | 1 |
| inmytime-05 | answerable | ✅ | True | 3 |
| inmytime-06 | answerable | ✅ | True | 2 |
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
| mcp-01 | answerable | ✅ | True | 3 |
| askbarry-02 | answerable | ✅ | True | 2 |

## All answers (for human review)

- **profile-01** ✅ Where did Barry work before becoming a software developer?
  - Barry spent 30 years at Intel Ireland leading engineering teams in high-volume, tightly controlled manufacturing before becoming a software developer.
- **profile-02** ✅ What qualification is Barry studying for, and where?
  - Barry is completing a Higher Diploma in Software Development at Maynooth University, with an expected completion date of 2027 [1].
- **profile-03** ✅ When is Barry available for full-time roles?
  - Barry is available for full-time roles from June 2027 [1]. He is currently open to part-time work during his studies toward a Higher Diploma in Software Development at Maynooth University, which he is completing in 2027 [1].
- **profile-04** ✅ Which AI coding agents does Barry use day to day?
  - Barry uses Claude Code and Google Antigravity as AI coding agents every day [1]. He uses them in VS Code to describe changes, which the agents write as code and tests alongside it [2].
- **profile-05** ✅ Describe Barry's workflow from prompt to production.
  - Barry's workflow begins with describing a change to an AI coding agent in VS Code, which writes both code and tests [1]. He then reviews the diff and runs tests locally, maintaining engineer oversight [1]. Next, he pushes to GitHub, triggering a CI pipeline that runs 86 tests plus an MCP self-test on a clean Linux runner [1]. Finally, Render auto-deploys a Docker container to production only after all checks pass; failing changes never reach users [1]. This process takes about two minutes from i
- **profile-06** ✅ Which programming languages does Barry know?
  - Barry knows Python, Java, SQL, JavaScript, and HTML/CSS [1].
- **profile-07** ❌ Has Barry used Docker?
  - Yes. Barry has used Docker in multiple projects. Wall Inspector runs with Docker Compose for its full stack [1], and its architecture includes a Docker container running Flask, Gunicorn, and AI agents [3]. Docker is also listed in his toolbox [2], and his deployment workflow uses GitHub Actions to build and deploy Docker containers to Render [4].
- **profile-08** ✅ What cloud and DevOps tools has Barry worked with?
  - Barry has worked with Docker, Terraform, GitHub Actions, Render, Cloudflare, and Cloudinary [1]. Across his projects, he has deployed applications using Docker Compose [7], managed infrastructure with Terraform [2, 3], automated CI/CD pipelines with GitHub Actions [2, 3], used Cloudflare for DNS and R2 storage [1, 8], and integrated Cloudinary CDN for image hosting [2, 4]. He has also used Azure services including Azure OpenAI and Azure AI Search [5, 6], and deployed on PythonAnywhere [8].
- **profile-09** ✅ How can I contact Barry?
  - Barry can be contacted at barry.b.sisk@gmail.com or via LinkedIn at https://www.linkedin.com/in/barry-s-50135113/
- **profile-10** ✅ What cloud tools has Barry used?
  - Barry has used Docker, Terraform, GitHub Actions, Render, Cloudflare, and Cloudinary for cloud and DevOps work [2]. Across his projects, he has deployed with Azure (Azure OpenAI, Azure AI Search) [1, 7], PostgreSQL and SQLite databases [2, 3], and Cloudinary CDN for image storage [3, 5]. He has also used Google Gemini API [4] and implemented OAuth with Google and Microsoft/Azure [2].
- **wall-01** ✅ What is Wall Inspector and who is it for?
  - Global Wall Inspector is a clinical skills-assessment and certification platform built for civil engineering, heritage conservation, and masonry construction students and assessors [1]. It turns high-resolution masonry photographs into interactive diagnostic workstations where students inspect walls using a zoom loupe, drop spatial defect pins, classify structural severity, and prescribe conservation remedies, which are then graded in real time against expert ground-truth bounding boxes [1]. Two
- **wall-02** ✅ What does the Intake Sentinel agent check in uploaded photographs?
  - Barry's Intake Sentinel agent evaluates newly uploaded field photographs across 4 photogrammetric pillars: 90° orthogonal plane, diffuse illumination, course framing, and Laplacian focus sharpness. It includes a non-blocking 'Progress Under Advisement' override.
- **wall-03** ✅ Which tools does the Wall Inspector MCP server expose?
  - Barry's Wall Inspector MCP server exposes four domain agents over JSON-RPC 2.0: `sentinel_evaluate_image`, `curriculum_cohort_intelligence`, `list_skill_specimens`, and `export_coco_dataset_stats`. These are available to external LLM hosts including Claude, Gemini, and Cursor.
- **wall-04** ✅ How does human-in-the-loop provenance tracking work in Wall Inspector?
  - Wall Inspector uses a 3-tier audit lineage for provenance tracking [1, 2]. When Gemini Vision proposes defect pins on image upload, they are tagged `auto_suggested` with unverified trust level [1]. When an assessor reviews, adjusts and saves the proposal, it is upgraded to `auto_accepted` with the assessor's name and timestamp audited [1]. Defects marked from scratch by assessors are tagged `human_graded` as gold-standard benchmarks [1]. Each defect pin carries a confidence score, and the assess
- **wall-05** ✅ What dataset format does Wall Inspector export for computer vision tools?
  - Wall Inspector exports labeled datasets in Microsoft COCO 1.0 JSON format for downstream Computer Vision tools including CVAT and YOLOv8. The MLOps COCO 1.0 Dataset Exporter includes full-resolution Cloudinary image links, expert ground-truth bounding boxes, and crowdsourced student consensus pins in the standard COCO JSON format.
- **wall-06** ✅ How many automated tests does Wall Inspector run?
  - Wall Inspector runs 86 automated unit and agent tests [1].
- **wall-07** ✅ Which database does Wall Inspector use in production?
  - Wall Inspector uses PostgreSQL 15 in production. The database connection string is injected via the `DATABASE_URL` environment variable [1], and the system architecture shows PostgreSQL 15 as the primary data store [2].
- **wall-08** ✅ Has Barry used Terraform for infrastructure as code?
  - Yes, Barry has used Terraform for infrastructure as code. In the Wall Inspector project, Terraform is used to define infrastructure in `infra/main.tf`, `infra/variables.tf`, and `infra/outputs.tf` [1][2]. Terraform is also listed in his DevOps toolbox [3].
- **wall-09** ✅ How are credentials and secrets handled in Wall Inspector?
  - In Wall Inspector, all credentials and cloud endpoints are injected strictly via environment variables and never hardcoded [1]. These include the PostgreSQL connection string, Cloudinary CDN key, Google Gemini Vision API key, assessor workstation credentials, and cryptographic session signing key [1]. Barry has also documented lessons from a credential-exposure incident in another project (my30words_showcase), where he rotates every exposed secret, rebuilds Git history, and applies strict `.giti
- **agentmath-01** ✅ How many assessment items does AgentMath have?
  - AgentMath has 3,000+ curriculum-aligned assessment items across 14+ Junior Cycle topics [1].
- **agentmath-02** ✅ How does AgentMath protect children's privacy?
  - AgentMath protects children's privacy through multiple mechanisms [1]. Students can use the platform fully without providing personal data by using Quick Try (no registration), anonymous guest codes (such as `panda42`) that track progress without collecting names or emails, or existing school accounts via Google/Microsoft sign-in [1]. The platform is designed with privacy-conscious principles for children [2], and guest progress transfers to accounts when students later sign in properly, so noth
- **agentmath-03** ✅ What is Agent of the Lost Numbers?
  - Agent of the Lost Numbers is a 3D, first-person history-of-maths adventure built in Three.js, part of the AgentMath platform. It features a procedurally generated maze and a room-by-room journey from Mesopotamia to Egypt, with puzzles for students to solve.
- **agentmath-04** ✅ What technology stack is AgentMath built with?
  - AgentMath uses Python and Flask for the backend, SQLite for data storage (question bank, student progress, and performance analytics), and HTML, CSS, JavaScript with Three.js for the frontend's 3D module [1]. Identity management is handled through Google OAuth and Microsoft OAuth, with anonymous guest codes also supported [1]. The platform is delivered as a Progressive Web App and hosted on PythonAnywhere [1]. Development involved AI-assisted development with Claude [1].
- **agentmath-05** ✅ What gamification features keep AgentMath students engaged?
  - AgentMath uses badges, avatars, leaderboards and a Points for Prizes reward system to keep students engaged [1]. The platform also includes classroom games and lesson packs with station-based activities [1].
- **inmytime-01** ✅ Does In My Time store the family stories it collects?
  - No. In My Time is built on a privacy-first architecture where the server relays each answer in the same request and stores nothing [1]. The database has no column capable of holding an answer, and the only records kept are timestamps and the author's position in the question sequence [1]. Media is forwarded by reference and never downloaded [1].
- **inmytime-02** ✅ How does In My Time get the grandparent's consent?
  - In My Time gets the grandparent's consent through WhatsApp: the custodian (adult child) signs up on the website and chooses which chapters to explore, then the grandparent (author) receives a single WhatsApp consent message. Nothing starts until the grandparent replies to that message—consent remains in their hands, not a checkbox someone else ticked.
- **inmytime-03** ✅ What is StoryCatcher?
  - StoryCatcher is a module within the In My Time project that lets family members record interviews with relatives in the browser [1]. It features guided interviews using curated question packs (including packs derived from the 1937 Schools' Collection), client-side encryption of recordings and names, per-interviewee access control, photo capture during recordings, flexible storage options (Cloudflare R2 or Google Drive), and a LifeLine timeline feature that pins clips and notes to decades and the
- **inmytime-04** ✅ Why were admin WhatsApp alerts failing silently, and how was it fixed?
  - Admin alerts were failing silently because of WhatsApp's 24-hour session rule: free-form messages are only delivered while a conversation is open, yet the messaging API reported every send as successful. Barry fixed it by adding an automatic fallback to a pre-approved template message, with tests covering both paths [1].
- **inmytime-05** ✅ Has Barry built multilingual or internationalised software?
  - Yes. In My Time includes German localisation built with Flask-Babel [1]. AgentMath demonstrates breadth from relational question banks to a 3D browser game [2]. In My Time also documents adding languages properly by building internationalisation at the foundation so adding a new language is a documented, repeatable process [3].
- **inmytime-06** ✅ What browser testing has Barry done?
  - Barry has done end-to-end browser testing with Playwright in the In My Time project [2], including tests that exercise real encryption and media playback [1]. He has also built automated browser test suites for In My Time [2].
- **brief-01** ✅ What is Brief?
  - Brief is a journaling app that asks users to write thirty words a week in response to prompts, creating a personal record of how they change over time [1]. It delivers prompts via WhatsApp or email [3], and users can scroll back through their archived entries, share with small groups, or seal entries as time capsules [4]. The app is private by default, with full data export and permanent deletion options [2], and is available as an installable web app at www.my30words.com [5].
- **brief-02** ✅ How did Barry handle a leaked credential incident?
  - Barry handled a credential-exposure incident in my30words by rotating every exposed secret (Google, Microsoft and Twilio) so the leaked values were dead, rebuilding the Git history as a single clean commit, and locking the repository down with a strict `.gitignore` for databases, configuration and backups. He took away the lesson that if a first commit ever contained a secret, the history should be reset rather than just untracking the file, and now applies this to every project.
- **brief-03** ✅ Why did weekly prompts drift off schedule, and how was it fixed?
  - In my30words, weekly prompts drifted off schedule because the system tracked each user's week position as a stored counter that could fall out of step, causing some users to receive prompts on an 8-day cycle instead of 7, and for others the cycle stalled. Barry rebuilt it so the week is calculated purely from time (from sign-up to now), eliminating the drift, and back-filled existing users with a one-off migration.
- **brief-04** ✅ How did Barry fix HTTPS certificates that would not validate?
  - Barry fixed HTTPS certificate validation issues by moving DNS to Cloudflare and setting the records to DNS-only mode. This solution was documented in both the In My Time and my30words projects, and he later reused the same fix on another project.
- **brief-05** ✅ What are time capsules in Brief?
  - In Brief, time capsules are a feature that allows users to seal an entry for 1, 5, or 10 years [1]. This enables users to preserve their journal entries and access them at a future date of their choosing.
- **askbarry-01** ✅ What is the Ask Barry project?
  - Ask Barry is a portfolio assistant that answers questions about Barry Sisk's software projects using only documentation from his public GitHub repositories, and cites the repository, file and section behind every answer [2]. It is intended for recruiters, interviewers and developers who want a quick, sourced answer about what Barry has built, as a starting point for reading the linked documentation [1]. The project is live at https://ask-barry-7dkz.onrender.com [2] and includes an MCP (Model Con
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
- **mcp-01** ✅ Which of Barry's projects include an MCP server?
  - Barry has built MCP servers in two projects. Ask Barry includes an MCP server (`ask_barry_mcp.py`) that lets Claude Desktop, Claude Code, Cursor or VS Code query the system as a tool [1]. Wall Inspector includes a Model Context Protocol Server (`mcp_server.py`) that exposes domain agents over JSON-RPC 2.0 for external LLM hosts like Claude, Gemini, and Cursor [2, 6].
- **askbarry-02** ✅ Has Barry deployed a RAG system to production?
  - Yes. Barry has deployed a retrieval-augmented generation (RAG) system to production in the Ask Barry project [1]. The system uses Azure AI Search for hybrid (keyword + vector) retrieval over his public repository documentation, and Azure OpenAI (gpt-4.1-mini) to write grounded answers with citations [1]. The RAG pipeline is live and includes answer-quality evaluation with an evidence-checking LLM judge [2].
