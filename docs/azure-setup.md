# Stage 3: Azure setup

This guide creates the three Azure pieces Ask Barry needs. Everything is done in the portal first (good AI-901 practice); Terraform can codify it later (Stage 7).

| Piece | What it's for | Tier |
|---|---|---|
| Microsoft Foundry resource (Azure OpenAI) | `text-embedding-3-small` for embeddings; a small chat model for answers | Pay per use (pennies) |
| Azure AI Search | Stores the chunks and vectors; hybrid keyword + vector search | **Free** (50 MB, 3 indexes) |
| Budget alert | Emails you before spending gets anywhere near real money | Free |

Written 27 Sep 2026. Azure's portal changes often, so if a button has moved, search the portal for the item's name.

---

## Step 1: Get a subscription

**Try Azure for Students first** (no credit card): https://azure.microsoft.com/free/students, signing up with your Maynooth email. It gives $100 credit for 12 months.

⚠️ **Known limitation:** several Microsoft Q&A threads in 2026 report that Azure for Students subscriptions get **zero quota for Azure OpenAI models**, and that they limit which regions you can deploy to. You'll find out in Step 4. If the model deployment is blocked, use **Option B**:

**Option B: a normal subscription with a budget.** Create a Pay-As-You-Go or free-account subscription (credit card required) and do Step 2 immediately. This project's AI usage should cost well under €1 a month.

### Check which regions you're allowed (Azure for Students only)
Portal → search **Policy** → **Authoring → Assignments** → open **Allowed resource deployment regions** → **Parameters**. Note the list. Pick one region from it that also supports Foundry and AI Search. In Europe, **Sweden Central** is the usual choice if it's allowed.

## Step 2: Budget alert (do this before creating anything)

Portal → **Cost Management + Billing** → **Budgets** → **+ Add**
- Scope: your subscription
- Amount: **€5** per month
- Alerts: 50% and 90% of **actual**, plus 100% of **forecasted**, sent to your email

(Azure for Students has a built-in spending limit: when the credit runs out, services stop rather than charging you. The budget is still worth adding.)

## Step 3: Resource group

Portal → **Resource groups** → **+ Create**
- Name: `rg-ask-barry`
- Region: your chosen region (e.g. Sweden Central)

Everything below goes in this group, so deleting the group later removes everything.

## Step 4: Foundry resource and model deployments

1. Go to **https://ai.azure.com** (Microsoft Foundry portal) and sign in.
2. **Create a new project**. Let it create a new **Foundry resource** in `rg-ask-barry` and your region. Name the resource something like `ask-barry-ai`.
3. In the project, open **Models + endpoints** (or **Deployments**) → **Deploy model** → **Deploy base model**:
   - **`text-embedding-3-small`**. Deployment name: `text-embedding-3-small`. Type: **Global Standard**. Reduce the rate limit to something small (e.g. 10K tokens per minute).
   - **A small chat model:** `gpt-5.4-mini` (retires Sep 2027) or `gpt-4.1-mini` (retires Apr 2027). Deployment name: the same as the model name. Type: **Global Standard**. Small rate limit.
   - Avoid `gpt-4o-mini`: it's marked as retiring, with no new deployments.
4. If you see **"quota insufficient"** or the deploy button is disabled, that's the Azure for Students limit. Switch to Option B in Step 1.
5. Get the endpoint and key: open the resource's **Overview** or **Keys and Endpoint**.
   - **Endpoint:** the one ending in `.openai.azure.com` (a `.services.ai.azure.com` one works too)
   - **Key 1** (keep Key 2 spare, for rotating the key without downtime later)

> Data zone note: **Global Standard** may process requests in any Azure region. For EU-only processing choose **Data Zone Standard** where offered. For public README content either is fine, but it's a good point to mention in the model card.

## Step 5: Azure AI Search (Free tier)

Portal → **+ Create a resource** → **Azure AI Search** →
- Resource group `rg-ask-barry`, a globally unique name such as `ask-barry-search`, same region
- **Pricing tier: Free** (click *Change pricing tier*). You're allowed only one free service per subscription.
- If the region says Free isn't available, try another allowed region. Don't pick a paid tier by accident: Basic costs around $70+/month.

After it's created: **Overview** → copy the **URL** (`https://<name>.search.windows.net`), then **Settings → Keys** → copy the **Primary admin key**.

## Step 6: Put the values in `.env` (never commit them)

```
AZURE_OPENAI_ENDPOINT=https://ask-barry-ai.openai.azure.com
AZURE_OPENAI_API_KEY=<Key 1>
AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-3-small
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5.4-mini
AZURE_SEARCH_ENDPOINT=https://ask-barry-search.search.windows.net
AZURE_SEARCH_API_KEY=<Primary admin key>
AZURE_SEARCH_INDEX=ask-barry-chunks
```

`.env` is in `.gitignore`. Before every commit, `git status` must never list it. The keys go into the Render dashboard only in Stage 5, when the live app needs them.

## Step 7: Verify

```bash
python -m scripts.check_azure
```

Expected:
```
PASS  Azure OpenAI embeddings: 1536-dimension vector
PASS  Azure OpenAI chat: model replied 'ready'
PASS  Azure AI Search: reachable, 0 index(es) so far
```

## Step 8: Sign in with Entra ID instead of keys (ASK-8)

Keys are all-or-nothing: anyone holding the Search admin key can delete the index. With Entra ID the app proves who it is and gets a token, and Azure role assignments decide what that identity may do. The code uses `DefaultAzureCredential` (see `app/azure_auth.py`), which picks the right sign-in for where it runs:

| Where | Signs in as | Roles |
|---|---|---|
| Your laptop | you, via `az login` | OpenAI User, Search Index Data Contributor, Search Service Contributor |
| Render | the `ask-barry-render` service principal | Cognitive Services OpenAI User, Search Index Data Reader |
| Azure compute (later) | a managed identity: no secret at all | same as Render |

Render isn't Azure, so it can't have a managed identity. A service principal still needs one secret, but it is scoped to two read-and-call roles, expires, and can be rotated without touching the Azure resources.

1. **Create the identity and roles** (`infra/identity.tf`):
   ```bash
   az login
   cd infra && terraform init -upgrade && terraform plan
   ```
   Expect only additions (the app registration, its service principal, five role assignments), nothing changed or destroyed. Then `terraform apply`.
2. **Check Search accepts tokens.** `az search service show -n ask-barry-search -g rg-ask-barry --query authOptions` should mention `aadOrApiKey`. If it says `apiKeyOnly`:
   `az search service update -n ask-barry-search -g rg-ask-barry --auth-options aadOrApiKey --aad-auth-failure-mode http401WithBearerChallenge`
3. **Try it locally.** In `.env` set `AZURE_AUTH_MODE=entra` and comment out both keys, then run `python -m scripts.check_azure`. New role assignments can take 5–10 minutes to apply; a `401`/`403` straight after `apply` usually just means wait.
4. **Create the Render secret** with the CLI, so it never enters Terraform state:
   ```bash
   az ad app credential reset --id "$(terraform output -raw render_client_id)" --display-name render --years 1 --query password -o tsv
   ```
5. **Render → Environment:** set `AZURE_TENANT_ID` and `AZURE_CLIENT_ID` (from `terraform output`) and `AZURE_CLIENT_SECRET`. After the deploy, `/ready` must say `ready`; then delete `AZURE_OPENAI_API_KEY` and `AZURE_SEARCH_API_KEY` from Render.
6. **The nightly index refresh signs in with GitHub OIDC (ASK-34), so GitHub stores no Azure secret at all.** Terraform creates the `ask-barry-github` app registration with a federated credential that Entra accepts only from this repo's `main` branch. In GitHub → Settings → Secrets and variables → Actions → **Variables**, set `AZURE_CLIENT_ID` (`terraform output -raw github_client_id`) and `AZURE_TENANT_ID`. Run the workflow by hand once, then delete the old key secrets.
7. **Turn keys off** (`local_auth_enabled = false` on both resources in `infra/main.tf`) once nothing uses them, then rotate the old keys so any copy left anywhere is useless.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `401` / `Access denied` | Wrong key, or a key from a different resource |
| `401` / `403` in Entra mode | Role assignment not applied yet (wait 5–10 min), not `az login`-ed, or Search still `apiKeyOnly` (Step 8) |
| `404` / `DeploymentNotFound` | The deployment *name* in `.env` doesn't match the name you gave it in Foundry |
| `429` | Rate limit too low, or quota exhausted; wait a minute |
| Quota insufficient when deploying | Azure for Students limitation (use Option B), **or** a new Pay-As-You-Go subscription with a 0 allowance for that model (common in 2026). In Foundry → Manage quota, turn on **Show all** to see each model's allowance, deploy a model that has some, or use **Request quota** (ask for ~10K tokens per minute; approval takes hours to days). Embeddings are enough for Stage 4 |
| Policy error when creating a resource | Region not in your subscription's allowed list (Step 1) |
| Embeddings `expected 1536` | You deployed `text-embedding-3-large` (3072 dims); use `-small` |

## AI-901 concepts this stage practises
Microsoft Foundry resources and projects, model catalog and deployments, deployment types (Global / Data Zone / Standard), quotas and rate limits, keys vs Microsoft Entra ID authentication, Azure AI Search tiers, resource groups, and cost management.
