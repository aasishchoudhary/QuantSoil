"""HTTP API for read-only evidence-first analyst queries."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from typing import Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from services.analyst.query import AnalystQueryError, AnalystService

_LOG = logging.getLogger("gods_eye.analyst")

def create_app(service: AnalystService) -> FastAPI:
    app = FastAPI(title="God's Eye World Intelligence — Analyst API", version="0.1.0")

    @app.middleware("http")
    async def security_and_audit(request, call_next):
        correlation = request.headers.get("X-Correlation-ID") or hashlib.sha256(
            f"{datetime.now(timezone.utc).isoformat()}:{request.url.path}".encode()
        ).hexdigest()[:24]
        if request.url.path != "/health" and os.getenv("ANALYST_AUTH_MODE", "optional").lower() == "required":
            expected = os.getenv("ANALYST_BEARER_TOKEN", "")
            supplied = request.headers.get("Authorization", "")
            if not expected or supplied != f"Bearer {expected}":
                return JSONResponse(
                    status_code=401,
                    content={"detail":"authentication required"},
                    headers={"WWW-Authenticate":"Bearer", "X-Correlation-ID":correlation},
                )
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        _LOG.info(json.dumps({
            "event":"analyst_request",
            "method":request.method,
            "path":request.url.path,
            "status":response.status_code,
            "correlation_id":correlation,
        }, sort_keys=True, separators=(",",":")))
        return response

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/snapshot")
    def snapshot(entity_ids: str = Query(...), at: datetime = Query(...)) -> dict[str, Any]:
        try:
            result = service.snapshot(tuple(x.strip() for x in entity_ids.split(",") if x.strip()), at=at)
            summary = service.evidence_summary(result.states)
        except AnalystQueryError as exc:
            raise HTTPException(400, str(exc)) from exc
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
        except (ValueError, AnalystQueryError) as exc:
            raise HTTPException(400, str(exc)) from exc
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
        except AnalystQueryError as exc:
            raise HTTPException(400, str(exc)) from exc
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
