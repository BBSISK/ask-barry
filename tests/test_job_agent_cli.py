"""Batch mode of scripts/job_agent.py: a folder of ads -> one .md + .json report per company, offline."""
import asyncio
import json

import pytest

from app.job_agent import Report, Row, render_markdown
from scripts.job_agent import ad_files, run_many


def test_folder_mode_runs_every_txt_in_order(tmp_path):
    (tmp_path / "b-kerry.txt").write_text("ad b")
    (tmp_path / "a-accenture.txt").write_text("ad a")
    (tmp_path / "notes.md").write_text("ignored")
    assert [p.name for p in ad_files(tmp_path)] == ["a-accenture.txt", "b-kerry.txt"]


def test_empty_folder_is_an_error(tmp_path):
    with pytest.raises(ValueError):
        ad_files(tmp_path)


def test_batch_saves_md_and_json_named_after_each_file_and_skips_bad_ads(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    async def fake_run(text):
        if not text.strip():
            raise ValueError("Please paste a job advertisement.")
        return Report(role_title="Graduate Engineer", rows=[Row("Python", status="evidenced", sources=["u"])]), \
            {"tool_calls": 1, "seconds": 0.1, "tool_log": []}

    items = [("accenture", "ad text"), ("empty", "  "), ("kerry", "ad text")]
    done = asyncio.run(run_many(items, fake_run, render_markdown, save=True))
    assert [name for name, _ in done] == ["accenture", "kerry"]
    saved = sorted(p.name for p in (tmp_path / "reports").iterdir())
    assert len(saved) == 4 and all(("accenture" in n or "kerry" in n) for n in saved)
    data = json.loads(next((tmp_path / "reports").glob("*accenture.json")).read_text())
    assert data["requirements"][0]["requirement"] == "Python" and data["role_title"] == "Graduate Engineer"
