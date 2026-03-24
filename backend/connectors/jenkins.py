"""
Jenkins API Connector
Fetches real build data: jobs, builds, logs.
Falls back to demo mode when Jenkins is unreachable.
"""

import os
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

JENKINS_URL = os.getenv("JENKINS_URL", "http://localhost:8080")
JENKINS_USER = os.getenv("JENKINS_USER", "admin")
JENKINS_TOKEN = os.getenv("JENKINS_TOKEN", "")

# ── Demo data templates ───────────────────────────────────────────────────────

_DEMO_JOBS = [
    "backend-deploy", "frontend-build", "ml-pipeline", "integration-tests", "data-etl"
]

_FAIL_LOGS = [
    "ERROR: NullPointerException at com.example.Service:42\nBuild failed after 3 retries.",
    "FATAL: Out of memory – Java heap space\nERROR: Build aborted.",
    "npm ERR! code ELIFECYCLE\nError: Process exited with status 1\nBuild FAILED",
    "CRITICAL segfault in worker thread\nAborted (core dumped)\nBUILD FAILURE",
    "TimeoutError: request to http://db:5432 timed out\nFATAL: Cannot connect to DB",
]
_OK_LOGS = [
    "BUILD SUCCESS\nTotal time: 45.23 s",
    "All tests passed (142/142)\nBUILD SUCCESS\nTotal time: 1m 03s",
    "Successfully built image sha256:abc1234\nPushed to registry.\nBUILD SUCCESS",
    "Deploying to production...\nDeployment complete.\nBUILD SUCCESS",
]


def _demo_builds(job_name: str, count: int = 10) -> list[dict]:
    """Generate realistic demo builds for a job."""
    builds = []
    now = datetime.utcnow()
    fail_rate = random.uniform(0.2, 0.5)
    for i in range(count, 0, -1):
        failed = random.random() < fail_rate
        duration_ms = random.randint(30_000, 300_000)
        ts = now - timedelta(hours=count - i) * random.randint(1, 4)
        builds.append({
            "job_name": job_name,
            "build_number": i,
            "status": "FAILURE" if failed else "SUCCESS",
            "duration_ms": duration_ms,
            "timestamp": ts.isoformat(),
            "url": f"{JENKINS_URL}/job/{job_name}/{i}/",
            "log": random.choice(_FAIL_LOGS if failed else _OK_LOGS),
            "demo": True,
        })
    return builds


# ── Real Jenkins calls ────────────────────────────────────────────────────────

class JenkinsConnector:
    def __init__(self):
        self.base = JENKINS_URL.rstrip("/")
        self.auth = HTTPBasicAuth(JENKINS_USER, JENKINS_TOKEN) if JENKINS_TOKEN else None
        self.timeout = 5  # seconds

    def _get(self, path: str) -> Optional[dict]:
        url = f"{self.base}{path}"
        try:
            resp = requests.get(url, auth=self.auth, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.debug(f"Jenkins GET {path} failed: {e}")
            return None

    def _get_text(self, path: str) -> Optional[str]:
        url = f"{self.base}{path}"
        try:
            resp = requests.get(url, auth=self.auth, timeout=self.timeout)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            logger.debug(f"Jenkins text GET {path} failed: {e}")
            return None

    # ── public API ─────────────────────────────────────────────────────────

    def is_reachable(self) -> bool:
        data = self._get("/api/json?tree=mode")
        return data is not None

    def list_jobs(self) -> list[dict]:
        """Return list of job dicts with name & last build status."""
        data = self._get("/api/json?tree=jobs[name,color,lastBuild[number,result]]")
        if data is None:
            logger.warning("Jenkins unreachable – using demo jobs")
            return [{"name": j, "demo": True} for j in _DEMO_JOBS]

        jobs = []
        for job in data.get("jobs", []):
            lb = job.get("lastBuild") or {}
            jobs.append({
                "name": job["name"],
                "color": job.get("color", "notbuilt"),
                "last_build_number": lb.get("number"),
                "last_build_result": lb.get("result"),
                "demo": False,
            })
        return jobs

    def get_builds(self, job_name: str, count: int = 10) -> list[dict]:
        """Return last `count` builds for a job, including logs."""
        path = (
            f"/job/{job_name}/api/json"
            f"?tree=builds[number,result,timestamp,duration,url]{{0,{count}}}"
        )
        data = self._get(path)
        if data is None:
            logger.warning(f"Jenkins unreachable – demo builds for {job_name}")
            return _demo_builds(job_name, count)

        builds = []
        for b in data.get("builds", []):
            log = self.get_build_log(job_name, b["number"])
            ts = datetime.utcfromtimestamp(b["timestamp"] / 1000).isoformat()
            builds.append({
                "job_name": job_name,
                "build_number": b["number"],
                "status": b.get("result") or "IN_PROGRESS",
                "duration_ms": b.get("duration", 0),
                "timestamp": ts,
                "url": b.get("url", ""),
                "log": log or "",
                "demo": False,
            })
        return builds

    def get_build_log(self, job_name: str, build_number: int) -> Optional[str]:
        """Fetch raw console log for a build (truncated to 2 KB)."""
        text = self._get_text(f"/job/{job_name}/{build_number}/consoleText")
        if text is None:
            return None
        return text[-2048:] if len(text) > 2048 else text

    def trigger_build(self, job_name: str) -> bool:
        """Trigger a new build (requires build token / proper auth)."""
        url = f"{self.base}/job/{job_name}/build"
        try:
            resp = requests.post(url, auth=self.auth, timeout=self.timeout)
            return resp.status_code in (200, 201)
        except Exception as e:
            logger.error(f"Trigger build failed: {e}")
            return False


# Module-level singleton
connector = JenkinsConnector()
