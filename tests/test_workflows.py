"""The nightly refresh workflow must pass every setting the ingest step needs, stay read-only,
and sign in to Azure with GitHub OIDC rather than stored keys (ASK-34)."""
import json
import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "refresh-index.yml"
KEY_MODE_SETTINGS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_EMBED_DEPLOYMENT",
                     "AZURE_SEARCH_ENDPOINT", "AZURE_SEARCH_API_KEY")
ENTRA_SETTINGS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_EMBED_DEPLOYMENT", "AZURE_SEARCH_ENDPOINT")


def test_refresh_workflow_passes_every_ingest_setting_from_secrets():
    text = WORKFLOW.read_text(encoding="utf-8")
    for name in ENTRA_SETTINGS:
        assert text.count(f"{name}: ${{{{ secrets.") == 3, f"{name} missing from a step in refresh-index.yml"


def test_refresh_workflow_runs_the_pipeline_in_order_and_is_read_only():
    text = WORKFLOW.read_text(encoding="utf-8")
    steps = [text.index(f"python -m scripts.{s}") for s in ("fetch_docs", "chunk_corpus", "ingest")]
    assert steps == sorted(steps)
    assert "contents: read" in text and "--allow-large-delete" not in text
    assert "schedule:" in text and "workflow_dispatch:" in text


def test_ingest_requires_exactly_these_settings():
    import inspect

    import scripts.ingest as ingest
    from app.azure_auth import required_settings
    assert "required_settings()" in inspect.getsource(ingest.main)
    def without_chat(env):
        return sorted(n for n in required_settings(env) if n != "AZURE_OPENAI_CHAT_DEPLOYMENT")
    assert without_chat({"AZURE_AUTH_MODE": "key"}) == sorted(KEY_MODE_SETTINGS)
    assert without_chat({"AZURE_AUTH_MODE": "entra"}) == sorted(ENTRA_SETTINGS)


def test_refresh_workflow_signs_in_with_oidc_and_holds_no_keys():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "id-token: write" in text
    assert "API_KEY" not in text and "ADMIN_KEY" not in text and "AZURE_AUTH_MODE: key" not in text
    assert text.count("AZURE_AUTH_MODE: entra") == 3          # sync, quality check, capability build
    # The IDs come from repository variables: identifiers, not secrets.
    assert "client-id: ${{ vars.AZURE_CLIENT_ID }}" in text and "secrets.AZURE_CLIENT_SECRET" not in text


def test_every_azure_step_has_a_fresh_sign_in_just_before_it():
    """GitHub's OIDC token is short-lived, so each Azure step gets its own azure/login."""
    steps = re.split(r"\n      - ", WORKFLOW.read_text(encoding="utf-8"))
    for i, step in enumerate(steps):
        if "AZURE_AUTH_MODE: entra" in step:
            assert "uses: azure/login@" in steps[i - 1], step.splitlines()[0]


def test_refresh_workflow_checks_retrieval_with_the_production_retriever():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "--retriever azure-hybrid-noname --min-section-recall" in text
    assert text.index("python -m scripts.ingest") < text.index("python -m scripts.evaluate_retrieval")


def test_capability_is_built_after_the_quality_check_and_published_by_a_separate_job():
    """ASK-42: only the publish job can write to the repo, and it commits only when the content changed."""
    import yaml
    text = WORKFLOW.read_text(encoding="utf-8")
    assert text.index("scripts.evaluate_retrieval") < text.index("scripts.build_capability")
    jobs = yaml.safe_load(text)["jobs"]
    assert "permissions" not in jobs["refresh"]                       # inherits read-only contents
    publish = jobs["publish-capability"]
    assert publish["needs"] == "refresh" and publish["permissions"] == {"contents": "write"}
    commit = publish["steps"][-1]["run"]
    assert "same_content" in commit and "No change: nothing to commit." in commit
    assert "git add data/capability.json data/capability_suggestions.json" in commit


def test_the_publish_check_runs_with_the_standard_library_only(tmp_path):
    """The publish job installs nothing, so its change check must not import the app (it once did: no flask)."""
    import re
    import subprocess
    import sys
    import yaml
    commit = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["publish-capability"]["steps"][-1]["run"]
    script = re.search(r"<<'PY'\n(.*?)\n\s*PY\n", commit, re.S).group(1)
    script = "\n".join(line[len("          "):] if line.startswith("          ") else line
                       for line in script.splitlines())
    assert "from app" not in script and "import app" not in script
    (tmp_path / "build").mkdir()
    (tmp_path / "data").mkdir()

    def run():
        out = subprocess.run([sys.executable, "-I", "-S", "-"], input=script, text=True, cwd=tmp_path,
                             capture_output=True, check=True)       # -S: no site-packages, like the runner
        return out.stdout.strip()

    old = {"generated_at": "2026-10-09T03:30:00Z", "skills": [{"id": "x", "tier": 2}]}
    for name in ("capability.json", "capability_suggestions.json"):
        (tmp_path / "data" / name).write_text(json.dumps(old))
        (tmp_path / "build" / name).write_text(json.dumps({**old, "generated_at": "2026-10-10T03:30:00Z"}))
    assert run() == ""                                               # only the time changed
    (tmp_path / "build" / "capability.json").write_text(json.dumps({**old, "skills": [{"id": "x", "tier": 3}]}))
    assert run() == "capability.json"

    from app.capability.builder import same_content                 # and it agrees with the app's rule
    a, b = old, {**old, "generated_at": "later"}
    assert same_content(a, b) and not same_content(a, {**old, "skills": []})


def test_nightly_data_never_goes_to_main():
    """ASK-62: the publish job writes only the capability-data branch, so main can require pull requests.
    (It replaced ASK-54's rebase-onto-main loop: with no data commits on main, a merge can't race the publish.)"""
    import yaml
    text = WORKFLOW.read_text(encoding="utf-8")
    publish = yaml.safe_load(text)["jobs"]["publish-capability"]
    run = "\n".join(step.get("run", "") for step in publish["steps"])
    assert "git push origin capability-data" in run
    assert run.count("git push") == 1 and "main" not in run and "--force" not in run
    assert all(step.get("with", {}).get("ref") in (None, "capability-data") for step in publish["steps"])
    # the builder reads the last published build from the same branch, falling back to main's snapshot
    assert "git show FETCH_HEAD:data/capability.json > build/previous.json" in text
    assert "--previous build/previous.json" in text


def test_the_live_app_reads_the_data_branch():
    import yaml
    env = {e["key"]: e.get("value") for e in
           yaml.safe_load((WORKFLOW.parents[2] / "render.yaml").read_text(encoding="utf-8"))["services"][0]["envVars"]}
    assert env["CAPABILITY_SOURCE"] == ("https://raw.githubusercontent.com/BBSISK/ask-barry/capability-data/"
                                        "data/capability.json")


CI = WORKFLOW.parent / "ci.yml"


def _job(text, name):
    start = text.index(f"\n  {name}:\n")
    nxt = re.search(r"\n  [a-z_-]+:\n", text[start + 1:])
    return text[start: start + 1 + nxt.start()] if nxt else text[start:]


def test_ci_runs_every_security_scanner_pinned_and_read_only():
    """ASK-59: shift-left checks. Each scanner is pinned so a new release can't change the gate silently."""
    job = _job(CI.read_text(encoding="utf-8"), "security")
    assert "contents: read" in job and "contents: write" not in job
    assert "pip-audit==2.10.1" in job and "pip-audit -r requirements.txt" in job
    assert "bandit==1.9.4" in job and "bandit -q -r app scripts ask_barry_mcp.py wsgi.py -ll" in job
    assert "checkov==3.3.28" in job and "checkov -d infra --framework terraform" in job
    assert "|| true" not in job and "continue-on-error" not in job      # a finding must fail the build


def test_gitleaks_scans_the_whole_history_with_a_verified_download():
    job = _job(CI.read_text(encoding="utf-8"), "security")
    assert "fetch-depth: 0" in job                                     # every commit, not just the last
    assert re.search(r'GITLEAKS_SHA256: "[0-9a-f]{64}"', job) and "sha256sum -c -" in job
    assert job.index("sha256sum -c -") < job.index("./gitleaks git")
    assert "--redact" in job                                           # a found secret never reaches the log


def test_gitleaks_allowlist_covers_only_the_fake_test_keys():
    text = (WORKFLOW.parents[2] / ".gitleaks.toml").read_text(encoding="utf-8")
    assert "useDefault = true" in text
    assert re.findall(r"paths = \['''(.+?)'''\]", text) == [r"^tests/test_check_azure\.py$"]


def test_every_security_skip_carries_a_reason():
    root = WORKFLOW.parents[2]
    for path in list((root / "infra").glob("*.tf")) + list((root / "app").rglob("*.py")) + \
            list((root / "scripts").glob("*.py")) + [root / "ask_barry_mcp.py"]:
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if "checkov:skip=" in line:
                assert re.search(r"checkov:skip=CKV2?_[A-Z]+_\d+:\s*\S", line), f"{path.name}:{i + 1}"
            if "# nosec" in line:
                assert lines[i - 1].strip().startswith("#"), f"{path.name}:{i + 1} needs a reason above it"


def test_dependabot_watches_python_packages_and_actions():
    text = (WORKFLOW.parent.parent / "dependabot.yml").read_text(encoding="utf-8")
    assert 'package-ecosystem: "pip"' in text and 'package-ecosystem: "github-actions"' in text
    assert 'versioning-strategy: "increase-if-necessary"' in text      # no PRs that only raise a minimum
