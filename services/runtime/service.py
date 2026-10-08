"""Production runtime service: scheduler + leased worker + health API."""
from __future__ import annotations
import os
import threading
from datetime import timedelta, timezone, datetime
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from packages.connectors.usgs import USGSEarthquakeConnector
from packages.connectors.noaa import NOAAWeatherAlertsConnector
from packages.connectors.registry import SourceRegistry
from packages.repositories.evidence_payload_s3 import S3EvidencePayloadStore
from packages.repositories.evidence_postgres import PostgresEvidenceRepository
from packages.repositories.source_health_postgres import PostgresIngestionAuditRepository, PostgresSourceHealthRepository
from services.connectors.runner import ConnectorRunner
from services.connectors.retry import RetryPolicy
from services.ingestion.observation import ObservationIngestor
from services.runtime.health import HealthStatus, check_database
from services.runtime.postgres import PostgresJobQueue
from services.runtime.scheduler import RuntimeScheduler, SourceSchedule
from services.runtime.telemetry import RuntimeEvent, emit, correlation_id
from services.runtime.worker import ConnectorWorker, WorkerPolicy

def _int(name: str, default: int, minimum: int = 0) -> int:
    value = int(os.getenv(name, str(default)))
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value

def _database_factory():
    dsn = os.getenv("DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("DATABASE_URL is required")
    import psycopg
    return psycopg.connect(dsn)

def build_components():
    connection = _database_factory()
    registry = SourceRegistry()
    usgs = USGSEarthquakeConnector()
    noaa = NOAAWeatherAlertsConnector(
        user_agent=os.getenv("NWS_USER_AGENT", "GodsEyeWorldIntelligence/0.1")
    )
    for connector in (usgs, noaa):
        registry.register(connector.spec)
    connectors = {usgs.spec.source: usgs, noaa.spec.source: noaa}

    queue = PostgresJobQueue(connection)
    health = PostgresSourceHealthRepository(connection)
    audit = PostgresIngestionAuditRepository(connection)
    evidence_payload = S3EvidencePayloadStore(os.environ["EVIDENCE_BUCKET"])
    evidence_metadata = PostgresEvidenceRepository(connection)
    runner = ConnectorRunner(
        registry, ObservationIngestor(),
        retry_policy=RetryPolicy(max_attempts=1),
        health_store=health,
        audit_store=audit,
        evidence_payload_store=evidence_payload,
        evidence_metadata_store=evidence_metadata,
    )
    worker = ConnectorWorker(
        queue, runner, connectors,
        policy=WorkerPolicy(
            lease_duration=timedelta(seconds=_int("RUNTIME_LEASE_SECONDS", 300, 1)),
            max_attempts=_int("RUNTIME_MAX_ATTEMPTS", 3, 1),
            retry_delay=timedelta(seconds=_int("RUNTIME_RETRY_DELAY_SECONDS", 30, 0)),
            max_retry_delay=timedelta(seconds=_int("RUNTIME_MAX_RETRY_DELAY_SECONDS", 600, 1)),
            jitter_ratio=float(os.getenv("RUNTIME_RETRY_JITTER_RATIO", "0.2")),
        ),
    )
    interval = timedelta(seconds=_int("RUNTIME_SOURCE_INTERVAL_SECONDS", 60, 1))
    scheduler = RuntimeScheduler(
        queue,
        tuple(SourceSchedule(source, interval, max_catch_up=_int("RUNTIME_MAX_CATCH_UP", 1, 0))
              for source in sorted(connectors)),
    )
    return connection, registry, connectors, queue, scheduler, worker

def create_app() -> FastAPI:
    app = FastAPI(title="God's Eye World Intelligence Runtime", version="0.1.0")
    state = {
        "started": False, "stop": threading.Event(), "thread": None,
        "connection": None, "connector_count": 0,
    }

    @app.get("/health/live")
    def live():
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready():
        db_ok = check_database(_database_factory) if os.getenv("DATABASE_URL") else False
        status = HealthStatus(
            live=True, ready=bool(state["started"] and db_ok),
            database_ok=db_ok, connector_count=state["connector_count"],
            detail="ready" if state["started"] and db_ok else "dependency_not_ready",
        )
        return JSONResponse(status_code=200 if status.ready else 503, content=status.__dict__)

    @app.on_event("startup")
    def startup():
        try:
            connection, registry, connectors, queue, scheduler, worker = build_components()
        except Exception as exc:
            emit(RuntimeEvent("runtime_start_failed", datetime.now(timezone.utc),
                              error_type=type(exc).__name__))
            return

        state["connection"] = connection
        state["connector_count"] = len(connectors)
        state["started"] = True

        def loop():
            poll = _int("RUNTIME_WORKER_POLL_SECONDS", 1, 1)
            while not state["stop"].is_set():
                now = datetime.now(timezone.utc)
                try:
                    scheduler.tick(now=now)
                    job = worker.run_once(now=now)
                    if job is not None:
                        emit(RuntimeEvent(
                            "runtime_job_finished", now, source=job.source,
                            job_id=job.job_id, attempt=job.attempts,
                            status=job.status.value, error_type=job.last_error_type,
                            correlation_id=correlation_id(job.job_id, job.attempts),
                        ))
                except Exception as exc:
                    emit(RuntimeEvent("runtime_loop_error", now, error_type=type(exc).__name__))
                state["stop"].wait(poll)

        state["thread"] = threading.Thread(target=loop, name="runtime-worker", daemon=True)
        state["thread"].start()
        emit(RuntimeEvent("runtime_started", datetime.now(timezone.utc)))

    @app.on_event("shutdown")
    def shutdown():
        state["stop"].set()
        thread = state.get("thread")
        if thread is not None:
            thread.join(timeout=10)
        connection = state.get("connection")
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
        state["started"] = False
        emit(RuntimeEvent("runtime_stopped", datetime.now(timezone.utc)))

    return app

app = create_app()
