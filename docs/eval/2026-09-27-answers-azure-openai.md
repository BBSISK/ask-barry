# Answer evaluation

Date: 2026-09-27 · Model: gpt-4.1-mini (azure-openai); judge gpt-4.1-mini · Retrieval: Azure hybrid, top 8 · Answerable: 37 · Traps: 8

| Metric | Value |
|---|---|
| Answered (answerable questions) | 92% |
| Answer cites a section containing the answer | 89% |
| Faithful to cited sources (LLM judge, of answered) | 94% |
| Answers with a true-but-uncited claim | 1 |
| Regression checks failed | 1 |
| **Traps: no false claim** | **100%** |
| Questions passing every check | 39 of 45 |

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
- Answer: Barry has used Microsoft Azure cloud tools for the Ask Barry project, including Azure OpenAI for embeddings and chat models, Azure AI Search for storing chunks and vectors with hybrid keyword and vector search, and Azure budget alerts to monitor spending. These tools are set up via the Azure portal and are part of the Ask Barry system's architecture. The use of these Azure services is documented i
- answered=True · cited_answer=False · faithful=True
- Check failures: missing 'Terraform'
- Sources: ask-barry/docs/azure-setup.md (Stage 3: Azure setup); ask-barry/README.md (Ask Barry > Current status: Stage 6 complete (RAG live in production, answer quality evaluated))

### agentmath-03 (answerable)
- Answer: Agent of the Lost Numbers is a 3D, first-person history-of-maths adventure built in Three.js, featuring a procedurally generated maze and a room-by-room journey from Mesopotamia to Egypt with puzzles to solve. It is part of the AgentMath project, which is an adaptive, game-based maths platform for Irish Junior Cycle students.
- answered=True · cited_answer=True · faithful=False
- Unsupported claims: It is part of the AgentMath project, which is an adaptive, game-based maths platform for Irish Junior Cycle students. (true but uncited: support is in a retrieved section the answer didn't cite)
- Sources: agentmath_showcase/README.md (🕵️ AgentMath > What it does)

### inmytime-05 (answerable)
- Answer: I can't find evidence of that in Barry's public GitHub documentation.
- answered=False · cited_answer=False · faithful=None
- Sources: none

### askbarry-01 (answerable)
- Answer: Ask Barry is an AI assistant that answers questions about Barry Sisk's software projects using only the README and documentation files in his public GitHub repositories, citing the repository, file, and section behind every answer. It is designed as a portfolio assistant for recruiters, interviewers, and developers to get quick, sourced answers about Barry's work. The project includes a Flask app 
- answered=True · cited_answer=True · faithful=False
- Unsupported claims: It includes a model card with an EU AI Act assessment. (judge quoted "Last reviewed: 27 September 2026 · Live: https://ask-barry-7dkz.onrender.com · Source: https://github.com/BBSISK/ask-barry

- **Role:** I'm the provid", not found in sources)
- Sources: ask-barry/docs/model-card.md (Ask Barry: model card > What it is); ask-barry/README.md (Ask Barry); ask-barry/docs/model-card.md (Ask Barry: model card); ask-barry/README.md (Ask Barry > Current status: Stage 6 complete (RAG live in production, answer quality evaluated))

## All questions

| ID | Type | Pass | Supported | Sources cited |
|---|---|---|---|---|
| profile-01 | answerable | ✅ | True | 1 |
| profile-02 | answerable | ✅ | True | 1 |
| profile-03 | answerable | ✅ | True | 1 |
| profile-04 | answerable | ✅ | True | 1 |
| profile-05 | answerable | ✅ | True | 1 |
| profile-06 | answerable | ❌ | False | 0 |
| profile-07 | answerable | ✅ | True | 3 |
| profile-08 | answerable | ✅ | True | 1 |
| profile-09 | answerable | ❌ | False | 0 |
| profile-10 | answerable | ❌ | True | 2 |
| wall-01 | answerable | ✅ | True | 1 |
| wall-02 | answerable | ✅ | True | 1 |
| wall-03 | answerable | ✅ | True | 1 |
| wall-04 | answerable | ✅ | True | 3 |
| wall-05 | answerable | ✅ | True | 2 |
| wall-06 | answerable | ✅ | True | 2 |
| wall-07 | answerable | ✅ | True | 2 |
| wall-08 | answerable | ✅ | True | 2 |
| wall-09 | answerable | ✅ | True | 1 |
| agentmath-01 | answerable | ✅ | True | 2 |
| agentmath-02 | answerable | ✅ | True | 3 |
| agentmath-03 | answerable | ❌ | True | 1 |
| agentmath-04 | answerable | ✅ | True | 2 |
| agentmath-05 | answerable | ✅ | True | 1 |
| inmytime-01 | answerable | ✅ | True | 3 |
| inmytime-02 | answerable | ✅ | True | 1 |
| inmytime-03 | answerable | ✅ | True | 2 |
| inmytime-04 | answerable | ✅ | True | 1 |
| inmytime-05 | answerable | ❌ | False | 0 |
| inmytime-06 | answerable | ✅ | True | 1 |
| brief-01 | answerable | ✅ | True | 7 |
| brief-02 | answerable | ✅ | True | 1 |
| brief-03 | answerable | ✅ | True | 1 |
| brief-04 | answerable | ✅ | True | 2 |
| brief-05 | answerable | ✅ | True | 1 |
| askbarry-01 | answerable | ❌ | True | 4 |
| trap-01 | trap | ✅ | False | 0 |
| trap-02 | trap | ✅ | False | 0 |
| trap-03 | trap | ✅ | False | 0 |
| trap-04 | trap | ✅ | False | 0 |
| trap-05 | trap | ✅ | True | 1 |
| trap-06 | trap | ✅ | False | 0 |
| trap-07 | trap | ✅ | False | 0 |
| trap-09 | trap | ✅ | False | 0 |
| askbarry-02 | answerable | ✅ | True | 4 |

## All answers (for human review)

- **profile-01** ✅ Where did Barry work before becoming a software developer?
  - Barry worked for 30 years at Intel Ireland leading engineering teams in high-volume, tightly controlled manufacturing before becoming a software developer.
- **profile-02** ✅ What qualification is Barry studying for, and where?
  - Barry is completing a Higher Diploma in Software Development at Maynooth University, expected in 2027.
- **profile-03** ✅ When is Barry available for full-time roles?
  - Barry is available for full-time roles from June 2027.
- **profile-04** ✅ Which AI coding agents does Barry use day to day?
  - Barry uses AI coding agents Claude Code and Google Antigravity every day and builds agents into his own apps, as stated in his personal introduction.
- **profile-05** ✅ Describe Barry's workflow from prompt to production.
  - Barry's workflow from prompt to production involves describing the change to an AI coding agent in VS Code, which writes the code and tests. He then reviews the diff and runs tests locally. After that, he pushes the change to GitHub, where a CI pipeline runs the full test suite on a clean Linux runner. If all tests pass, Render auto-deploys the Docker container to production; if tests fail, deployment is blocked, ensuring only reviewed, tested changes go live in about two minutes.
- **profile-06** ❌ Which programming languages does Barry know?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **profile-07** ✅ Has Barry used Docker?
  - Barry uses Docker in the Global Wall Inspector project, where the full stack (web application and PostgreSQL 15 database) runs with Docker Compose. The Docker container includes Flask, Gunicorn, and AI agents, and is deployed automatically via Render after passing CI tests. This is documented in the Wall Inspector README and the build process description in BBSISK README.
- **profile-08** ✅ What cloud and DevOps tools has Barry worked with?
  - Barry has worked with Docker, Terraform, GitHub Actions, Render, Cloudflare, and Cloudinary as cloud and DevOps tools, as listed in his toolbox.
- **profile-09** ❌ How can I contact Barry?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **profile-10** ❌ What cloud tools has Barry used?
  - Barry has used Microsoft Azure cloud tools for the Ask Barry project, including Azure OpenAI for embeddings and chat models, Azure AI Search for storing chunks and vectors with hybrid keyword and vector search, and Azure budget alerts to monitor spending. These tools are set up via the Azure portal and are part of the Ask Barry system's architecture. The use of these Azure services is documented in the Ask Barry project, specifically in the Azure setup guide and the project status documentation.
- **wall-01** ✅ What is Wall Inspector and who is it for?
  - Wall Inspector is a clinical skills-assessment and certification platform designed for civil engineering, heritage conservation, and masonry construction students and assessors. It enables interactive diagnostics of masonry defects using high-resolution photographs, allowing students to inspect walls, classify defects, and prescribe remedies that are graded in real time against expert ground truth. The platform addresses limitations of traditional masonry training by providing objective, interac
- **wall-02** ✅ What does the Intake Sentinel agent check in uploaded photographs?
  - The Intake Sentinel agent evaluates newly uploaded field photographs across four photogrammetric pillars: 90° orthogonal plane, diffuse illumination, course framing, and Laplacian focus sharpness.
- **wall-03** ✅ Which tools does the Wall Inspector MCP server expose?
  - The Wall Inspector MCP server exposes the platform's domain agents over JSON-RPC 2.0 for external LLM hosts. These tools include `sentinel_evaluate_image`, `curriculum_cohort_intelligence`, `list_skill_specimens`, and `export_coco_dataset_stats`.
- **wall-04** ✅ How does human-in-the-loop provenance tracking work in Wall Inspector?
  - In Wall Inspector, human-in-the-loop provenance tracking uses a 3-tier audit lineage for defect pins: 'auto_suggested' pins are AI proposals by Gemini Vision on upload and are unverified; 'auto_accepted' pins are those reviewed, adjusted, and saved by an assessor with name and timestamp auditing, making them verified; 'human_graded' pins are marked from scratch by an assessor and serve as gold-standard benchmarks. Each defect pin includes a confidence score, and the assessor queue can be filtere
- **wall-05** ✅ What dataset format does Wall Inspector export for computer vision tools?
  - Wall Inspector exports datasets in the Microsoft COCO 1.0 JSON format for downstream computer vision training with tools like CVAT and YOLOv8.
- **wall-06** ✅ How many automated tests does Wall Inspector run?
  - Wall Inspector runs 86 automated unit and agent tests as part of its verification process.
- **wall-07** ✅ Which database does Wall Inspector use in production?
  - Wall Inspector uses a managed PostgreSQL 15 database in production, as indicated by the environment variable DATABASE_URL and the system architecture documentation.
- **wall-08** ✅ Has Barry used Terraform for infrastructure as code?
  - Barry uses Terraform for infrastructure as code in the Global Wall Inspector project, as shown in the system and DevOps architecture diagram. For the Ask Barry project, infrastructure as code for Azure resources is planned but not yet implemented.
- **wall-09** ✅ How are credentials and secrets handled in Wall Inspector?
  - In Wall Inspector, all credentials and cloud endpoints are injected strictly via environment variables and never hardcoded. These include the PostgreSQL connection string, Cloudinary CDN key, Google Gemini Vision API key, assessor workstation credentials, and a cryptographic session signing key. This approach ensures that sensitive information is managed securely outside the codebase.
- **agentmath-01** ✅ How many assessment items does AgentMath have?
  - AgentMath has over 3,000 curriculum-aligned assessment items.
- **agentmath-02** ✅ How does AgentMath protect children's privacy?
  - AgentMath protects children's privacy by allowing students to use the platform without providing personal data through three access methods: Quick Try with no registration, anonymous guest codes that track progress without collecting names or emails, and Google/Microsoft sign-in using existing school accounts. It also supports guest-to-account progress transfer to avoid data loss when students sign in properly later. The design is privacy-conscious specifically for children, enabling full platfo
- **agentmath-03** ❌ What is Agent of the Lost Numbers?
  - Agent of the Lost Numbers is a 3D, first-person history-of-maths adventure built in Three.js, featuring a procedurally generated maze and a room-by-room journey from Mesopotamia to Egypt with puzzles to solve. It is part of the AgentMath project, which is an adaptive, game-based maths platform for Irish Junior Cycle students.
- **agentmath-04** ✅ What technology stack is AgentMath built with?
  - AgentMath is built with a backend using Python and Flask, with SQLite for data storage including question bank and student progress. The front end uses HTML, CSS, JavaScript, and Three.js for 3D modules. It supports identity management via Google OAuth, Microsoft OAuth (Azure app registration), and anonymous guest codes. The platform is delivered as a Progressive Web App hosted on PythonAnywhere, with development assisted by AI tools like Claude.
- **agentmath-05** ✅ What gamification features keep AgentMath students engaged?
  - AgentMath includes gamification features such as badges, avatars, leaderboards, and a Points for Prizes reward system to keep students engaged.
- **inmytime-01** ✅ Does In My Time store the family stories it collects?
  - In My Time does not store the family stories it collects. The server relays each answer in the same request and stores nothing, keeping no message text or transcriptions. The database only stores timestamps and the author's position in the question sequence, with no column capable of holding an answer. Even the admin view never shows story content, only progress metrics.
- **inmytime-02** ✅ How does In My Time get the grandparent's consent?
  - In My Time obtains the grandparent's consent by sending them a single WhatsApp consent message, and the process only starts once the grandparent replies to that message, ensuring consent is in their hands.
- **inmytime-03** ✅ What is StoryCatcher?
  - StoryCatcher is a module within the In My Time project that allows family members to record interviews with relatives directly in the browser. It features guided interviews using curated question packs, client-side encryption for recordings and names, per-interviewee access control enforced server-side, photo capture during recordings, and bring-your-own storage options such as Cloudflare R2 or Google Drive. It also includes a LifeLine timeline that pins clips and notes to decades and themes alo
- **inmytime-04** ✅ Why were admin WhatsApp alerts failing silently, and how was it fixed?
  - Admin WhatsApp alerts were failing silently because WhatsApp's 24-hour session rule only delivers free-form messages while a conversation is open. The fix was to add an automatic fallback to a pre-approved template message, with tests covering both the free-form and template message paths.
- **inmytime-05** ❌ Has Barry built multilingual or internationalised software?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **inmytime-06** ✅ What browser testing has Barry done?
  - Barry has done browser tests that exercise real encryption and media playback as part of the In My Time project, demonstrating careful product thinking and privacy by design.
- **brief-01** ✅ What is Brief?
  - Brief is a journaling app designed to ask users for only thirty words a week as a snapshot of their current state, helping them track personal change over time. It features a 16-week prompt cycle with anchor and texture questions, supports groups and anonymous public feeds, and offers privacy-first data handling with full export and permanent deletion. Users receive prompts via WhatsApp or email and can interact through an installable web app with Google, Microsoft, or email sign-in. The project
- **brief-02** ✅ How did Barry handle a leaked credential incident?
  - Barry handled the leaked credential incident by rotating every exposed secret (Google, Microsoft, and Twilio) to invalidate the leaked values, rebuilding the Git history as a single clean commit, and locking the repository down with a strict .gitignore for databases, configuration, and backups. He learned to reset the Git history rather than just untracking files if a first commit ever contained a secret.
- **brief-03** ✅ Why did weekly prompts drift off schedule, and how was it fixed?
  - Weekly prompts drifted off schedule because the system tracked each user's week position as a stored counter that could fall out of step, causing some users to receive prompts on an 8-day cycle instead of 7 or for the prompt cycle to stall. Barry fixed this by rebuilding the system so the week is calculated purely from time (from sign-up to now), eliminating the possibility of schedule drift. He also back-filled existing users with a one-off migration to align their schedules.
- **brief-04** ✅ How did Barry fix HTTPS certificates that would not validate?
  - Barry fixed HTTPS certificate validation failures by moving the DNS hosting to Cloudflare and setting the DNS records to DNS-only mode. This approach resolved the certificate issuance problems caused by the registrar's DNS setup. He applied this fix in both the my30words and In My Time projects.
- **brief-05** ✅ What are time capsules in Brief?
  - In Brief, time capsules are a feature that allows users to seal an entry for 1, 5, or 10 years, effectively locking the content for that duration before it can be accessed again.
- **askbarry-01** ❌ What is the Ask Barry project?
  - Ask Barry is an AI assistant that answers questions about Barry Sisk's software projects using only the README and documentation files in his public GitHub repositories, citing the repository, file, and section behind every answer. It is designed as a portfolio assistant for recruiters, interviewers, and developers to get quick, sourced answers about Barry's work. The project includes a Flask app with CI and Render deployment, document fetching and chunking, Azure AI Search with embeddings, grou
- **trap-01** ✅ Has Barry used Kubernetes?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-02** ✅ Does Barry have AWS experience?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-03** ✅ Has Barry built native mobile apps in Swift or Kotlin?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-04** ✅ Has Barry built front ends with React?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-05** ✅ Does Barry have a PhD?
  - Barry is completing a Higher Diploma in Software Development at Maynooth University, planned for 2027. There is no mention of a PhD in the documentation. (judge: The answer explicitly states there is no mention of a PhD and only mentions a Higher Diploma.)
- **trap-06** ✅ Has Barry used MongoDB?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-07** ✅ Has Barry trained a YOLOv8 model?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **trap-09** ✅ Has Barry worked with Apache Kafka?
  - I can't find evidence of that in Barry's public GitHub documentation.
- **askbarry-02** ✅ Has Barry deployed a RAG system to production?
  - Barry has deployed a retrieval-augmented generation (RAG) system to production in the Ask Barry project. It uses Azure AI Search for hybrid retrieval and Azure OpenAI's gpt-4.1-mini for grounded answering with citations, running as a Flask app with CI and Render deployment. The system enforces honesty rules by refusing answers without valid citations and includes answer-quality evaluation with an evidence-checking LLM judge. This RAG system is live in production as of Stage 6 completion.
