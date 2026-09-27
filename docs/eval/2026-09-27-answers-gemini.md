# Answer evaluation

Date: 2026-09-27 · Model: gemini-3.5-flash (gemini); judge gpt-4.1-mini · Retrieval: Azure hybrid, top 8 · Answerable: 38 · Traps: 8

| Metric | Value |
|---|---|
| Answered (answerable questions) | 100% |
| Answer cites a section containing the answer | 100% |
| Faithful to cited sources (LLM judge, of answered) | 100% |
| Answers with a true-but-uncited claim | 0 |
| Regression checks failed | 0 |
| **Traps: no false claim** | **100%** |
| Questions passing every check | 46 of 46 |

The judge is the same model family (gpt-4.1-mini), so the citation test and regression checks are deliberately deterministic. Sample sizes are small; one question is about 3 points.

## Failures and notes

None.
## All questions

| ID | Type | Pass | Supported | Sources cited |
|---|---|---|---|---|
| profile-01 | answerable | ✅ | True | 1 |
| profile-02 | answerable | ✅ | True | 2 |
| profile-03 | answerable | ✅ | True | 1 |
| profile-04 | answerable | ✅ | True | 2 |
| profile-05 | answerable | ✅ | True | 1 |
| profile-06 | answerable | ✅ | True | 3 |
| profile-07 | answerable | ✅ | True | 5 |
| profile-08 | answerable | ✅ | True | 7 |
| profile-09 | answerable | ✅ | True | 1 |
| profile-10 | answerable | ✅ | True | 5 |
| wall-01 | answerable | ✅ | True | 1 |
| wall-02 | answerable | ✅ | True | 2 |
| wall-03 | answerable | ✅ | True | 1 |
| wall-04 | answerable | ✅ | True | 2 |
| wall-05 | answerable | ✅ | True | 4 |
| wall-06 | answerable | ✅ | True | 1 |
| wall-07 | answerable | ✅ | True | 3 |
| wall-08 | answerable | ✅ | True | 4 |
| wall-09 | answerable | ✅ | True | 1 |
| agentmath-01 | answerable | ✅ | True | 2 |
| agentmath-02 | answerable | ✅ | True | 3 |
| agentmath-03 | answerable | ✅ | True | 2 |
| agentmath-04 | answerable | ✅ | True | 3 |
| agentmath-05 | answerable | ✅ | True | 1 |
| inmytime-01 | answerable | ✅ | True | 4 |
| inmytime-02 | answerable | ✅ | True | 2 |
| inmytime-03 | answerable | ✅ | True | 2 |
| inmytime-04 | answerable | ✅ | True | 1 |
| inmytime-05 | answerable | ✅ | True | 2 |
| inmytime-06 | answerable | ✅ | True | 3 |
| brief-01 | answerable | ✅ | True | 6 |
| brief-02 | answerable | ✅ | True | 1 |
| brief-03 | answerable | ✅ | True | 1 |
| brief-04 | answerable | ✅ | True | 2 |
| brief-05 | answerable | ✅ | True | 2 |
| askbarry-01 | answerable | ✅ | True | 5 |
| trap-01 | trap | ✅ | False | 0 |
| trap-02 | trap | ✅ | False | 0 |
| trap-03 | trap | ✅ | False | 0 |
| trap-04 | trap | ✅ | False | 0 |
| trap-05 | trap | ✅ | False | 0 |
| trap-06 | trap | ✅ | False | 0 |
| trap-07 | trap | ✅ | False | 0 |
| trap-09 | trap | ✅ | False | 0 |
| mcp-01 | answerable | ✅ | True | 6 |
| askbarry-02 | answerable | ✅ | True | 3 |

## All answers (for human review)

- **profile-01** ✅ Where did Barry work before becoming a software developer?
  - Before becoming a software developer, Barry spent 30 years at Intel Ireland. During his time there, he led engineering teams in high-volume, tightly controlled manufacturing.
- **profile-02** ✅ What qualification is Barry studying for, and where?
  - Barry is studying for a Higher Diploma in Software Development at Maynooth University.
- **profile-03** ✅ When is Barry available for full-time roles?
  - Barry is available for full-time roles starting from June 2027. He is also open to part-time work during his studies prior to that date.
- **profile-04** ✅ Which AI coding agents does Barry use day to day?
  - Barry uses Claude Code and Google Antigravity as AI coding agents on a daily basis [1]. He prompts these agents within VS Code to write code and tests, which he then reviews and runs locally [2].
- **profile-05** ✅ Describe Barry's workflow from prompt to production.
  - Barry's workflow begins by describing a change to an AI coding agent in VS Code, which writes the code and accompanying tests. He then reviews the diff and runs the tests locally to verify the changes. After pushing the code to GitHub, a CI pipeline runs the full test suite on a clean Linux runner. If all checks pass, Render automatically deploys the Docker container to production.
- **profile-06** ✅ Which programming languages does Barry know?
  - Barry knows Python, Java, SQL, JavaScript, and HTML/CSS. Python is also used throughout his projects, such as in the ask-barry MCP server and scripts.
- **profile-07** ✅ Has Barry used Docker?
  - Barry has used Docker across his projects and lists it in his DevOps toolbox [2]. He utilizes Docker in the Wall Inspector project, which includes a Dockerfile and can be run locally using Docker Compose [1, 3, 5]. Furthermore, his automated deployment pipeline deploys a Docker container to Render [4].
- **profile-08** ✅ What cloud and DevOps tools has Barry worked with?
  - Barry has worked with Docker, Terraform, GitHub Actions, Render, Cloudflare, and Cloudinary [1]. In the Global Wall Inspector project, he utilized Terraform for infrastructure, GitHub Actions for CI/CD, and Docker/Docker Compose for containerization [2, 3, 7]. For the In My Time project, his infrastructure tools included Cloudflare DNS, Let's Encrypt, PythonAnywhere, and GitHub [7]. He has also documented manual setup for Azure services in the Ask Barry project, with plans to codify them using T
- **profile-09** ✅ How can I contact Barry?
  - Barry can be contacted via email at barry.b.sisk@gmail.com. He can also be reached through his LinkedIn profile.
- **profile-10** ✅ What cloud tools has Barry used?
  - Barry's toolbox lists cloud and DevOps tools including Docker, Terraform, GitHub Actions, Render, Cloudflare, and Cloudinary [2]. In the Global Wall Inspector project, he utilizes Docker, GitHub Actions, Terraform, and Cloudinary CDN [3, 5]. For the Ask Barry project, he sets up and uses Azure services, specifically Azure OpenAI and Azure AI Search [1, 7].
- **wall-01** ✅ What is Wall Inspector and who is it for?
  - Barry's Global Wall Inspector is a clinical skills-assessment and certification platform that turns high-resolution masonry photographs into interactive diagnostic workstations [1]. It is built for civil engineering, heritage conservation, and masonry construction students and assessors [1]. On the platform, students inspect walls using a zoom loupe, drop spatial defect pins, classify structural severity, and prescribe conservation remedies, which are graded in real time [1].
- **wall-02** ✅ What does the Intake Sentinel agent check in uploaded photographs?
  - In the Global Wall Inspector project, the Intake Sentinel agent audits the quality of newly uploaded field photographs. It evaluates these images across four photogrammetric pillars: a 90° orthogonal plane, diffuse illumination, course framing, and Laplacian focus sharpness. This evaluation is performed with a non-blocking Progress Under Advisement override.
- **wall-03** ✅ Which tools does the Wall Inspector MCP server expose?
  - The Wall Inspector Model Context Protocol (MCP) server exposes several domain agent tools over JSON-RPC 2.0 for external LLM hosts like Claude, Gemini, and Cursor. These tools are `sentinel_evaluate_image`, `curriculum_cohort_intelligence`, `list_skill_specimens`, and `export_coco_dataset_stats`.
- **wall-04** ✅ How does human-in-the-loop provenance tracking work in Wall Inspector?
  - In Wall Inspector, human-in-the-loop provenance tracking uses a three-tier audit lineage to classify defect pins [1, 2]. Defect proposals generated by Gemini Vision are initially tagged as `auto_suggested` [1, 2]. When an assessor reviews and saves a proposal, it is upgraded to `auto_accepted` with an audited name and timestamp, while defects marked from scratch are labeled `human_graded` [1, 2]. This tracking adds metadata like confidence scores and provenance to PostgreSQL records, ensuring on
- **wall-05** ✅ What dataset format does Wall Inspector export for computer vision tools?
  - Barry's Wall Inspector project exports labeled datasets in the Microsoft COCO 1.0 JSON format. This standard format is designed for downstream Computer Vision training, specifically supporting CVAT and YOLOv8 or YOLOv8-Seg pipelines. The exported dataset includes full-resolution Cloudinary image links, expert ground-truth bounding boxes, and crowdsourced student consensus pins.
- **wall-06** ✅ How many automated tests does Wall Inspector run?
  - Barry's Wall Inspector project runs 86 automated unit and agent tests.
- **wall-07** ✅ Which database does Wall Inspector use in production?
  - In production, Wall Inspector uses PostgreSQL 15 [1, 3, 7]. The database is managed, and its connection string is injected strictly via the DATABASE_URL environment variable [1]. Existing production records in PostgreSQL are preserved on startup using a non-destructive auto-migration [2].
- **wall-08** ✅ Has Barry used Terraform for infrastructure as code?
  - Yes, Barry has used Terraform for infrastructure as code. In the Global Wall Inspector project, he uses Terraform to manage infrastructure, utilizing files such as `infra/main.tf`, `infra/variables.tf`, and `infra/outputs.tf` [1, 3]. He also lists Terraform in his general Cloud & DevOps toolbox [4]. Additionally, he plans to use Terraform to codify the Azure setup in Stage 7 of the Ask Barry project [2].
- **wall-09** ✅ How are credentials and secrets handled in Wall Inspector?
  - In the Wall Inspector project, all credentials and cloud endpoints are injected strictly via environment variables and are never hardcoded [1]. These environment variables include DATABASE_URL for PostgreSQL, CLOUDINARY_URL for Cloudinary CDN, and GEMINI_API_KEY for the Google Gemini Vision API [1]. They also manage assessor workstation credentials (ADMIN_PASSWORD and ADMIN_PIN) and a cryptographic session signing key (SECRET_KEY) [1].
- **agentmath-01** ✅ How many assessment items does AgentMath have?
  - AgentMath has over 3,000 curriculum-aligned assessment items.
- **agentmath-02** ✅ How does AgentMath protect children's privacy?
  - AgentMath protects children's privacy by allowing students to use the platform fully without providing any personal data [2]. It offers anonymous guest codes to track progress without collecting a name or email address, as well as a "Quick Try" option with no registration [1]. Alternatively, students can sign in using existing school accounts via Google or Microsoft OAuth [1, 6]. Guest-to-account progress transfer is also supported so no progress is lost if a student later signs in properly [1].
- **agentmath-03** ✅ What is Agent of the Lost Numbers?
  - Agent of the Lost Numbers is a 3D, first-person history-of-maths adventure game built using Three.js as part of Barry's AgentMath platform. The game features a procedurally generated maze, puzzles to solve, and a room-by-room journey from Mesopotamia to Egypt.
- **agentmath-04** ✅ What technology stack is AgentMath built with?
  - AgentMath's backend is built using Python and Flask, with SQLite managing data such as the question bank and student progress. The front end utilizes HTML, CSS, JavaScript, and Three.js for its 3D module. For identity, the platform supports Google and Microsoft OAuth alongside anonymous guest codes. It is delivered as a Progressive Web App hosted on PythonAnywhere.
- **agentmath-05** ✅ What gamification features keep AgentMath students engaged?
  - AgentMath uses gamification features such as badges, avatars, leaderboards, and a "Points for Prizes" reward system to keep students engaged [1]. It also features "Real Life Adventures," including a multi-week "Soccer Owner Journey" where students build a pitch and plan match strategy [1]. Additionally, the platform includes "Agent of the Lost Numbers," a 3D, first-person history-of-maths adventure game [1].
- **inmytime-01** ✅ Does In My Time store the family stories it collects?
  - No, Barry's "In My Time" project does not store the family stories it collects. The server relays each answer instantly to the custodian and stores no message text, transcriptions, or downloaded media. Additionally, the database schema is designed without any columns capable of holding an answer.
- **inmytime-02** ✅ How does In My Time get the grandparent's consent?
  - In the "In My Time" project, the grandparent (the "author") receives a single WhatsApp consent message [1]. Nothing starts until they reply, ensuring consent remains in their hands rather than a checkbox ticked by someone else [1]. This design works within the consent rules of real-world messaging platforms [2].
- **inmytime-03** ✅ What is StoryCatcher?
  - StoryCatcher is a module of Barry's 'In My Time' project that allows family members to record interviews with relatives in the browser [1]. It features guided interviews using curated question packs, client-side encryption, and per-interviewee access control [1]. Users can capture photos during recordings and save encrypted media to Cloudflare R2 or Google Drive [1, 7]. It also includes a scrollable timeline called LifeLine to pin clips and notes alongside historical context [1].
- **inmytime-04** ✅ Why were admin WhatsApp alerts failing silently, and how was it fixed?
  - In the "In My Time" project, admin alerts failed silently because of WhatsApp's 24-hour session rule, which dictates that free-form messages are only delivered while a conversation is open, despite the messaging API reporting successful sends [1]. Barry fixed this by implementing an automatic fallback to a pre-approved template message [1]. He also added tests to cover both delivery paths [1].
- **inmytime-05** ✅ Has Barry built multilingual or internationalised software?
  - Yes, Barry has built internationalised software. For his project "In My Time", he built internationalisation at the foundation of the application to make adding new languages a documented, repeatable process [1]. This project features German localisation and utilizes Flask-Babel [2].
- **inmytime-06** ✅ What browser testing has Barry done?
  - For the "In My Time" project, Barry has implemented automated end-to-end browser test suites using Playwright. These browser tests are designed to exercise real encryption, recording, and media playback.
- **brief-01** ✅ What is Brief?
  - Brief is a journaling app built by Barry Sisk that asks users for exactly thirty words a week to create a personal record of how they change over time [1, 6]. Prompts are delivered weekly via WhatsApp or email, and users write their entries in an installable web app [4, 5, 8]. The app features a 16-week prompt cycle, sharing groups, anonymous public feeds, and time capsules [4]. It is built with Flask, SQLite, Twilio, and OAuth, and prioritizes privacy with full data export and permanent account
- **brief-02** ✅ How did Barry handle a leaked credential incident?
  - When an automated scanner flagged API credentials in an early commit of the my30words_showcase project, Barry rotated all exposed Google, Microsoft, and Twilio secrets to deactivate them. He then rebuilt the Git history as a single clean commit and secured the repository with a strict .gitignore. Barry now applies the practice of resetting Git history, rather than just untracking files, to all his projects if a first commit contains a secret.
- **brief-03** ✅ Why did weekly prompts drift off schedule, and how was it fixed?
  - In the my30words_showcase project, prompts drifted because each user's week position was tracked using a stored counter that could fall out of step, causing some cycles to stall or run on an 8-day schedule. Barry fixed this by rebuilding the system to calculate the week purely from time elapsed since sign-up. He also back-filled existing users with a one-off migration to prevent future drift.
- **brief-04** ✅ How did Barry fix HTTPS certificates that would not validate?
  - In both the 'In My Time' and 'my30words' projects, Barry resolved HTTPS certificate validation failures caused by the registrar's DNS setup [1, 2]. He fixed the issue by moving the DNS to Cloudflare and configuring the records to DNS-only [1, 2].
- **brief-05** ✅ What are time capsules in Brief?
  - In Barry's project Brief, time capsules are a feature that allows users to seal a journal entry for 1, 5, or 10 years. These capsules are stored in the application's SQLite database alongside users, entries, and groups.
- **askbarry-01** ✅ What is the Ask Barry project?
  - Ask Barry is an AI portfolio assistant designed to answer questions about Barry Sisk's software projects for recruiters, interviewers, and developers [1, 2]. It answers questions using only the documentation from his public GitHub repositories and cites the exact repository, file, and section for every answer [1, 2]. The system is built on a general-purpose model supplied through Microsoft Azure and uses Azure AI Search for hybrid retrieval [5, 8]. It can be accessed via a live website or throug
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
  - Barry has implemented Model Context Protocol (MCP) servers in two of his projects: Ask Barry and Wall Inspector. In the Ask Barry project, the MCP server is implemented in `ask_barry_mcp.py` to allow AI assistants to query the project as a tool. In the Wall Inspector project, the MCP server is implemented in `mcp_server.py` to expose the platform's domain agents over JSON-RPC 2.0.
- **askbarry-02** ✅ Has Barry deployed a RAG system to production?
  - Yes, Barry has deployed a RAG system to production. His project "Ask Barry" features retrieval-augmented generation live in production on Render. The system uses Azure AI Search for hybrid retrieval and Azure OpenAI to generate grounded answers with citations.
