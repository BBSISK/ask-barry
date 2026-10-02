# Answer evaluation

Date: 2026-10-02 · Model: gpt-4.1-mini (azure-openai); judge gpt-4.1-mini · Retrieval: Azure hybrid, top 8 · Answerable: 39 · Traps: 8

| Metric | Value |
|---|---|
| Answered (answerable questions) | 100% |
| Answer cites a section containing the answer | 100% |
| Faithful to cited sources (LLM judge, of answered) | 95% |
| Answers with a true-but-uncited claim | 2 |
| Regression checks failed | 0 |
| **Traps: no false claim** | **100%** |
| Questions passing every check | 45 of 47 |

The judge is the same model family (gpt-4.1-mini), so the citation test and regression checks are deliberately deterministic. Sample sizes are small; one question is about 3 points.

## Failures and notes

### profile-07 (answerable)
- Answer: Barry has used Docker in multiple projects. The Wall Inspector project uses Docker Compose to run the full stack including a Flask web app and PostgreSQL 15 database (source 1). The system architecture for Wall Inspector includes a Docker container running Flask, Gunicorn, and other components (source 3). Additionally, Barry's featured projects list Docker as a technology used in Wall Inspector (s
- answered=True · cited_answer=True · faithful=False
- Unsupported claims: Barry has used Docker in multiple projects. (true but uncited: support is in a retrieved section the answer didn't cite)
- Sources: wall_inspector/README.md (🏛️ Global Wall Inspector — AI Masonry Diagnostic & Skills Certification Platform > 🛠️ Quick Start & Verification > 1. Run with Docker Compose (Full Stack: Web + PostgreSQL 15)); wall_inspector/README.md (🏛️ Global Wall Inspector — AI Masonry Diagnostic & Skills Certification Platform > 🏗️ System & DevOps Architecture); BBSISK/README.md (⚙️ How I build: from prompt to production in minutes); BBSISK/README.md (🛠️ Featured projects); BBSISK/README.md (🛠️ Featured projects)

### agentmath-03 (answerable)
- Answer: Agent of the Lost Numbers is a 3D, first-person history-of-maths adventure built in Three.js. It features a procedurally generated maze and a room-by-room journey from Mesopotamia to Egypt, with puzzles to solve. It is part of the AgentMath project, which is an adaptive, game-based maths platform for Irish Junior Cycle students.
- answered=True · cited_answer=True · faithful=False
- Unsupported claims: It is part of the AgentMath project, which is an adaptive, game-based maths platform for Irish Junior Cycle students. (true but uncited: support is in a retrieved section the answer didn't cite)
- Sources: agentmath_showcase/README.md (🕵️ AgentMath > What it does)

## All questions

| ID | Type | Pass | Supported | Sources cited |
|---|---|---|---|---|
| profile-01 | answerable | ✅ | True | 3 |
| profile-02 | answerable | ✅ | True | 2 |
| profile-03 | answerable | ✅ | True | 2 |
| profile-04 | answerable | ✅ | True | 2 |
| profile-05 | answerable | ✅ | True | 1 |
| profile-06 | answerable | ✅ | True | 1 |
| profile-07 | answerable | ❌ | True | 5 |
| profile-08 | answerable | ✅ | True | 4 |
| profile-09 | answerable | ✅ | True | 1 |
| profile-10 | answerable | ✅ | True | 7 |
| career-01 | answerable | ✅ | True | 5 |
| wall-01 | answerable | ✅ | True | 1 |
| wall-02 | answerable | ✅ | True | 1 |
| wall-03 | answerable | ✅ | True | 1 |
| wall-04 | answerable | ✅ | True | 2 |
| wall-05 | answerable | ✅ | True | 3 |
| wall-06 | answerable | ✅ | True | 1 |
| wall-07 | answerable | ✅ | True | 3 |
| wall-08 | answerable | ✅ | True | 3 |
| wall-09 | answerable | ✅ | True | 1 |
| agentmath-01 | answerable | ✅ | True | 2 |
| agentmath-02 | answerable | ✅ | True | 3 |
| agentmath-03 | answerable | ❌ | True | 1 |
| agentmath-04 | answerable | ✅ | True | 2 |
| agentmath-05 | answerable | ✅ | True | 1 |
| inmytime-01 | answerable | ✅ | True | 2 |
| inmytime-02 | answerable | ✅ | True | 1 |
| inmytime-03 | answerable | ✅ | True | 2 |
| inmytime-04 | answerable | ✅ | True | 1 |
| inmytime-05 | answerable | ✅ | True | 3 |
| inmytime-06 | answerable | ✅ | True | 2 |
| brief-01 | answerable | ✅ | True | 7 |
| brief-02 | answerable | ✅ | True | 1 |
| brief-03 | answerable | ✅ | True | 1 |
| brief-04 | answerable | ✅ | True | 2 |
| brief-05 | answerable | ✅ | True | 1 |
| askbarry-01 | answerable | ✅ | True | 5 |
| trap-01 | trap | ✅ | False | 0 |
| trap-02 | trap | ✅ | False | 0 |
| trap-03 | trap | ✅ | False | 0 |
| trap-04 | trap | ✅ | False | 0 |
| trap-05 | trap | ✅ | True | 1 |
| trap-06 | trap | ✅ | False | 0 |
| trap-07 | trap | ✅ | True | 2 |
| trap-09 | trap | ✅ | False | 0 |
| mcp-01 | answerable | ✅ | True | 3 |
| askbarry-02 | answerable | ✅ | True | 3 |

## All answers (for human review)

- **profile-01** ✅ Where did Barry work before becoming a software developer?
  - Before becoming a software developer, Barry worked for 30 years at Intel Ireland leading engineering teams in high-volume, tightly controlled manufacturing. Prior to Intel, he worked for 5 years at Schlumberger Industries, UK as a Process Engineer and Supplier Quality Engineer.
- **profile-02** ✅ What qualification is Barry studying for, and where?
  - Barry is completing a Higher Diploma in Software Development at Maynooth University.
- **profile-03** ✅ When is Barry available for full-time roles?
  - Barry is open to full-time roles from June 2027, after completing his Higher Diploma in Software Development at Maynooth University.
- **profile-04** ✅ Which AI coding agents does Barry use day to day?
  - Barry uses Claude Code and Google Antigravity as AI coding agents every day in his development work.
- **profile-05** ✅ Describe Barry's workflow from prompt to production.
  - Barry's workflow starts with describing the change to an AI coding agent in VS Code, which writes the code and tests. He then reviews the diff and runs tests locally. After that, he pushes the change to GitHub, where a CI pipeline runs the full test suite on a clean Linux runner. Only if all tests pass does Render auto-deploy the Docker container to production, ensuring no defects reach users. This process takes about two minutes from idea to live and includes quality gates at every step.
- **profile-06** ✅ Which programming languages does Barry know?
  - Barry knows Python, Java, SQL, JavaScript, and HTML/CSS as programming languages.
- **profile-07** ❌ Has Barry used Docker?
  - Barry has used Docker in multiple projects. The Wall Inspector project uses Docker Compose to run the full stack including a Flask web app and PostgreSQL 15 database (source 1). The system architecture for Wall Inspector includes a Docker container running Flask, Gunicorn, and other components (source 3). Additionally, Barry's featured projects list Docker as a technology used in Wall Inspector (sources 5 and 6). The CI/CD pipeline described in the BBSISK repo also deploys Docker containers auto
- **profile-08** ✅ What cloud and DevOps tools has Barry worked with?
  - Barry has worked with Docker, Terraform, GitHub Actions, Render, Microsoft Azure, Cloudflare, and Cloudinary as cloud and DevOps tools. He uses Terraform for infrastructure as code and GitHub Actions for CI/CD pipelines. His projects include Azure resources managed with Terraform and Docker containerization for application deployment. These tools are used across projects such as Global Wall Inspector and Ask Barry.
- **profile-09** ✅ How can I contact Barry?
  - Barry can be contacted by email at barry.b.sisk@gmail.com or via LinkedIn at https://www.linkedin.com/in/barry-s-50135113/
- **profile-10** ✅ What cloud tools has Barry used?
  - Barry has used Microsoft Azure extensively, including Azure OpenAI, Azure AI Search, and Azure Cognitive Services, managed with Terraform and integrated with GitHub Actions for CI/CD in the Ask Barry project. He also uses Docker and Render for deployment, Cloudflare and Cloudinary for CDN and image hosting, and PostgreSQL and SQLite for data storage. In the Wall Inspector project, he uses Google Gemini Vision API and Cloudinary CDN. His infrastructure as code includes Azure resource groups, cogn
- **career-01** ✅ What leadership roles did Barry hold at Intel?
  - Barry held multiple leadership roles at Intel Ireland, including 300mm CMP Group Leader (July 2009 – September 2016), 200mm CMP Group Leader (April 2008 – July 2009), CVD Group Leader (April 2005 – April 2008), and 300mm Implant Group Leader (October 2016 – August 2019). He also led teams in high-volume manufacturing across various semiconductor technologies and managed a multinational team for equipment sales. Earlier, he was a Process Quality Team Lead and led a four-shift team of technicians 
- **wall-01** ✅ What is Wall Inspector and who is it for?
  - Wall Inspector is a clinical skills-assessment and certification platform designed for civil engineering, heritage conservation, and masonry construction students and assessors. It enables interactive diagnostics of masonry defects using high-resolution photographs, allowing students to inspect walls, classify defects, and prescribe remedies that are graded in real time against expert ground-truth data. The platform addresses limitations of traditional masonry training by providing objective, in
- **wall-02** ✅ What does the Intake Sentinel agent check in uploaded photographs?
  - The Intake Sentinel agent evaluates newly uploaded field photographs across four photogrammetric pillars: 90° orthogonal plane, diffuse illumination, course framing, and Laplacian focus sharpness.
- **wall-03** ✅ Which tools does the Wall Inspector MCP server expose?
  - The Wall Inspector MCP server exposes the platform's domain agents over JSON-RPC 2.0 for external LLM hosts. These agents include `sentinel_evaluate_image`, `curriculum_cohort_intelligence`, `list_skill_specimens`, and `export_coco_dataset_stats`.
- **wall-04** ✅ How does human-in-the-loop provenance tracking work in Wall Inspector?
  - In Wall Inspector, human-in-the-loop provenance tracking uses a 3-tier audit lineage for defect pins: 'auto_suggested' when Gemini Vision AI proposes defects on upload (unverified), 'auto_accepted' when an assessor reviews, adjusts, and saves the AI proposal with name and timestamp auditing (verified), and 'human_graded' when an assessor marks all defects from scratch as gold-standard benchmarks. Each defect pin includes a confidence score, and the assessor queue can be filtered by lineage to bu
- **wall-05** ✅ What dataset format does Wall Inspector export for computer vision tools?
  - Wall Inspector exports datasets in the Microsoft COCO 1.0 JSON format for downstream computer vision training with tools like CVAT and YOLOv8.
- **wall-06** ✅ How many automated tests does Wall Inspector run?
  - Wall Inspector runs 86 automated unit and agent tests.
- **wall-07** ✅ Which database does Wall Inspector use in production?
  - Wall Inspector uses a managed PostgreSQL 15 database in production, connected via the DATABASE_URL environment variable.
- **wall-08** ✅ Has Barry used Terraform for infrastructure as code?
  - Barry has used Terraform for infrastructure as code in multiple projects. In the Ask Barry project, Terraform describes and imports Azure resources such as resource groups, Azure AI services, and Azure AI Search, ensuring no resources are recreated and maintaining safe configurations. In the Global Wall Inspector project, Terraform is part of the infrastructure as code and CI/CD setup managing the application container and cloud resources. These uses are documented with specific Terraform files 
- **wall-09** ✅ How are credentials and secrets handled in Wall Inspector?
  - In Wall Inspector, all credentials and cloud endpoints are injected strictly via environment variables and never hardcoded. These include the PostgreSQL connection string, Cloudinary CDN key, Google Gemini Vision API key, assessor workstation credentials, and a cryptographic session signing key. This approach ensures that sensitive information is managed securely outside the codebase.
- **agentmath-01** ✅ How many assessment items does AgentMath have?
  - AgentMath has over 3,000 curriculum-aligned assessment items.
- **agentmath-02** ✅ How does AgentMath protect children's privacy?
  - AgentMath protects children's privacy by allowing students to use the platform without providing personal data through three access methods: Quick Try with no registration, anonymous guest codes that track progress without collecting names or emails, and optional Google or Microsoft sign-in using existing school accounts. It also supports guest-to-account progress transfer so students do not lose progress when they later sign in properly. The design is explicitly privacy-conscious for children, 
- **agentmath-03** ❌ What is Agent of the Lost Numbers?
  - Agent of the Lost Numbers is a 3D, first-person history-of-maths adventure built in Three.js. It features a procedurally generated maze and a room-by-room journey from Mesopotamia to Egypt, with puzzles to solve. It is part of the AgentMath project, which is an adaptive, game-based maths platform for Irish Junior Cycle students.
- **agentmath-04** ✅ What technology stack is AgentMath built with?
  - AgentMath is built with a backend using Python and Flask, with SQLite for data storage including question bank and student progress. The front end uses HTML, CSS, JavaScript, and Three.js for 3D modules. It supports identity management via Google OAuth, Microsoft OAuth (Azure app registration), and anonymous guest codes. The platform is delivered as a Progressive Web App hosted on PythonAnywhere, with development assisted by AI tools like Claude.
- **agentmath-05** ✅ What gamification features keep AgentMath students engaged?
  - AgentMath includes gamification features such as badges, avatars, leaderboards, and a Points for Prizes reward system to keep students engaged.
- **inmytime-01** ✅ Does In My Time store the family stories it collects?
  - In My Time does not store the family stories it collects. The server relays each answer in the same request and stores nothing, keeping no message text or transcriptions. The database schema has no column capable of holding an answer, and only timestamps and the author's position in the question sequence are recorded. Even the admin view shows only progress metrics, never story content.
- **inmytime-02** ✅ How does In My Time get the grandparent's consent?
  - In My Time obtains the grandparent's consent by sending them a single WhatsApp consent message, and nothing starts until the grandparent (the author) replies to that message, ensuring consent is in their hands.
- **inmytime-03** ✅ What is StoryCatcher?
  - StoryCatcher is a module within the In My Time project that allows family members to record interviews with relatives directly in the browser. It features guided interviews using curated question packs, client-side encryption for recordings and names with per-interviewee keys, per-interviewee access control enforced server-side, photo capture during recordings, and bring-your-own storage options such as Cloudflare R2 or Google Drive. It also includes a LifeLine feature, a scrollable timeline whe
- **inmytime-04** ✅ Why were admin WhatsApp alerts failing silently, and how was it fixed?
  - Admin WhatsApp alerts failed silently because WhatsApp's 24-hour session rule only delivers free-form messages while a conversation is open. The fix was to add an automatic fallback to a pre-approved template message, with tests covering both the free-form and template message paths.
- **inmytime-05** ✅ Has Barry built multilingual or internationalised software?
  - Barry built internationalisation at the foundation of the In My Time project, enabling adding new languages as a documented, repeatable process. This shows he has implemented multilingual or internationalised software in that project.
- **inmytime-06** ✅ What browser testing has Barry done?
  - Barry has done browser testing that exercises real encryption and media playback, as part of the In My Time project. These are automated end-to-end Playwright browser tests that include recording and playback to ensure thorough testing of the application's encryption and media features.
- **brief-01** ✅ What is Brief?
  - Brief is a journaling app designed to ask users for only thirty words a week as a snapshot of their current state, enabling them to track personal change over months and years. It features a 16-week prompt cycle with anchor and texture questions, supports groups and anonymous public feeds, and offers privacy-first data handling with full export and permanent deletion. Users receive prompts via WhatsApp or email and can interact through an installable web app with Google, Microsoft, or email sign
- **brief-02** ✅ How did Barry handle a leaked credential incident?
  - Barry handled a leaked credential incident by rotating every exposed secret (Google, Microsoft, and Twilio), rebuilding the Git history as a single clean commit, and locking the repository down with a strict .gitignore for databases, configuration, and backups. He learned to reset the history rather than just untracking the file if a first commit ever contained a secret.
- **brief-03** ✅ Why did weekly prompts drift off schedule, and how was it fixed?
  - Weekly prompts drifted off schedule because the system tracked each user's week position as a stored counter that could fall out of step, causing some users to receive prompts on an 8-day cycle instead of 7 or for the prompt cycle to stall. Barry fixed this by rebuilding the system so the week is calculated purely from time (from sign-up to now), eliminating the possibility of schedule drift. He also back-filled existing users with a one-off migration to align their schedules.
- **brief-04** ✅ How did Barry fix HTTPS certificates that would not validate?
  - Barry fixed HTTPS certificate validation failures caused by the registrar's DNS record setup by moving the DNS to Cloudflare and setting the records to DNS-only. This solution was applied in both the In My Time and my30words projects.
- **brief-05** ✅ What are time capsules in Brief?
  - In Brief, time capsules are a feature that allows users to seal an entry for 1, 5, or 10 years, effectively locking it away for that period before it can be accessed again.
- **askbarry-01** ✅ What is the Ask Barry project?
  - Barry has built Ask Barry, an AI assistant that answers questions about his software projects using only the README and documentation files in his public GitHub repositories, citing the repository, file, and section behind every answer. It is a retrieval-augmented generation (RAG) assistant that fetches public READMEs and docs nightly, splits them into sections, embeds them, and indexes them in Azure AI Search for hybrid retrieval. The system uses a GPT-4.1-mini model to generate answers with so
- **trap-01** ✅ Has Barry used Kubernetes?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-02** ✅ Does Barry have AWS experience?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-03** ✅ Has Barry built native mobile apps in Swift or Kotlin?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-04** ✅ Has Barry built front ends with React?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-05** ✅ Does Barry have a PhD?
  - Barry does not have a PhD. His highest completed degree is a B.Eng. in Production Engineering with First Class Honours from the University of Limerick (1985–1989). He is currently pursuing a Higher Diploma in Software Development at Maynooth University (2026–2027). (judge: The answer explicitly states Barry does not have a PhD and only lists his completed degrees.)
- **trap-06** ✅ Has Barry used MongoDB?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-07** ✅ Has Barry trained a YOLOv8 model?
  - Barry's Global Wall Inspector project exports labeled datasets in Microsoft COCO 1.0 JSON format specifically for YOLOv8-Seg pipelines, indicating preparation of data for YOLOv8 model training. However, the sources do not explicitly state that Barry has trained a YOLOv8 model himself. (judge: The answer states Barry prepares data for YOLOv8 training but does not explicitly say he has trained a YOLOv8 model himself.)
- **trap-09** ✅ Has Barry worked with Apache Kafka?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **mcp-01** ✅ Which of Barry's projects include an MCP server?
  - Barry's projects that include an MCP server are Ask Barry and Wall Inspector. Ask Barry has an MCP server implemented in the file ask_barry_mcp.py, which serves as a Model Context Protocol server tool for AI assistants (source 1). Wall Inspector includes an MCP server component in its architecture, specifically the file mcp_server.py, as part of its AI agents and containerized application (sources 4 and 6).
- **askbarry-02** ✅ Has Barry deployed a RAG system to production?
  - Barry has deployed a retrieval-augmented generation (RAG) system called Ask Barry to production. It uses Azure AI Search with hybrid keyword and vector retrieval over his public repo documentation, and Azure OpenAI's gpt-4.1-mini to generate answers with citations. The system includes a Flask app with CI and Render deployment, nightly index refresh, answer-quality evaluation with AI judges, and a job-ad evidence agent, all live and evaluated in production.
