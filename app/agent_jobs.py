"""Stage 8d: run the job-ad evidence agent from the website as a background job.

One ad takes 30-60 s, longer than a web request should wait, so POST /api/evidence starts a job and
returns its id; the page polls GET /api/evidence/<id> and shows each tool call as it happens.

Deliberately small (free single-instance host):
  - jobs live in this process's memory, so the server runs ONE gunicorn worker (render.yaml);
  - at most MAX_RUNNING jobs at once (each run starts an MCP helper process, ~90 MB);
  - finished jobs are forgotten after JOB_TTL seconds, and the job ad text is never stored or logged:
    only the questions the agent asked and the evidence map are kept, for the page to display.
"""
import asyncio
import logging
import secrets
import threading
import time
from dataclasses import dataclass, field

from .job_agent import clean_job_ad, render_markdown

MAX_RUNNING = 1
JOB_TTL = 30 * 60
log = logging.getLogger(__name__)


class Busy(Exception):
    """Another evidence map is already being prepared."""


@dataclass
class Job:
    id: str
    status: str = "running"                 # running | done | error
    steps: list = field(default_factory=list)
    report: dict = None
    markdown: str = ""
    error: str = ""
    started: float = field(default_factory=time.time)
    finished: float = None

    def to_dict(self):
        return {"id": self.id, "status": self.status, "steps": list(self.steps), "report": self.report,
                "markdown": self.markdown, "error": self.error,
                "seconds": round((self.finished or time.time()) - self.started, 1), "ai_generated": True}


def default_runner(job_ad, on_call):
    """Runs the real agent (Azure + the ask_barry MCP server) in this thread's own event loop."""
    from .job_agent_runtime import run
    return asyncio.run(run(job_ad, on_call=on_call))


class JobStore:
    def __init__(self, runner=default_runner, clock=time.time):
        self.runner = runner
        self.clock = clock
        self._jobs = {}
        self._lock = threading.Lock()

    def _expire(self):
        now = self.clock()
        for job_id in [j.id for j in self._jobs.values() if j.finished and now - j.finished > JOB_TTL]:
            del self._jobs[job_id]

    def running(self):
        return sum(1 for j in self._jobs.values() if j.status == "running")

    def start(self, job_ad, wait=False):
        """Validate the ad, start a job, return it. Raises ValueError (bad ad) or Busy."""
        text = clean_job_ad(job_ad)
        with self._lock:
            self._expire()
            if self.running() >= MAX_RUNNING:
                raise Busy("Another evidence map is being prepared. Please try again in a minute.")
            job = Job(id=secrets.token_urlsafe(12), started=self.clock())
            self._jobs[job.id] = job
        thread = threading.Thread(target=self._work, args=(job, text), daemon=True)
        thread.start()
        if wait:                                   # tests
            thread.join()
        return job

    def _work(self, job, text):
        def on_call(call):
            job.steps.append({"question": call.question, "supported": call.supported, "links": len(call.urls)})
        try:
            report, _ = self.runner(text, on_call)
            job.report, job.markdown = report.to_dict(), render_markdown(report)
            job.status = "done"
            log.info("evidence map: rows=%d tool_calls=%d blocked=%s fallback=%s",
                     len(report.rows), len(job.steps), bool(report.blocked), report.fallback)
        except Exception:                          # never leak internals (or the ad) to the browser or logs
            log.exception("evidence map failed (ad length %d)", len(text))
            job.status, job.error = "error", "Sorry, something went wrong preparing the evidence map. Please try again."
        finally:
            job.finished = self.clock()

    def get(self, job_id):
        with self._lock:
            self._expire()
            return self._jobs.get(job_id)
