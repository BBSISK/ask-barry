# Answer evaluation

Date: 2026-10-03 · Model: eu.amazon.nova-2-lite-v1:0 (bedrock-nova); judge gpt-4.1-mini · Retrieval: Azure hybrid, top 8 · Answerable: 39 · Traps: 8

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
- Answer: Barry has used Docker in multiple projects. In the Global Wall Inspector project, Docker Compose is used for running the full stack application with PostgreSQL 15, and the system architecture includes a Docker container for the Flask application with Gunicorn, Sentinel and Director agents, and an MCP server. The BBSISK project also lists Docker among its technologies, and its build process uses Re
- answered=True · cited_answer=True · faithful=False
- Unsupported claims: Barry has used Docker in multiple projects. (true but uncited: support is in a retrieved section the answer didn't cite)
- Sources: wall_inspector/README.md (🏛️ Global Wall Inspector — AI Masonry Diagnostic & Skills Certification Platform > 🛠️ Quick Start & Verification > 1. Run with Docker Compose (Full Stack: Web + PostgreSQL 15)); BBSISK/README.md (🧰 Toolbox); wall_inspector/README.md (🏛️ Global Wall Inspector — AI Masonry Diagnostic & Skills Certification Platform > 🏗️ System & DevOps Architecture); BBSISK/README.md (⚙️ How I build: from prompt to production in minutes)

### inmytime-05 (answerable)
- Answer: Barry has built multilingual or internationalised software in two projects. In In My Time, he built internationalisation at the foundation to allow adding new languages as a documented, repeatable process. In Brief, he implemented German localisation.
- answered=True · cited_answer=True · faithful=False
- Unsupported claims: In Brief, Barry implemented German localisation. (true but uncited: support is in a retrieved section the answer didn't cite)
- Sources: inmytime-showcase/README.md (🌸 In My Time > What this project demonstrates); inmytime-showcase/README.md (🌸 In My Time > Problems I solved along the way)

## All questions

| ID | Type | Pass | Supported | Sources cited |
|---|---|---|---|---|
| profile-01 | answerable | ✅ | True | 3 |
| profile-02 | answerable | ✅ | True | 1 |
| profile-03 | answerable | ✅ | True | 1 |
| profile-04 | answerable | ✅ | True | 2 |
| profile-05 | answerable | ✅ | True | 1 |
| profile-06 | answerable | ✅ | True | 1 |
| profile-07 | answerable | ❌ | True | 4 |
| profile-08 | answerable | ✅ | True | 4 |
| profile-09 | answerable | ✅ | True | 2 |
| profile-10 | answerable | ✅ | True | 5 |
| career-01 | answerable | ✅ | True | 2 |
| wall-01 | answerable | ✅ | True | 2 |
| wall-02 | answerable | ✅ | True | 2 |
| wall-03 | answerable | ✅ | True | 1 |
| wall-04 | answerable | ✅ | True | 2 |
| wall-05 | answerable | ✅ | True | 2 |
| wall-06 | answerable | ✅ | True | 1 |
| wall-07 | answerable | ✅ | True | 4 |
| wall-08 | answerable | ✅ | True | 3 |
| wall-09 | answerable | ✅ | True | 1 |
| agentmath-01 | answerable | ✅ | True | 1 |
| agentmath-02 | answerable | ✅ | True | 2 |
| agentmath-03 | answerable | ✅ | True | 1 |
| agentmath-04 | answerable | ✅ | True | 3 |
| agentmath-05 | answerable | ✅ | True | 1 |
| inmytime-01 | answerable | ✅ | True | 4 |
| inmytime-02 | answerable | ✅ | True | 2 |
| inmytime-03 | answerable | ✅ | True | 1 |
| inmytime-04 | answerable | ✅ | True | 1 |
| inmytime-05 | answerable | ❌ | True | 2 |
| inmytime-06 | answerable | ✅ | True | 2 |
| brief-01 | answerable | ✅ | True | 3 |
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
| trap-07 | trap | ✅ | True | 1 |
| trap-09 | trap | ✅ | False | 0 |
| mcp-01 | answerable | ✅ | True | 4 |
| askbarry-02 | answerable | ✅ | True | 5 |

## All answers (for human review)

- **profile-01** ✅ Where did Barry work before becoming a software developer?
  - Barry worked at Intel Ireland for 30 years leading engineering teams in high-volume, tightly controlled manufacturing, and before that at Schlumberger Industries in the UK for 5 years as a Process Engineer and Supplier Quality Engineer.
- **profile-02** ✅ What qualification is Barry studying for, and where?
  - Barry is completing a Higher Diploma in Software Development at Maynooth University.
- **profile-03** ✅ When is Barry available for full-time roles?
  - Barry is available for full-time roles from June 2027.
- **profile-04** ✅ Which AI coding agents does Barry use day to day?
  - Barry uses Claude Code and Google Antigravity as AI coding agents every day.
- **profile-05** ✅ Describe Barry's workflow from prompt to production.
  - Barry's workflow from prompt to production involves several key steps: first, an AI coding agent in VS Code generates code and tests based on a prompt. Barry then reviews the changes and runs tests locally. After review, he pushes the changes to GitHub, triggering a CI pipeline that runs 86 tests plus a self-test on a clean Linux runner using GitHub Actions. If all tests pass, Render automatically deploys the Docker container to production; if any tests fail, deployment is blocked to ensure the 
- **profile-06** ✅ Which programming languages does Barry know?
  - Barry knows Python, Java, SQL, JavaScript, and HTML/CSS.
- **profile-07** ❌ Has Barry used Docker?
  - Barry has used Docker in multiple projects. In the Global Wall Inspector project, Docker Compose is used for running the full stack application with PostgreSQL 15, and the system architecture includes a Docker container for the Flask application with Gunicorn, Sentinel and Director agents, and an MCP server. The BBSISK project also lists Docker among its technologies, and its build process uses Render to auto-deploy a Docker container after GitHub Actions testing passes.
- **profile-08** ✅ What cloud and DevOps tools has Barry worked with?
  - Barry has worked with Docker, Terraform, GitHub Actions, Render, Microsoft Azure, Cloudflare, and Cloudinary. These tools are listed in his toolbox and are used in his projects like Wall Inspector and Ask Barry.
- **profile-09** ✅ How can I contact Barry?
  - Barry can be contacted via email at barry.b.sisk@gmail.com or through his LinkedIn profile.
- **profile-10** ✅ What cloud tools has Barry used?
  - Barry has used Docker, Terraform, GitHub Actions, Render, Microsoft Azure, Cloudflare, and Cloudinary. Specifically, Docker and Terraform are used in both Ask Barry and Wall Inspector projects. GitHub Actions is used for CI in both projects. Render is mentioned as a deployment platform for Ask Barry. Microsoft Azure is used for Azure OpenAI and Azure AI Search in Ask Barry. Cloudflare and Cloudinary are listed under cloud and devops tools in the toolbox section.
- **career-01** ✅ What leadership roles did Barry hold at Intel?
  - Barry held several leadership roles at Intel, including 300mm CMP Group Leader from July 2009 to September 2016, 200mm CMP Group Leader from April 2008 to July 2009, CVD Group Leader from April 2005 to April 2008, and 300mm Implant Group Leader from October 2016 to August 2019.
- **wall-01** ✅ What is Wall Inspector and who is it for?
  - Wall Inspector is a clinical skills-assessment & certification platform built for civil engineering, heritage conservation, and masonry construction students and assessors. It turns high-resolution, uncompressed masonry photographs into interactive diagnostic workstations where students can inspect walls, classify structural severity, and prescribe conservation remedies, which are then graded in real time against expert ground-truth bounding boxes.
- **wall-02** ✅ What does the Intake Sentinel agent check in uploaded photographs?
  - The Intake Sentinel agent evaluates newly uploaded field photographs across 4 photogrammetric pillars: 90° orthogonal plane, diffuse illumination, course framing, and Laplacian focus sharpness.
- **wall-03** ✅ Which tools does the Wall Inspector MCP server expose?
  - The Wall Inspector MCP server exposes the following tools: sentinel_evaluate_image, curriculum_cohort_intelligence, list_skill_specimens, and export_coco_dataset_stats.
- **wall-04** ✅ How does human-in-the-loop provenance tracking work in Wall Inspector?
  - In Wall Inspector, human-in-the-loop provenance tracking has three tiers: auto_suggested (AI proposals), auto_accepted (assessor-reviewed AI proposals), and human_graded (assessor-marked from scratch). Each tier is tagged accordingly, with auto_accepted including the assessor's name and timestamp. This creates a verified ground-truth pool for future training and retrieval.
- **wall-05** ✅ What dataset format does Wall Inspector export for computer vision tools?
  - Wall Inspector exports labeled datasets in Microsoft COCO 1.0 JSON format for downstream Computer Vision training, specifically for CVAT and YOLOv8.
- **wall-06** ✅ How many automated tests does Wall Inspector run?
  - Wall Inspector runs 86 automated unit and agent tests.
- **wall-07** ✅ Which database does Wall Inspector use in production?
  - Wall Inspector uses PostgreSQL 15 in production.
- **wall-08** ✅ Has Barry used Terraform for infrastructure as code?
  - Yes, Barry has used Terraform for infrastructure as code in both the Ask Barry and Wall Inspector projects. In Ask Barry, Terraform is used to manage Azure resources with import blocks to adopt existing resources without recreation (1). In Wall Inspector, Terraform is part of the infrastructure as code and CI/CD setup, as shown in the system architecture diagram and listed in key repository files (2, 4).
- **wall-09** ✅ How are credentials and secrets handled in Wall Inspector?
  - In Wall Inspector, all credentials and cloud endpoints are injected strictly via environment variables and are never hardcoded. The required variables include DATABASE_URL for PostgreSQL 15, CLOUDINARY_URL for Cloudinary CDN, GEMINI_API_KEY for Google Gemini Vision API, ADMIN_PASSWORD and ADMIN_PIN for assessor workstation credentials, and SECRET_KEY for cryptographic session signing.
- **agentmath-01** ✅ How many assessment items does AgentMath have?
  - AgentMath has over 3,000 curriculum-aligned assessment items.
- **agentmath-02** ✅ How does AgentMath protect children's privacy?
  - AgentMath protects children's privacy by offering three ways to sign in: Quick Try with no registration, anonymous guest codes that track progress without collecting personal data, and Google/Microsoft sign-in using existing school accounts. It also allows guest-to-account progress transfer so students don't lose progress when they later sign in properly. The platform is designed specifically for children's privacy, allowing students to use it fully without giving any personal data.
- **agentmath-03** ✅ What is Agent of the Lost Numbers?
  - Agent of the Lost Numbers is a 3D, first-person history-of-maths adventure built in Three.js, featuring a procedurally generated maze and a room-by-room journey from Mesopotamia to Egypt, with puzzles to solve.
- **agentmath-04** ✅ What technology stack is AgentMath built with?
  - AgentMath uses Python and Flask for the backend, SQLite for data storage, HTML, CSS, JavaScript, and Three.js for the front end, and Google and Microsoft OAuth for identity. It is delivered as a Progressive Web App hosted on PythonAnywhere with GitHub for version control.
- **agentmath-05** ✅ What gamification features keep AgentMath students engaged?
  - AgentMath includes badges, avatars, leaderboards, and a Points for Prizes reward system to keep students engaged. It also features real-life adventures such as a multi-week Soccer Owner Journey and classroom games like station-based activities and a Z-score sprint lab.
- **inmytime-01** ✅ Does In My Time store the family stories it collects?
  - In My Time does not store the family stories it collects. The server relays each answer in the same request and stores nothing, keeping no message text and no transcriptions. Media is forwarded by reference and never downloaded. The database schema has no column capable of holding an answer, and the only records kept are timestamps and the author's position in the question sequence.
- **inmytime-02** ✅ How does In My Time get the grandparent's consent?
  - In My Time gets the grandparent's consent through a WhatsApp message. After the custodian signs up, the grandparent receives a single WhatsApp consent message and nothing starts until they reply, meaning consent is in their hands.
- **inmytime-03** ✅ What is StoryCatcher?
  - StoryCatcher is a module within the In My Time project that allows family members to record interviews with relatives directly in the browser. It features guided interviews with curated question packs, client-side encryption for recordings and names, per-interviewee access control, photo capture during recordings, and options for storing recordings in Cloudflare R2 or Google Drive.
- **inmytime-04** ✅ Why were admin WhatsApp alerts failing silently, and how was it fixed?
  - Admin WhatsApp alerts were failing silently because of WhatsApp's 24-hour session rule, which only delivers free-form messages while a conversation is open. Barry fixed this by adding an automatic fallback to a pre-approved template message, with tests covering both paths.
- **inmytime-05** ❌ Has Barry built multilingual or internationalised software?
  - Barry has built multilingual or internationalised software in two projects. In In My Time, he built internationalisation at the foundation to allow adding new languages as a documented, repeatable process. In Brief, he implemented German localisation.
- **inmytime-06** ✅ What browser testing has Barry done?
  - Barry has done browser testing that exercises real encryption and media playback in the In My Time project, and end-to-end Playwright browser tests (real encryption, recording and playback) are part of its testing strategy.
- **brief-01** ✅ What is Brief?
  - Brief is a journaling app that asks users to write thirty words a week about their life, designed to create a personal record of how they change over time. It sends weekly prompts via WhatsApp or email and allows users to archive entries, scroll back through their timeline, and optionally share with groups or seal entries as time capsules. It features a 16-week prompt cycle, groups, echoes, time capsules, and an installable web app with OAuth sign-in.
- **brief-02** ✅ How did Barry handle a leaked credential incident?
  - Barry handled a leaked credential incident in the my30words_showcase project by rotating every exposed secret (Google, Microsoft, and Twilio), rebuilding the Git history as a single clean commit, and locking the repository down with a strict .gitignore for databases, configuration, and backups.
- **brief-03** ✅ Why did weekly prompts drift off schedule, and how was it fixed?
  - Weekly prompts drifted off schedule because the system tracked each user's week position using a stored counter that could fall out of step. This was fixed by recalculating the week purely from time (from sign-up to now), which prevents drift. An existing user migration back-filled their data to the new system.
- **brief-04** ✅ How did Barry fix HTTPS certificates that would not validate?
  - Barry fixed HTTPS certificates that would not validate by moving DNS to Cloudflare and setting the records to DNS-only. This solution was applied to both the 'In My Time' and 'my30words_showcase' projects.
- **brief-05** ✅ What are time capsules in Brief?
  - In Brief, time capsules allow users to seal an entry for 1, 5, or 10 years.
- **askbarry-01** ✅ What is the Ask Barry project?
  - Barry developed Ask Barry, an AI assistant that answers questions about his software projects using only the documentation in his public GitHub repositories. The assistant cites the repository, file, and section behind every answer. It is designed for recruiters, interviewers, and developers to get quick, sourced answers about his work.
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
  - Barry has not trained a YOLOv8 model, but he has exported data in COCO format suitable for training YOLOv8. The Global Wall Inspector project includes an MLOps COCO 1.0 Dataset Exporter that produces JSON files for CVAT and YOLOv8-Seg pipelines [1]. (judge: The answer explicitly states Barry has not trained a YOLOv8 model but has only exported data suitable for training it.)
- **trap-09** ✅ Has Barry worked with Apache Kafka?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **mcp-01** ✅ Which of Barry's projects include an MCP server?
  - Barry's projects Ask Barry and Wall Inspector both include an MCP server. Ask Barry uses an MCP server to allow AI assistants like Claude Desktop and VS Code to query his documentation directly (ask-barry_mcp.py). Wall Inspector also includes an MCP server as part of its architecture, connected to the Flask application and other components.
- **askbarry-02** ✅ Has Barry deployed a RAG system to production?
  - Yes, Barry has deployed a RAG (Retrieval-Augmented Generation) system to production. The project 'Ask Barry' is live in production with RAG capabilities, including Azure AI Search for hybrid retrieval, Azure OpenAI for generating answers, and strict citation requirements. The system has been evaluated for answer quality and includes a job-ad agent that is also live and evaluated.
