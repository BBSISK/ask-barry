import json

import pytest

from scripts.fetch_docs import blob_url, fetch_all, is_doc_path, select_doc_paths, select_repos


# --- repo selection ---------------------------------------------------------

def test_select_repos_skips_forks_private_and_excluded():
    repos = [
        {"name": "wall_inspector", "private": False, "fork": False},
        {"name": "someone-elses-lib", "private": False, "fork": True},
        {"name": "secret", "private": True, "fork": False},
        {"name": "old-experiment", "private": False, "fork": False},
    ]
    kept = select_repos(repos, exclude=["Old-Experiment"])
    assert [r["name"] for r in kept] == ["wall_inspector"]


def test_select_repos_treats_missing_private_flag_as_private():
    assert select_repos([{"name": "x", "fork": False}]) == []


# --- doc path selection -----------------------------------------------------

@pytest.mark.parametrize("path,expected", [
    ("README.md", True),
    ("INTERVIEW_ARCHITECTURE_GUIDE.md", True),      # root-level markdown
    ("docs/architecture.md", True),
    ("docs/deep/nested/notes.md", True),
    ("scripts/utils/README.md", True),              # READMEs at any depth
    ("app/templates/email.md", False),              # other nested markdown
    ("node_modules/pkg/README.md", False),          # vendored
    (".github/PULL_REQUEST_TEMPLATE.md", False),
    ("app.py", False),
    ("README.txt", False),
])
def test_is_doc_path(path, expected):
    assert is_doc_path(path, size=1000) is expected


def test_size_limits():
    assert not is_doc_path("README.md", size=8)          # placeholder
    assert not is_doc_path("README.md", size=5_000_000)  # too big
    assert is_doc_path("README.md", size=None)           # size unknown -> allowed


def test_select_doc_paths_only_blobs_sorted():
    tree = [
        {"path": "docs", "type": "tree"},
        {"path": "docs/b.md", "type": "blob", "size": 500},
        {"path": "README.md", "type": "blob", "size": 500},
        {"path": "main.py", "type": "blob", "size": 500},
    ]
    assert select_doc_paths(tree) == ["README.md", "docs/b.md"]


def test_blob_url_pins_commit_and_quotes_spaces():
    assert blob_url("BBSISK", "demo", "abc", "docs/my notes.md") == \
        "https://github.com/BBSISK/demo/blob/abc/docs/my%20notes.md"


# --- end-to-end with a fake GitHub client (no network) ----------------------

class FakeGitHub:
    def __init__(self):
        self.calls = []

    def get_json(self, url):
        self.calls.append(url)
        if "/users/BBSISK/repos" in url:
            return [
                {"name": "demo", "private": False, "fork": False, "default_branch": "main"},
                {"name": "forked", "private": False, "fork": True, "default_branch": "main"},
            ]
        if url.endswith("/repos/BBSISK/demo/branches/main"):
            return {"commit": {"sha": "abc1234567"}}
        if "/repos/BBSISK/demo/git/trees/abc1234567" in url:
            return {"truncated": False, "tree": [
                {"path": "README.md", "type": "blob", "size": 120},
                {"path": "src/app.py", "type": "blob", "size": 120},
            ]}
        raise AssertionError(f"unexpected URL {url}")

    def get_text(self, url):
        self.calls.append(url)
        assert url == "https://raw.githubusercontent.com/BBSISK/demo/abc1234567/README.md"
        return "# Demo\n\nHello from the demo repo, a Flask app with CI.\n"


def test_fetch_all_writes_files_and_manifest(tmp_path):
    client = FakeGitHub()
    manifest = fetch_all(client, "BBSISK", tmp_path)

    assert [d["repo"] for d in manifest["documents"]] == ["demo"]      # fork skipped
    doc = manifest["documents"][0]
    assert doc["path"] == "README.md"
    assert doc["commit_sha"] == "abc1234567"
    assert doc["url"] == "https://github.com/BBSISK/demo/blob/abc1234567/README.md"
    assert (tmp_path / "demo" / "README.md").read_text().startswith("# Demo")

    on_disk = json.loads((tmp_path / "manifest.json").read_text())
    assert on_disk["documents"] == manifest["documents"]
    assert not any("forked" in c for c in client.calls)               # fork never queried


def test_fetch_all_respects_excluded_paths(tmp_path):
    manifest = fetch_all(FakeGitHub(), "BBSISK", tmp_path, exclude_paths=["demo/README.md"])
    assert manifest["documents"] == []


def test_folder_exclusion_keeps_eval_reports_out_of_the_corpus():
    from scripts.fetch_docs import DEFAULT_EXCLUDED_PATHS, is_excluded
    assert is_excluded("ask-barry", "docs/eval/2026-09-27-bm25.md", DEFAULT_EXCLUDED_PATHS)
    assert not is_excluded("ask-barry", "docs/azure-setup.md", DEFAULT_EXCLUDED_PATHS)
    assert not is_excluded("ask-barry", "README.md", DEFAULT_EXCLUDED_PATHS)
    assert is_excluded("Wall_Inspector", "INTERVIEW_ARCHITECTURE_GUIDE.md", DEFAULT_EXCLUDED_PATHS)
