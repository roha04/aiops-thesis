"""
Generate synthetic labeled logs for ML training.
Produces 5000+ varied samples so TF-IDF learns meaningful patterns.
"""

import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.config import SessionLocal, engine
from db.models import TrainingData, Base

Base.metadata.create_all(bind=engine)

# ── Vocabulary banks ──────────────────────────────────────────────────────────

SERVICES  = ["auth-service", "api-gateway", "db-worker", "cache-manager",
             "scheduler", "build-runner", "test-executor", "deploy-agent",
             "metrics-collector", "log-aggregator", "notification-svc",
             "payment-svc", "user-svc", "order-svc", "inventory-svc"]

DURATIONS = ["12ms", "45ms", "123ms", "1.2s", "3.4s", "0.8s", "250ms", "78ms"]
PORTS     = ["8080", "5432", "6379", "3306", "27017", "9200", "5601", "9090"]
COUNTS    = ["142", "248", "512", "1024", "87", "334", "201", "43"]
VERSIONS  = ["v1.2.3", "v2.0.1", "v0.9.7", "v3.1.0", "v1.0.0-beta"]
BRANCHES  = ["main", "develop", "feature/auth", "hotfix/db", "release/2.0"]
ENVS      = ["staging", "production", "dev", "qa", "canary"]


def _svc():  return random.choice(SERVICES)
def _dur():  return random.choice(DURATIONS)
def _port(): return random.choice(PORTS)
def _cnt():  return random.choice(COUNTS)
def _ver():  return random.choice(VERSIONS)
def _br():   return random.choice(BRANCHES)
def _env():  return random.choice(ENVS)


# ── Normal log templates ──────────────────────────────────────────────────────

def _normal_templates():
    return [
        f"INFO [{_svc()}] Build started for branch {_br()}",
        f"INFO [{_svc()}] Running unit tests...",
        f"INFO [{_svc()}] Tests passed ({_cnt()}/{_cnt()})",
        f"INFO [{_svc()}] Building Docker image {_ver()}",
        f"INFO [{_svc()}] Pushing image to registry",
        f"INFO [{_svc()}] Deployment initiated on {_env()}",
        f"INFO [{_svc()}] Health checks passing",
        f"INFO [{_svc()}] Service started on port {_port()}",
        f"INFO [{_svc()}] Connected to database successfully",
        f"INFO [{_svc()}] Cache warmed up with {_cnt()} entries",
        f"INFO [{_svc()}] Configuration loaded from environment",
        f"INFO [{_svc()}] Listening on port {_port()}",
        f"INFO [{_svc()}] Request processed in {_dur()}",
        f"INFO [{_svc()}] Database query completed in {_dur()}",
        f"INFO [{_svc()}] Cache hit rate: 92%",
        f"INFO [{_svc()}] All {_cnt()} services healthy",
        f"INFO [{_svc()}] Backup completed in {_dur()}",
        f"INFO [{_svc()}] Load balancer health check OK",
        f"INFO [{_svc()}] API response time: {_dur()}",
        f"INFO [{_svc()}] Memory usage: 45%",
        f"INFO [{_svc()}] CPU usage: 22%",
        f"INFO [{_svc()}] Disk usage: 65%",
        f"INFO [{_svc()}] Compilation complete in {_dur()}",
        f"INFO [{_svc()}] Artifact created: app-{_ver()}.jar",
        f"INFO [{_svc()}] Deployed to {_env()} successfully",
        f"INFO [{_svc()}] Integration tests passed ({_cnt()} scenarios)",
        f"INFO [{_svc()}] Container image pull complete",
        f"INFO [{_svc()}] Smoke tests OK — all endpoints responding",
        f"INFO [{_svc()}] Metrics published to Prometheus",
        f"INFO [{_svc()}] Pipeline finished in {_dur()}",
        f"INFO [{_svc()}] Code coverage: 87% (threshold 80%)",
        f"INFO [{_svc()}] Linting complete — no issues",
        f"INFO [{_svc()}] Static analysis passed",
        f"INFO [{_svc()}] Seeds executed on {_env()} DB",
        f"INFO [{_svc()}] Migration v{random.randint(1,99):03d} applied",
        f"INFO [{_svc()}] Feature flag '{random.choice(['dark_mode','beta_api','v2_flow'])}' evaluated: enabled",
        f"INFO [{_svc()}] Session {random.randint(1000,9999)} authenticated",
        f"INFO [{_svc()}] Cleanup completed — {_cnt()} temp files removed",
        f"INFO [{_svc()}] Queue depth: {random.randint(0,20)} messages",
        f"INFO [{_svc()}] Graceful shutdown initiated",
        f"DEBUG [{_svc()}] Received request GET /api/health",
        f"DEBUG [{_svc()}] Cache key hit: user_{random.randint(1,999)}",
        f"DEBUG [{_svc()}] DB pool: {random.randint(1,8)}/10 connections active",
    ]


# ── Warning log templates (labeled normal — warnings don't always mean failure) ──

def _warning_templates():
    return [
        f"WARNING [{_svc()}] High memory usage detected (85%)",
        f"WARNING [{_svc()}] CPU spike detected (92%) — monitoring",
        f"WARNING [{_svc()}] Slow database query ({_dur()})",
        f"WARNING [{_svc()}] Deprecated API endpoint /v1/users called",
        f"WARNING [{_svc()}] Missing cache entries — falling back to DB",
        f"WARNING [{_svc()}] Disk usage high (78%) — consider cleanup",
        f"WARNING [{_svc()}] Thread pool at 80% capacity",
        f"WARNING [{_svc()}] Rate limit approaching (890/1000 req/min)",
        f"WARNING [{_svc()}] Connection pool low ({random.randint(1,3)}/10)",
        f"WARNING [{_svc()}] Response time degradation: {_dur()}",
        f"WARNING [{_svc()}] Retry attempt {random.randint(1,3)}/3 for {_svc()}",
        f"WARNING [{_svc()}] Certificate expires in {random.randint(7,30)} days",
    ]


# ── Anomaly / error log templates ─────────────────────────────────────────────

def _anomaly_templates():
    return [
        # Database
        f"ERROR [{_svc()}] Database connection timeout after 30s",
        f"ERROR [{_svc()}] Database connection lost — retrying",
        f"ERROR [{_svc()}] SQL query failed: Lock wait timeout exceeded",
        f"ERROR [{_svc()}] Connection refused from PostgreSQL on port {_port()}",
        f"ERROR [{_svc()}] Cannot acquire database connection from pool",
        f"ERROR [{_svc()}] Database pool exhausted — all connections in use",
        f"ERROR [{_svc()}] Transaction rollback: deadlock detected",
        f"FATAL [{_svc()}] Cannot connect to primary DB — failover failed",
        # Memory
        f"ERROR [{_svc()}] Memory allocation failed — OutOfMemoryError",
        f"FATAL [{_svc()}] JVM heap space exceeded — process killed",
        f"ERROR [{_svc()}] GC overhead limit exceeded — too much garbage",
        f"CRITICAL [{_svc()}] OOM killer triggered — container restarting",
        # Auth
        f"ERROR [{_svc()}] JWT token expired — authentication failed",
        f"ERROR [{_svc()}] Invalid API key — request rejected",
        f"ERROR [{_svc()}] LDAP authentication failed for user admin",
        f"ERROR [{_svc()}] Unauthorized access to /admin — 403 returned",
        # Network
        f"ERROR [{_svc()}] Port {_port()} already in use",
        f"ERROR [{_svc()}] Network unreachable to downstream {_svc()}",
        f"ERROR [{_svc()}] Connection refused by host 10.0.0.1",
        f"ERROR [{_svc()}] Socket timeout after 10s",
        f"ERROR [{_svc()}] DNS resolution failed for {_svc()}.internal",
        # Config
        f"ERROR [{_svc()}] File not found: config.yml",
        f"ERROR [{_svc()}] Configuration parsing failed: unexpected token",
        f"ERROR [{_svc()}] Missing required env variable DATABASE_URL",
        # SSL
        f"ERROR [{_svc()}] SSL certificate verification failed",
        f"CRITICAL [{_svc()}] TLS certificate expired — service unreachable",
        f"ERROR [{_svc()}] TLS handshake failed — protocol mismatch",
        # Deployment
        f"ERROR [{_svc()}] Deployment rollback initiated on {_env()}",
        f"ERROR [{_svc()}] Docker container crashed unexpectedly (exit code 137)",
        f"ERROR [{_svc()}] Image pull failed: rate limit exceeded",
        f"ERROR [{_svc()}] Kubernetes pod evicted: insufficient memory",
        f"FATAL [{_svc()}] Health check failed — pod marked unhealthy",
        # Application
        f"ERROR [{_svc()}] NullPointerException at Service.process():42",
        f"ERROR [{_svc()}] ArrayIndexOutOfBoundsException in worker thread",
        f"FATAL [{_svc()}] Stack overflow detected — infinite recursion",
        f"ERROR [{_svc()}] Unhandled exception in request handler",
        f"ERROR [{_svc()}] Circuit breaker OPEN — {_svc()} unavailable",
        f"ERROR [{_svc()}] Service dependencies missing — startup aborted",
        # System
        f"ERROR [{_svc()}] Disk space critical (512MB remaining)",
        f"CRITICAL [{_svc()}] Disk full — writes failing",
        f"ERROR [{_svc()}] File descriptor limit exceeded (ulimit)",
        f"ERROR [{_svc()}] System resource limit reached: max processes",
        # Build / test
        f"ERROR [{_svc()}] Build FAILED: {random.randint(1,20)} test(s) failed",
        f"ERROR [{_svc()}] Compilation error: undefined reference to main",
        f"ERROR [{_svc()}] Dependency resolution failed: version conflict",
        f"FATAL [{_svc()}] Pipeline aborted: critical step failed",
        f"ERROR [{_svc()}] Test suite FAILED after {_dur()}",
    ]


# ── Generator ─────────────────────────────────────────────────────────────────

def generate_logs(normal_count: int = 4000, anomaly_count: int = 1500) -> int:
    """
    Generate labeled synthetic logs and persist them.
    Clears existing training data before inserting.
    Returns total rows inserted.
    """
    db = SessionLocal()
    try:
        print(f"Generating {normal_count} normal + {anomaly_count} anomaly logs ...")

        db.query(TrainingData).delete()
        db.commit()

        batch = []

        # ── Normal logs ───────────────────────────────────────────────────
        for i in range(normal_count):
            if random.random() < 0.80:
                log_text = random.choice(_normal_templates())
            else:
                # 20% are warnings — still labeled normal
                log_text = random.choice(_warning_templates())
            batch.append(TrainingData(log_text=log_text, is_anomaly=False))
            if len(batch) >= 500:
                db.bulk_save_objects(batch)
                db.commit()
                batch = []
                print(f"  {i + 1} normal logs ...")

        # ── Anomaly logs ──────────────────────────────────────────────────
        for i in range(anomaly_count):
            if random.random() < 0.08:
                # ~8% are warning-style anomalies (harder boundary)
                log_text = random.choice(_warning_templates()) + " — CRITICAL threshold breached"
            else:
                log_text = random.choice(_anomaly_templates())
            batch.append(TrainingData(log_text=log_text, is_anomaly=True))
            if len(batch) >= 500:
                db.bulk_save_objects(batch)
                db.commit()
                batch = []
                print(f"  {i + 1} anomaly logs ...")

        if batch:
            db.bulk_save_objects(batch)
            db.commit()

        total    = db.query(TrainingData).count()
        anomalies = db.query(TrainingData).filter(TrainingData.is_anomaly == True).count()
        normal    = total - anomalies

        print(f"\nDatabase stats:")
        print(f"  Total  : {total}")
        print(f"  Normal : {normal}  ({100 * normal / total:.1f}%)")
        print(f"  Anomaly: {anomalies} ({100 * anomalies / total:.1f}%)")

        return total

    except Exception as exc:
        print(f"Error: {exc}")
        db.rollback()
        raise
    finally:
        db.close()


# ── Sequence Generator (for LSTM training) ────────────────────────────────────

def generate_sequences(
    n_normal:  int = 2000,
    n_failure: int = 800,
    seq_len:   int = 20,
) -> tuple:
    """
    Generate labeled build sequences for LSTM training.

    Each sequence is a list of ``seq_len`` log-line strings representing one
    CI/CD build run.  Returns ``(sequences, labels)`` where:
      - sequences : List[List[str]]  — one list of lines per build
      - labels    : List[int]        — 0 = successful build, 1 = failed build

    Failure builds are constructed realistically: the first 60–80 % of lines
    are normal / info lines, the remainder are error / critical lines.  This
    forces the LSTM to learn *temporal escalation patterns* rather than just
    the presence of a single error keyword.
    """
    random.seed(42)
    sequences: list = []
    labels:    list = []

    # ── Successful builds ─────────────────────────────────────────────────
    for _ in range(n_normal):
        seq = []
        for _ in range(seq_len):
            if random.random() < 0.85:
                seq.append(random.choice(_normal_templates()))
            else:
                seq.append(random.choice(_warning_templates()))
        sequences.append(seq)
        labels.append(0)

    # ── Failed builds ─────────────────────────────────────────────────────
    for _ in range(n_failure):
        # Normal phase: first 60–80 % of the sequence
        normal_lines = int(seq_len * random.uniform(0.60, 0.80))
        error_lines  = seq_len - normal_lines

        seq = []
        # Normal / warning lines at the start
        for _ in range(normal_lines):
            if random.random() < 0.75:
                seq.append(random.choice(_normal_templates()))
            else:
                seq.append(random.choice(_warning_templates()))
        # Error / critical lines at the end (escalation pattern)
        for _ in range(error_lines):
            seq.append(random.choice(_anomaly_templates()))

        sequences.append(seq)
        labels.append(1)

    # Shuffle so dataset isn't sorted by class
    combined = list(zip(sequences, labels))
    random.shuffle(combined)
    sequences, labels = zip(*combined)
    return list(sequences), list(labels)


if __name__ == "__main__":
    generate_logs()
