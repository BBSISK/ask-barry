"""Fetch documentation files from Barry's PUBLIC GitHub repositories.

Usage (from the project root):
    python -m scripts.fetch_docs                 # owner defaults to BBSISK
    python -m scripts.fetch_docs --owner BBSISK --out corpus

What it does:
  1. Lists the owner's public repositories (forks and private repos are skipped).
  2. For each repo, reads the file tree at the latest commit of the default branch.
  3. Selects documentation files (see select_doc_paths) and downloads them,
     pinned to that commit SHA so every citation points at an exact version.
  4. Writes the files to corpus/<repo>/<path> and a corpus/manifest.json.

Only the Python standard library is used. Set GITHUB_TOKEN (read-only) to raise
the API rate limit; it is optional for a handful of public repos.
"""
import argparse
import json
import os
import posixpath
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"

DOC_EXTENSIONS = (".md", ".markdown")
# Folders that hold third-party or generated content, never Barry's own docs.
EXCLUDED_DIRS = {"node_modules", "vendor", "venv", ".venv", "site-packages", "dist", "build", ".github"}
# Individual files that are public but are not evidence of Barry's work
# (e.g. interview rehearsal notes, domain reference catalogues). Edit as needed.
DEFAULT_EXCLUDED_PATHS = (
    "wall_inspector/INTERVIEW_ARCHITECTURE_GUIDE.md",
    "wall_inspector/worked_examples_catalog.md",
)
MIN_BYTES = 50          # skip empty placeholder READMEs
MAX_BYTES = 200_000     # skip anything suspiciously large


# ---------------------------------------------------------------------------
# Pure selection logic (unit-tested, no network)
# ---------------------------------------------------------------------------

def select_repos(repos, exclude=()):
    """Keep public, non-fork repos not in the exclude list."""
    excluded = {name.lower() for name in exclude}
    return [
        r for r in repos
        if not r.get("private", True)
        and not r.get("fork", False)
        and r.get("name", "").lower() not in excluded
    ]


def is_doc_path(path, size=None):
    """Decide whether a repo file counts as documentation.

    Included: Markdown files at the repo root, anywhere under docs/,
    and README files at any depth. Excluded: vendored/generated folders,
    empty placeholders and very large files.
    """
    parts = path.split("/")
    if any(p in EXCLUDED_DIRS for p in parts[:-1]):
        return False
    name = parts[-1]
    if not name.lower().endswith(DOC_EXTENSIONS):
        return False
    if size is not None and not (MIN_BYTES <= size <= MAX_BYTES):
        return False
    at_root = len(parts) == 1
    in_docs = parts[0].lower() == "docs"
    is_readme = posixpath.splitext(name)[0].lower() == "readme"
    return at_root or in_docs or is_readme


def select_doc_paths(tree):
    """Filter a GitHub git-tree listing down to documentation blobs."""
    return sorted(
        item["path"] for item in tree
        if item.get("type") == "blob" and is_doc_path(item["path"], item.get("size"))
    )


def blob_url(owner, repo, sha, path):
    """Human-readable GitHub link to a file at an exact commit."""
    return f"https://github.com/{owner}/{repo}/blob/{sha}/{urllib.parse.quote(path)}"


def raw_url(owner, repo, sha, path):
    return f"{RAW}/{owner}/{repo}/{sha}/{urllib.parse.quote(path)}"


# ---------------------------------------------------------------------------
# Network layer (kept thin so tests can swap in a fake)
# ---------------------------------------------------------------------------

class GitHubClient:
    def __init__(self, token=None, timeout=30):
        self.token = token
        self.timeout = timeout

    def _request(self, url, accept):
        headers = {"Accept": accept, "User-Agent": "ask-barry-fetch-docs"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return resp.read()

    def get_json(self, url):
        return json.loads(self._request(url, "application/vnd.github+json"))

    def get_text(self, url):
        return self._request(url, "text/plain").decode("utf-8", errors="replace")


def list_public_repos(client, owner):
    repos, page = [], 1
    while True:
        batch = client.get_json(f"{API}/users/{owner}/repos?type=owner&per_page=100&page={page}")
        repos.extend(batch)
        if len(batch) < 100:
            return repos
        page += 1


def fetch_repo_docs(client, owner, repo, exclude_paths=()):
    """Return (commit_sha, [(path, text), ...]) for one repo.

    exclude_paths: "repo/path" strings for individual files to leave out.
    """
    branch = repo["default_branch"]
    name = repo["name"]
    branch_info = client.get_json(f"{API}/repos/{owner}/{name}/branches/{urllib.parse.quote(branch, safe='/')}")
    sha = branch_info["commit"]["sha"]
    tree = client.get_json(f"{API}/repos/{owner}/{name}/git/trees/{sha}?recursive=1")
    if tree.get("truncated"):
        print(f"  warning: tree for {name} was truncated by GitHub; some docs may be missing", file=sys.stderr)
    docs = []
    skip = {p.lower() for p in exclude_paths}
    for path in select_doc_paths(tree.get("tree", [])):
        if f"{name}/{path}".lower() in skip:
            print(f"  skipping excluded file {name}/{path}")
            continue
        docs.append((path, client.get_text(raw_url(owner, name, sha, path))))
    return sha, docs


def fetch_all(client, owner, out_dir, exclude=(), exclude_paths=()):
    """Fetch every public repo's docs into out_dir and write manifest.json."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest = {"owner": owner, "fetched_at": fetched_at, "documents": []}

    for repo in select_repos(list_public_repos(client, owner), exclude):
        name = repo["name"]
        sha, docs = fetch_repo_docs(client, owner, repo, exclude_paths)
        print(f"{name}: {len(docs)} doc file(s) @ {sha[:7]}")
        for path, text in docs:
            dest = out_dir / name / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
            manifest["documents"].append({
                "repo": name,
                "path": path,
                "commit_sha": sha,
                "url": blob_url(owner, name, sha, path),
                "local_path": f"{name}/{path}",
                "bytes": len(text.encode("utf-8")),
            })

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--owner", default=os.getenv("GITHUB_OWNER", "BBSISK"))
    parser.add_argument("--out", default="corpus")
    parser.add_argument("--exclude", nargs="*", default=[], help="repo names to skip")
    parser.add_argument("--exclude-paths", nargs="*", default=None,
                        help='files to skip as "repo/path" (default: see DEFAULT_EXCLUDED_PATHS)')
    args = parser.parse_args(argv)

    client = GitHubClient(token=os.getenv("GITHUB_TOKEN") or None)
    exclude_paths = DEFAULT_EXCLUDED_PATHS if args.exclude_paths is None else args.exclude_paths
    try:
        manifest = fetch_all(client, args.owner, args.out, args.exclude, exclude_paths)
    except urllib.error.HTTPError as err:
        if err.code in (403, 429):
            sys.exit(
                "GitHub API rate limit reached (60 requests/hour without a token).\n"
                "Wait an hour, or run with a read-only token, e.g.:\n"
                "  GITHUB_TOKEN=$(gh auth token) python -m scripts.fetch_docs"
            )
        raise
    repos = {d["repo"] for d in manifest["documents"]}
    print(f"\nDone: {len(manifest['documents'])} files from {len(repos)} repos -> {args.out}/manifest.json")


if __name__ == "__main__":
    main()
