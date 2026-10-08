"""HTTP API for read-only evidence-first analyst queries."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging
import os
import time
from collections import OrderedDict, deque
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi import status

from packages.repositories.map_postgres import MapRepositoryError
from packages.repositories.world_state_postgres import WorldStateRepositoryError
from services.analyst.query import AnalystQueryError, AnalystService

_LOG = logging.getLogger("gods_eye.analyst")


class AnalystUnavailableError(RuntimeError):
    """Raised when authoritative analyst dependencies are not available."""


def create_unavailable_app(reason: str = "runtime dependencies are not ready") -> FastAPI:
    """Keep the public analyst contract mounted during dependency degradation.

    A live process must not turn an expected API into HTTP 404 simply because
    PostgreSQL/S3 initialization failed. The degraded surface returns explicit
    503 responses and never exposes internal exception details.
    """
    app = FastAPI(title="God's Eye World Intelligence — Analyst API", version="0.1.0")

    @app.get("/health")
    def health() -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "ready": False, "detail": reason},
        )

    @app.api_route("/{path:path}", methods=["GET", "HEAD", "OPTIONS"])
    def unavailable(path: str) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": reason, "path": f"/{path}"},
        )

    return app


def create_app(service: AnalystService, audit_store=None, health_check=None) -> FastAPI:
    app = FastAPI(title="God's Eye World Intelligence — Analyst API", version="0.1.0")

    rate_limit: OrderedDict[str, deque[float]] = OrderedDict()
    rate_limit_per_minute = int(os.getenv("ANALYST_RATE_LIMIT_PER_MINUTE", "120"))
    rate_limit_max_clients = int(os.getenv("ANALYST_RATE_LIMIT_MAX_CLIENTS", "10000"))
    trust_proxy_headers = os.getenv("ANALYST_TRUST_PROXY_HEADERS", "false").lower() == "true"
    if rate_limit_per_minute < 1:
        raise ValueError("ANALYST_RATE_LIMIT_PER_MINUTE must be >= 1")
    if rate_limit_max_clients < 1:
        raise ValueError("ANALYST_RATE_LIMIT_MAX_CLIENTS must be >= 1")

    @app.middleware("http")
    async def security_and_audit(request, call_next):
        correlation = request.headers.get("X-Correlation-ID") or hashlib.sha256(
            f"{datetime.now(timezone.utc).isoformat()}:{request.url.path}".encode()
        ).hexdigest()[:24]
        if request.url.path != "/health":
            if trust_proxy_headers:
                client_key = request.headers.get(
                    "X-Forwarded-For",
                    request.client.host if request.client else "unknown",
                ).split(",")[0].strip()
            else:
                client_key = request.client.host if request.client else "unknown"
            client_key = client_key or "unknown"
            now = time.monotonic()
            bucket = rate_limit.get(client_key)
            if bucket is None:
                if len(rate_limit) >= rate_limit_max_clients:
                    rate_limit.popitem(last=False)
                bucket = deque()
                rate_limit[client_key] = bucket
            else:
                rate_limit.move_to_end(client_key)
            while bucket and now - bucket[0] >= 60:
                bucket.popleft()
            if len(bucket) >= rate_limit_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "rate limit exceeded"},
                    headers={"Retry-After": "60", "X-Correlation-ID": correlation},
                )
            bucket.append(now)
        if request.url.path != "/health" and os.getenv("ANALYST_AUTH_MODE", "optional").lower() == "required":
            expected = os.getenv("ANALYST_BEARER_TOKEN", "")
            supplied = request.headers.get("Authorization", "")
            if not expected or not hmac.compare_digest(supplied, f"Bearer {expected}"):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "authentication required"},
                    headers={
                        "WWW-Authenticate": "Bearer",
                        "X-Correlation-ID": correlation,
                    },
                )
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if audit_store is not None:
            try:
                audit_store.put(
                    occurred_at=datetime.now(timezone.utc),
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    correlation_id=correlation,
                )
            except Exception:
                _LOG.exception("analyst audit persistence failed")
        _LOG.info(json.dumps({
            "event": "analyst_request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "correlation_id": correlation,
        }, sort_keys=True, separators=(",", ":")))
        return response

    @app.get("/health")
    def health() -> JSONResponse:
        if health_check is not None:
            try:
                health_check()
            except Exception:
                _LOG.exception("analyst health dependency check failed")
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "status": "degraded",
                        "ready": False,
                        "detail": "analyst dependencies are not ready",
                    },
                )
        return JSONResponse(status_code=200, content={"status": "ok", "ready": True})

    @app.get("/snapshot")
    def snapshot(entity_ids: str = Query(...), at: datetime = Query(...)) -> dict[str, Any]:
        try:
            result = service.snapshot(
                tuple(x.strip() for x in entity_ids.split(",") if x.strip()),
                at=at,
            )
            summary = service.evidence_summary(result.states)
        except AnalystUnavailableError as exc:
            raise HTTPException(503, str(exc)) from exc
        except (AnalystQueryError,) as exc:
            raise HTTPException(400, str(exc)) from exc
        except WorldStateRepositoryError as exc:
            _LOG.exception("analyst snapshot datastore query failed")
            raise HTTPException(503, "analyst datastore unavailable") from exc
        return {
            "as_of": result.requested_at.isoformat(),
            "generated_at": result.generated_at.isoformat(),
            "states": [_state(state) for state in result.states],
            "evidence": {
                "refs": list(summary.evidence_refs),
                "sources": list(summary.sources),
                "observed_at_min": summary.observed_at_min.isoformat() if summary.observed_at_min else None,
                "observed_at_max": summary.observed_at_max.isoformat() if summary.observed_at_max else None,
            },
        }

    @app.get("/spatial")
    def spatial(
        bbox: str = Query(..., description="minLon,minLat,maxLon,maxLat"),
        at: datetime | None = Query(default=None),
        limit: int = Query(default=500, ge=1, le=5000),
    ) -> dict[str, Any]:
        try:
            parts = tuple(float(x.strip()) for x in bbox.split(","))
            result = service.spatial(parts, at=at, limit=limit)
        except AnalystUnavailableError as exc:
            raise HTTPException(503, str(exc)) from exc
        except (ValueError, AnalystQueryError) as exc:
            raise HTTPException(400, str(exc)) from exc
        except MapRepositoryError as exc:
            _LOG.exception("analyst spatial datastore query failed")
            raise HTTPException(503, "analyst datastore unavailable") from exc
        return {
            "type": "FeatureCollection",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "count": len(result.features),
            "features": [
                item.to_geojson() if hasattr(item, "to_geojson") else item
                for item in result.features
            ],
        }

    @app.get("/timeline/{entity_id}")
    def timeline(entity_id: str, start: datetime = Query(...), end: datetime = Query(...)) -> dict[str, Any]:
        try:
            result = service.timeline(entity_id, start=start, end=end)
        except AnalystUnavailableError as exc:
            raise HTTPException(503, str(exc)) from exc
        except AnalystQueryError as exc:
            raise HTTPException(400, str(exc)) from exc
        except WorldStateRepositoryError as exc:
            _LOG.exception("analyst timeline datastore query failed")
            raise HTTPException(503, "analyst datastore unavailable") from exc
        return {
            "entity_id": result.entity_id,
            "start": result.start.isoformat(),
            "end": result.end.isoformat(),
            "changes": [{
                "from_state_id": item.from_state_id,
                "to_state_id": item.to_state_id,
                "valid_from": item.valid_from.isoformat() if item.valid_from else None,
                "valid_to": item.valid_to.isoformat() if item.valid_to else None,
                "changed_properties": list(item.changed_properties),
                "evidence_refs": list(item.evidence_refs),
            } for item in result.changes],
        }

    return app


def _state(state) -> dict[str, Any]:
    return {
        "state_id": state.state_id,
        "entity_id": state.entity_id,
        "entity_type": state.entity_type,
        "valid_from": state.valid_from.isoformat(),
        "valid_to": state.valid_to.isoformat() if state.valid_to else None,
        "observed_at": state.observed_at.isoformat(),
        "recorded_at": state.recorded_at.isoformat(),
        "properties": dict(state.properties),
        "geometry": dict(state.geometry) if state.geometry else None,
        "confidence": state.confidence,
        "evidence_refs": list(state.evidence_refs),
    }
