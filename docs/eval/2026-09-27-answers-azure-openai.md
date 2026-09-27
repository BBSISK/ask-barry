# Answer evaluation

Date: 2026-09-27 · Model: gpt-4.1-mini (azure-openai); judge gpt-4.1-mini · Retrieval: Azure hybrid, top 8 · Answerable: 38 · Traps: 8

| Metric | Value |
|---|---|
| Answered (answerable questions) | 100% |
| Answer cites a section containing the answer | 100% |
| Faithful to cited sources (LLM judge, of answered) | 92% |
| Answers with a true-but-uncited claim | 3 |
| Regression checks failed | 0 |
| **Traps: no false claim** | **100%** |
| Questions passing every check | 43 of 46 |

The judge is the same model family (gpt-4.1-mini), so the citation test and regression checks are deliberately deterministic. Sample sizes are small; one question is about 3 points.

## Failures and notes

### agentmath-03 (answerable)
- Answer: Agent of the Lost Numbers is a 3D, first-person history-of-maths adventure built in Three.js, featuring a procedurally generated maze and a room-by-room journey from Mesopotamia to Egypt with puzzles to solve. It is part of the AgentMath project, which is an adaptive, game-based maths platform for Irish Junior Cycle students. This feature demonstrates the breadth of the project, combining a relati
- answered=True · cited_answer=True · faithful=False
- Unsupported claims: Agent of the Lost Numbers is part of the AgentMath project, which is an adaptive, game-based maths platform for Irish Junior Cycle students. (true but uncited: support is in a retrieved section the answer didn't cite)
- Sources: agentmath_showcase/README.md (🕵️ AgentMath > What it does); agentmath_showcase/README.md (🕵️ AgentMath > What this project demonstrates)

### inmytime-06 (answerable)
- Answer: Barry has done browser testing that exercises real encryption and media playback in the In My Time project, including automated end-to-end Playwright browser tests. This testing is part of a privacy-first architecture ensuring client-side encryption and per-user access control. The tests are designed to cover real-world scenarios involving messaging platforms and sensitive user data. This is docum
- answered=True · cited_answer=True · faithful=False
- Unsupported claims: This is documented specifically in the In My Time project. (true but uncited: support is in a retrieved section the answer didn't cite)
- Sources: inmytime-showcase/README.md (🌸 In My Time > What this project demonstrates); inmytime-showcase/README.md (🌸 In My Time > Tech stack)

### askbarry-01 (answerable)
- Answer: Ask Barry is an AI assistant that answers questions about Barry Sisk's software projects using only the README and documentation files in his public GitHub repositories. It provides answers with citations to the exact repository, file, and section, designed for recruiters, interviewers, and developers as a starting point to understand Barry's work. It is not intended for ranking, scoring, filterin
- answered=True · cited_answer=True · faithful=False
- Unsupported claims: It includes honesty controls to avoid unsupported claims. (true but uncited: support is in a retrieved section the answer didn't cite)
- Sources: ask-barry/docs/model-card.md (Ask Barry: model card > What it is); ask-barry/README.md (Ask Barry); ask-barry/docs/model-card.md (Ask Barry: model card)

## All questions

| ID | Type | Pass | Supported | Sources cited |
|---|---|---|---|---|
| profile-01 | answerable | ✅ | True | 1 |
| profile-02 | answerable | ✅ | True | 2 |
| profile-03 | answerable | ✅ | True | 1 |
| profile-04 | answerable | ✅ | True | 2 |
| profile-05 | answerable | ✅ | True | 1 |
| profile-06 | answerable | ✅ | True | 1 |
| profile-07 | answerable | ✅ | True | 4 |
| profile-08 | answerable | ✅ | True | 3 |
| profile-09 | answerable | ✅ | True | 1 |
| profile-10 | answerable | ✅ | True | 5 |
| wall-01 | answerable | ✅ | True | 1 |
| wall-02 | answerable | ✅ | True | 1 |
| wall-03 | answerable | ✅ | True | 1 |
| wall-04 | answerable | ✅ | True | 2 |
| wall-05 | answerable | ✅ | True | 2 |
| wall-06 | answerable | ✅ | True | 1 |
| wall-07 | answerable | ✅ | True | 3 |
| wall-08 | answerable | ✅ | True | 3 |
| wall-09 | answerable | ✅ | True | 1 |
| agentmath-01 | answerable | ✅ | True | 2 |
| agentmath-02 | answerable | ✅ | True | 3 |
| agentmath-03 | answerable | ❌ | True | 2 |
| agentmath-04 | answerable | ✅ | True | 2 |
| agentmath-05 | answerable | ✅ | True | 1 |
| inmytime-01 | answerable | ✅ | True | 3 |
| inmytime-02 | answerable | ✅ | True | 1 |
| inmytime-03 | answerable | ✅ | True | 2 |
| inmytime-04 | answerable | ✅ | True | 1 |
| inmytime-05 | answerable | ✅ | True | 3 |
| inmytime-06 | answerable | ❌ | True | 2 |
| brief-01 | answerable | ✅ | True | 7 |
| brief-02 | answerable | ✅ | True | 1 |
| brief-03 | answerable | ✅ | True | 1 |
| brief-04 | answerable | ✅ | True | 2 |
| brief-05 | answerable | ✅ | True | 1 |
| askbarry-01 | answerable | ❌ | True | 3 |
| trap-01 | trap | ✅ | False | 0 |
| trap-02 | trap | ✅ | False | 0 |
| trap-03 | trap | ✅ | False | 0 |
| trap-04 | trap | ✅ | False | 0 |
| trap-05 | trap | ✅ | True | 1 |
| trap-06 | trap | ✅ | False | 0 |
| trap-07 | trap | ✅ | True | 2 |
| trap-09 | trap | ✅ | False | 0 |
| mcp-01 | answerable | ✅ | True | 4 |
| askbarry-02 | answerable | ✅ | True | 3 |

## All answers (for human review)

- **profile-01** ✅ Where did Barry work before becoming a software developer?
  - Barry worked for 30 years at Intel Ireland leading engineering teams in high-volume, tightly controlled manufacturing before becoming a software developer.
- **profile-02** ✅ What qualification is Barry studying for, and where?
  - Barry is completing a Higher Diploma in Software Development at Maynooth University, expected in 2027.
- **profile-03** ✅ When is Barry available for full-time roles?
  - Barry is open to full-time roles from June 2027.
- **profile-04** ✅ Which AI coding agents does Barry use day to day?
  - Barry uses Claude Code and Google Antigravity AI coding agents daily in VS Code, integrating them into his development workflow to write code and tests alongside prompts.
- **profile-05** ✅ Describe Barry's workflow from prompt to production.
  - Barry's workflow from prompt to production involves describing the change to an AI coding agent in VS Code, which writes the code and tests. He then reviews the diff and runs tests locally. After pushing to GitHub, a CI pipeline runs the full test suite on a clean Linux runner. Deployment to production via Render happens automatically only if all tests pass, ensuring no defects reach users. This process takes about two minutes and includes quality gates at every step.
- **profile-06** ✅ Which programming languages does Barry know?
  - Barry knows Python, Java, SQL, JavaScript, and HTML/CSS as programming languages.
- **profile-07** ✅ Has Barry used Docker?
  - Barry has used Docker in multiple projects. The Wall Inspector project runs as a full stack application with Docker Compose, including web and PostgreSQL services. Docker is also part of the system architecture with containerized Flask and AI agent components. Additionally, Barry uses Docker in his development and deployment pipeline, with automatic deployment of Docker containers via Render.
- **profile-08** ✅ What cloud and DevOps tools has Barry worked with?
  - Barry has worked with Docker, Terraform, GitHub Actions, Render, Cloudflare, and Cloudinary as cloud and DevOps tools in his projects. These are used in the Global Wall Inspector project for infrastructure as code, CI/CD, containerization, and cloud storage. Additionally, in the In My Time project, Cloudflare DNS and GitHub are part of the infrastructure stack.
- **profile-09** ✅ How can I contact Barry?
  - Barry can be contacted via email at barry.b.sisk@gmail.com or through his LinkedIn profile at https://www.linkedin.com/in/barry-s-50135113/
- **profile-10** ✅ What cloud tools has Barry used?
  - Barry has used Microsoft Azure services including Azure OpenAI for embeddings and chat models, and Azure AI Search for hybrid keyword and vector search, as part of the Ask Barry project. He uses Terraform for infrastructure as code and GitHub Actions for CI/CD in the Global Wall Inspector project. Cloud services also include Cloudinary CDN for uncompressed photos and managed PostgreSQL 15 for database storage. Additionally, Barry employs Docker containers for application deployment and integrate
- **wall-01** ✅ What is Wall Inspector and who is it for?
  - Wall Inspector is a clinical skills-assessment and certification platform designed for civil engineering, heritage conservation, and masonry construction students and assessors. It enables interactive diagnostics of masonry defects using high-resolution photographs, allowing students to inspect walls, classify defects, and prescribe remedies that are graded in real time against expert ground truth. The platform addresses limitations of traditional masonry training by providing objective, interac
- **wall-02** ✅ What does the Intake Sentinel agent check in uploaded photographs?
  - The Intake Sentinel agent evaluates newly uploaded field photographs across four photogrammetric pillars: 90° orthogonal plane, diffuse illumination, course framing, and Laplacian focus sharpness.
- **wall-03** ✅ Which tools does the Wall Inspector MCP server expose?
  - The Wall Inspector MCP server exposes the platform's domain agents over JSON-RPC 2.0 for external LLM hosts. These tools include `sentinel_evaluate_image`, `curriculum_cohort_intelligence`, `list_skill_specimens`, and `export_coco_dataset_stats`.
- **wall-04** ✅ How does human-in-the-loop provenance tracking work in Wall Inspector?
  - In Wall Inspector, human-in-the-loop provenance tracking uses a 3-tier audit lineage for defect pins proposed by the AI. Initially, Gemini Vision proposes defect pins tagged as `auto_suggested` (unverified). An assessor then reviews, adjusts, and saves these proposals, upgrading them to `auto_accepted` with the assessor's name and timestamp recorded. Alternatively, assessors can mark defects from scratch, which are labeled `human_graded` and serve as gold-standard benchmarks. Each defect pin als
- **wall-05** ✅ What dataset format does Wall Inspector export for computer vision tools?
  - Wall Inspector exports datasets in the Microsoft COCO 1.0 JSON format for downstream computer vision training with tools like CVAT and YOLOv8.
- **wall-06** ✅ How many automated tests does Wall Inspector run?
  - Wall Inspector runs 86 automated unit and agent tests.
- **wall-07** ✅ Which database does Wall Inspector use in production?
  - Wall Inspector uses a managed PostgreSQL 15 database in production, connected via the DATABASE_URL environment variable.
- **wall-08** ✅ Has Barry used Terraform for infrastructure as code?
  - Barry has used Terraform for infrastructure as code in the Global Wall Inspector project, as shown by the presence of Terraform files (infra/main.tf) and its integration in the system architecture. Additionally, Terraform is mentioned as part of the infrastructure setup in the Azure setup guide for Ask Barry, with plans to codify Azure resources using Terraform.
- **wall-09** ✅ How are credentials and secrets handled in Wall Inspector?
  - In Wall Inspector, all credentials and cloud endpoints are injected strictly via environment variables and never hardcoded. These include the PostgreSQL connection string, Cloudinary CDN key, Google Gemini Vision API key, assessor workstation credentials, and a cryptographic session signing key. This approach ensures that sensitive information is managed securely outside the codebase.
- **agentmath-01** ✅ How many assessment items does AgentMath have?
  - AgentMath has over 3,000 curriculum-aligned assessment items.
- **agentmath-02** ✅ How does AgentMath protect children's privacy?
  - AgentMath protects children's privacy by allowing use without collecting personal data through three access methods: Quick Try with no registration, anonymous guest codes that track progress without names or emails, and optional Google or Microsoft sign-in using existing school accounts. It also supports guest-to-account progress transfer to avoid data loss when students sign in later. The platform is designed specifically with children's privacy in mind, enabling full use without requiring pers
- **agentmath-03** ❌ What is Agent of the Lost Numbers?
  - Agent of the Lost Numbers is a 3D, first-person history-of-maths adventure built in Three.js, featuring a procedurally generated maze and a room-by-room journey from Mesopotamia to Egypt with puzzles to solve. It is part of the AgentMath project, which is an adaptive, game-based maths platform for Irish Junior Cycle students. This feature demonstrates the breadth of the project, combining a relational question bank and dashboards with a 3D browser game experience.
- **agentmath-04** ✅ What technology stack is AgentMath built with?
  - AgentMath is built with a backend using Python and Flask, with SQLite for data storage including question bank and student progress. The front end uses HTML, CSS, JavaScript, and Three.js for 3D modules. It supports identity via Google OAuth, Microsoft OAuth (Azure app registration), and anonymous guest codes. The platform is delivered as a Progressive Web App hosted on PythonAnywhere, with development assisted by AI tools like Claude.
- **agentmath-05** ✅ What gamification features keep AgentMath students engaged?
  - AgentMath includes gamification features such as badges, avatars, leaderboards, and a Points for Prizes reward system to keep students engaged.
- **inmytime-01** ✅ Does In My Time store the family stories it collects?
  - In My Time does not store the family stories it collects. The server relays each answer in the same request and stores nothing, keeping no message text or transcriptions. The database only stores timestamps and the author's position in the question sequence, with no column capable of holding an answer. Even the admin view never shows story content, only progress metrics.
- **inmytime-02** ✅ How does In My Time get the grandparent's consent?
  - In My Time obtains the grandparent's consent by sending them a single WhatsApp consent message, and nothing starts until the grandparent replies to that message, ensuring the consent is in their hands.
- **inmytime-03** ✅ What is StoryCatcher?
  - StoryCatcher is a module within the In My Time project that enables family members to record interviews with relatives directly in the browser. It features guided interviews using curated question packs, client-side encryption for recordings and names, per-interviewee access control enforced server-side, photo capture during recordings, and flexible storage options including Cloudflare R2 or Google Drive. It also includes a LifeLine timeline that pins clips and notes to decades and themes alongs
- **inmytime-04** ✅ Why were admin WhatsApp alerts failing silently, and how was it fixed?
  - Admin WhatsApp alerts were failing silently because WhatsApp's 24-hour session rule only delivers free-form messages while a conversation is open. The fix was to add an automatic fallback to a pre-approved template message, with tests covering both the free-form and template message paths.
- **inmytime-05** ✅ Has Barry built multilingual or internationalised software?
  - Barry built internationalisation at the foundation of the In My Time project, enabling adding new languages through a documented, repeatable process. This approach was implemented to properly add languages rather than translating page by page.
- **inmytime-06** ❌ What browser testing has Barry done?
  - Barry has done browser testing that exercises real encryption and media playback in the In My Time project, including automated end-to-end Playwright browser tests. This testing is part of a privacy-first architecture ensuring client-side encryption and per-user access control. The tests are designed to cover real-world scenarios involving messaging platforms and sensitive user data. This is documented specifically in the In My Time project.
- **brief-01** ✅ What is Brief?
  - Brief is a journaling app designed to ask users for only thirty words a week as a snapshot of their current state, helping them build a personal record over time. It features a 16-week prompt cycle with anchor and texture questions, supports groups and anonymous public feeds, and offers privacy-first data handling with full export and permanent deletion. Users receive prompts via WhatsApp or email and can scroll back through their timeline to see how they have changed. The app is a Progressive W
- **brief-02** ✅ How did Barry handle a leaked credential incident?
  - Barry handled a leaked credential incident by rotating every exposed secret (Google, Microsoft, and Twilio), rebuilding the Git history as a single clean commit, and locking the repository down with a strict .gitignore for databases, configuration, and backups. He learned to reset the history rather than just untracking files if a first commit ever contained a secret.
- **brief-03** ✅ Why did weekly prompts drift off schedule, and how was it fixed?
  - Weekly prompts drifted off schedule because the system tracked each user's week position as a stored counter that could fall out of step, causing some users to receive prompts on an 8-day cycle instead of 7 or for the prompt cycle to stall. Barry fixed this by rebuilding the system so the week is calculated purely from time (from sign-up to now), eliminating the possibility of schedule drift. He also back-filled existing users with a one-off migration to align their schedules.
- **brief-04** ✅ How did Barry fix HTTPS certificates that would not validate?
  - Barry fixed HTTPS certificate validation failures caused by the registrar's DNS setup by moving DNS to Cloudflare and setting the records to DNS-only. This solution was applied in the In My Time project and later reused in the my30words project.
- **brief-05** ✅ What are time capsules in Brief?
  - In Brief, time capsules are a feature that allows users to seal an entry for 1, 5, or 10 years, effectively locking the content for that duration before it can be accessed again.
- **askbarry-01** ❌ What is the Ask Barry project?
  - Ask Barry is an AI assistant that answers questions about Barry Sisk's software projects using only the README and documentation files in his public GitHub repositories. It provides answers with citations to the exact repository, file, and section, designed for recruiters, interviewers, and developers as a starting point to understand Barry's work. It is not intended for ranking, scoring, filtering, or making hiring decisions. The system is live and includes honesty controls to avoid unsupported
- **trap-01** ✅ Has Barry used Kubernetes?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-02** ✅ Does Barry have AWS experience?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-03** ✅ Has Barry built native mobile apps in Swift or Kotlin?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-04** ✅ Has Barry built front ends with React?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-05** ✅ Does Barry have a PhD?
  - Barry is completing a Higher Diploma in Software Development at Maynooth University, expected in 2027. There is no mention of a PhD in the provided sources. (judge: The answer explicitly states there is no mention of a PhD and only mentions a Higher Diploma in progress.)
- **trap-06** ✅ Has Barry used MongoDB?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-07** ✅ Has Barry trained a YOLOv8 model?
  - Barry's Global Wall Inspector project exports labeled datasets in Microsoft COCO 1.0 JSON format for downstream Computer Vision training pipelines including YOLOv8-Seg. This indicates Barry has prepared data for YOLOv8 training, but the sources do not explicitly state that Barry has trained a YOLOv8 model himself. (judge: The answer states Barry has prepared data for YOLOv8 training but does not explicitly claim he has trained a YOLOv8 model himself.)
- **trap-09** ✅ Has Barry worked with Apache Kafka?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **mcp-01** ✅ Which of Barry's projects include an MCP server?
  - Barry's projects that include an MCP server are Ask Barry and Wall Inspector. Ask Barry has an MCP server implemented in ask_barry_mcp.py to allow AI assistants to query it as a tool. Wall Inspector includes an MCP server (mcp_server.py) exposing platform domain agents over JSON-RPC 2.0 for external LLM hosts.
- **askbarry-02** ✅ Has Barry deployed a RAG system to production?
  - Barry has deployed a retrieval-augmented generation (RAG) system to production in the Ask Barry project. It uses Azure AI Search for hybrid keyword and vector retrieval over his public repo documentation, and Azure OpenAI's gpt-4.1-mini to generate answers with citations. The system enforces citation checks and refuses answers without valid citations, and it is live with nightly index refresh and answer quality evaluation. The deployment includes a Flask app with CI and Render deployment, with a
