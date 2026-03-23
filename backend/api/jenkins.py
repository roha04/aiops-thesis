"""
Jenkins Integration API
- List jobs / builds from Jenkins (real or demo)
- Sync builds: fetch logs + run ML predictions
- Track actual failures vs predictions
- SSE endpoint for real-time streaming demo
"""

import asyncio
import json
import logging
import random
from datetime import datetime
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from db.config import get_db
from db.models import JenkinsBuild
from ml.pipeline import AIOpsPredictor
from connectors.jenkins import connector as jenkins

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jenkins", tags=["jenkins"])

_predictor = AIOpsPredictor()


# ─── helpers ──────────────────────────────────────────────────────────────────

def _run_prediction(log: str, job_name: str) -> dict:
    """Run ML prediction on a log string and return a structured dict."""
    try:
        result = _predictor.analyze(log, failure_history=None)
    except Exception as e:
        logger.error(f"Prediction error for {job_name}: {e}")
        result = {
            "risk_level": "UNKNOWN",
            "score": 0.0,
            "recommendation": "Prediction unavailable",
            "details": {"log_anomaly": {"is_anomaly": False, "confidence": 0}},
        }
    return result


def _upsert_build(db: Session, raw: dict, prediction: dict) -> JenkinsBuild:
    """Insert or update a JenkinsBuild row."""
    existing = (
        db.query(JenkinsBuild)
        .filter(
            JenkinsBuild.job_name == raw["job_name"],
            JenkinsBuild.build_number == raw["build_number"],
        )
        .first()
    )

    actual_failure = raw["status"] not in ("SUCCESS", "IN_PROGRESS")
    predicted_failure = prediction["details"]["log_anomaly"].get("is_anomaly", False)
    prediction_correct = (predicted_failure == actual_failure) if raw["status"] != "IN_PROGRESS" else None

    ts = None
    if raw.get("timestamp"):
        try:
            ts = datetime.fromisoformat(raw["timestamp"])
        except ValueError:
            ts = None

    if existing:
        existing.status = raw["status"]
        existing.duration_ms = raw.get("duration_ms")
        existing.log_snippet = (raw.get("log") or "")[:2000]
        existing.predicted_failure = predicted_failure
        existing.prediction_confidence = prediction["details"]["log_anomaly"].get("confidence")
        existing.risk_level = prediction["risk_level"]
        existing.risk_score = prediction["score"]
        existing.recommendation = prediction["recommendation"]
        existing.actual_failure = actual_failure
        existing.prediction_correct = prediction_correct
        existing.build_timestamp = ts
        existing.synced_at = datetime.utcnow()
        row = existing
    else:
        row = JenkinsBuild(
            job_name=raw["job_name"],
            build_number=raw["build_number"],
            status=raw["status"],
            duration_ms=raw.get("duration_ms"),
            build_url=raw.get("url", ""),
            log_snippet=(raw.get("log") or "")[:2000],
            is_demo=raw.get("demo", False),
            predicted_failure=predicted_failure,
            prediction_confidence=prediction["details"]["log_anomaly"].get("confidence"),
            risk_level=prediction["risk_level"],
            risk_score=prediction["score"],
            recommendation=prediction["recommendation"],
            actual_failure=actual_failure,
            prediction_correct=prediction_correct,
            build_timestamp=ts,
        )
        db.add(row)

    db.commit()
    db.refresh(row)
    return row


def _row_to_dict(row: JenkinsBuild) -> dict:
    return {
        "id": row.id,
        "job_name": row.job_name,
        "build_number": row.build_number,
        "status": row.status,
        "duration_ms": row.duration_ms,
        "build_url": row.build_url,
        "log_snippet": row.log_snippet,
        "is_demo": row.is_demo,
        "predicted_failure": row.predicted_failure,
        "prediction_confidence": row.prediction_confidence,
        "risk_level": row.risk_level,
        "risk_score": row.risk_score,
        "recommendation": row.recommendation,
        "actual_failure": row.actual_failure,
        "prediction_correct": row.prediction_correct,
        "build_timestamp": row.build_timestamp.isoformat() if row.build_timestamp else None,
        "synced_at": row.synced_at.isoformat() if row.synced_at else None,
    }


# ─── routes ───────────────────────────────────────────────────────────────────

@router.get("/status")
def jenkins_status():
    """Check whether Jenkins is reachable."""
    reachable = jenkins.is_reachable()
    return {
        "reachable": reachable,
        "mode": "live" if reachable else "demo",
        "url": jenkins.base,
    }


@router.get("/jobs")
def list_jobs():
    """Return all Jenkins jobs (or demo jobs if Jenkins is offline)."""
    jobs = jenkins.list_jobs()
    return {"jobs": jobs, "count": len(jobs)}


@router.get("/builds/{job_name}")
def get_builds(
    job_name: str,
    count: int = Query(default=10, ge=1, le=50),
):
    """Return raw builds for a job (no DB, no prediction)."""
    builds = jenkins.get_builds(job_name, count)
    return {"job_name": job_name, "builds": builds}


@router.post("/sync")
def sync_builds(
    job_name: Optional[str] = Query(default=None, description="Sync a single job; omit to sync all"),
    count: int = Query(default=10, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """
    Fetch builds from Jenkins, run ML predictions, persist to DB.
    Returns list of processed build records.
    """
    jobs_to_sync: list[str]

    if job_name:
        jobs_to_sync = [job_name]
    else:
        jobs = jenkins.list_jobs()
        jobs_to_sync = [j["name"] for j in jobs]

    synced = []
    for jname in jobs_to_sync:
        try:
            raw_builds = jenkins.get_builds(jname, count)
            for raw in raw_builds:
                log = raw.get("log") or ""
                prediction = _run_prediction(log, jname)
                row = _upsert_build(db, raw, prediction)
                synced.append(_row_to_dict(row))
        except Exception as e:
            logger.error(f"Sync failed for {jname}: {e}")

    return {
        "synced": len(synced),
        "builds": synced,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/history")
def build_history(
    job_name: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Return synced build history from DB, optionally filtered by job."""
    q = db.query(JenkinsBuild).order_by(JenkinsBuild.build_timestamp.desc())
    if job_name:
        q = q.filter(JenkinsBuild.job_name == job_name)
    rows = q.limit(limit).all()
    return {"builds": [_row_to_dict(r) for r in rows], "total": len(rows)}


@router.get("/comparison")
def prediction_comparison(
    job_name: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Aggregate: actual failures vs predicted failures per job."""
    q = db.query(JenkinsBuild).filter(JenkinsBuild.status != "IN_PROGRESS")
    if job_name:
        q = q.filter(JenkinsBuild.job_name == job_name)
    rows = q.all()

    per_job: dict[str, dict] = {}
    for r in rows:
        entry = per_job.setdefault(
            r.job_name,
            {
                "job_name": r.job_name,
                "total_builds": 0,
                "actual_failures": 0,
                "predicted_failures": 0,
                "correct_predictions": 0,
                "false_positives": 0,
                "false_negatives": 0,
            },
        )
        entry["total_builds"] += 1
        if r.actual_failure:
            entry["actual_failures"] += 1
        if r.predicted_failure:
            entry["predicted_failures"] += 1
        if r.prediction_correct is True:
            entry["correct_predictions"] += 1
        if r.predicted_failure and not r.actual_failure:
            entry["false_positives"] += 1
        if not r.predicted_failure and r.actual_failure:
            entry["false_negatives"] += 1

    result = list(per_job.values())
    for entry in result:
        total = entry["total_builds"]
        entry["accuracy"] = round(entry["correct_predictions"] / total, 3) if total else 0.0

    return {"comparison": result}


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    """High-level KPIs for the Jenkins dashboard card."""
    rows = db.query(JenkinsBuild).all()
    total = len(rows)
    actual_fail = sum(1 for r in rows if r.actual_failure)
    predicted_fail = sum(1 for r in rows if r.predicted_failure)
    correct = sum(1 for r in rows if r.prediction_correct is True)
    high_risk = sum(1 for r in rows if r.risk_level == "HIGH")

    return {
        "total_builds": total,
        "actual_failures": actual_fail,
        "predicted_failures": predicted_fail,
        "correct_predictions": correct,
        "overall_accuracy": round(correct / total, 3) if total else 0.0,
        "high_risk_builds": high_risk,
        "jenkins_mode": "live" if jenkins.is_reachable() else "demo",
    }


# ─── SSE real-time demo ───────────────────────────────────────────────────────

_DEMO_JOB_NAMES = [
    "backend-deploy", "frontend-build", "ml-pipeline",
    "integration-tests", "data-etl",
]
_FAIL_LOGS = [
    "ERROR: NullPointerException at Service:42\nBuild FAILED after 3 retries.",
    "FATAL: Out of memory – heap space\nERROR: Build aborted.",
    "npm ERR! ELIFECYCLE\nProcess exited with status 1\nBuild FAILED",
    "TimeoutError: DB connection timed out\nFATAL: Cannot connect\nBUILD FAILURE",
]
_OK_LOGS = [
    "All tests passed (142/142)\nBUILD SUCCESS",
    "Successfully pushed image sha256:abc1234\nBUILD SUCCESS",
    "Deploying to production... Done.\nBUILD SUCCESS",
]


async def _demo_stream(db: Session) -> AsyncGenerator[str, None]:
    """Yield SSE events: one build every ~1.5 s for up to 20 events."""
    build_num = random.randint(100, 200)
    for _ in range(20):
        await asyncio.sleep(1.5)
        job = random.choice(_DEMO_JOB_NAMES)
        failed = random.random() < 0.35
        log = random.choice(_FAIL_LOGS if failed else _OK_LOGS)

        raw = {
            "job_name": job,
            "build_number": build_num,
            "status": "FAILURE" if failed else "SUCCESS",
            "duration_ms": random.randint(30_000, 300_000),
            "timestamp": datetime.utcnow().isoformat(),
            "url": f"http://jenkins/{job}/{build_num}/",
            "log": log,
            "demo": True,
        }
        prediction = _run_prediction(log, job)
        row = _upsert_build(db, raw, prediction)
        payload = json.dumps(_row_to_dict(row))
        yield f"data: {payload}\n\n"
        build_num += 1

    yield "data: {\"done\": true}\n\n"


@router.get("/stream-demo")
async def stream_demo(db: Session = Depends(get_db)):
    """
    Server-Sent Events: stream 20 simulated Jenkins builds with live ML predictions.
    Frontend can consume via EventSource.
    """
    return StreamingResponse(
        _demo_stream(db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
