"""HTTP API for read-only evidence-first analyst queries."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging
import os
import threading
import time
from typing import Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from services.analyst.query import AnalystQueryError, AnalystService
from services.analyst.public_sources import PublicSourceError, aircraft_for_bbox, earthquakes
from services.analyst.orbital_sources import OrbitalSourceError, orbital_objects

_LOG = logging.getLogger("gods_eye.analyst")
_SOURCE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_SOURCE_CACHE_LOCK = threading.Lock()


def _cached_public_source(key: str, ttl_seconds: int, producer) -> dict[str, Any]:
    """Cache successful public-provider responses to bound request rates across clients."""
    now = time.monotonic()
    with _SOURCE_CACHE_LOCK:
        cached = _SOURCE_CACHE.get(key)
        if cached and cached[0] > now:
            return cached[1]
    result = producer()
    with _SOURCE_CACHE_LOCK:
        _SOURCE_CACHE[key] = (time.monotonic() + ttl_seconds, result)
        if len(_SOURCE_CACHE) > 256:
            now = time.monotonic()
            for cache_key, (expires, _) in list(_SOURCE_CACHE.items()):
                if expires <= now:
                    _SOURCE_CACHE.pop(cache_key, None)
            while len(_SOURCE_CACHE) > 256:
                _SOURCE_CACHE.pop(next(iter(_SOURCE_CACHE)))
    return result

def create_app(service: AnalystService, audit_store=None) -> FastAPI:
    app = FastAPI(title="God's Eye World Intelligence — Analyst API", version="0.1.0")

    @app.middleware("http")
    async def security_and_audit(request, call_next):
        correlation = request.headers.get("X-Correlation-ID") or hashlib.sha256(
            f"{datetime.now(timezone.utc).isoformat()}:{request.url.path}".encode()
        ).hexdigest()[:24]
        if request.url.path != "/health" and os.getenv("ANALYST_AUTH_MODE", "optional").lower() == "required":
            expected = os.getenv("ANALYST_BEARER_TOKEN", "")
            supplied = request.headers.get("Authorization", "")
            if not expected or not hmac.compare_digest(supplied, f"Bearer {expected}"):
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

    @app.get("/sources/earthquakes")
    def public_earthquakes() -> dict[str, Any]:
        """USGS past-hour earthquake observations; provider freshness is preserved."""
        try:
            return _cached_public_source("usgs-earthquakes", 60, earthquakes)
        except PublicSourceError as exc:
            raise HTTPException(502, str(exc)) from exc

    @app.get("/sources/aircraft")
    def public_aircraft(
        bbox: str = Query(..., description="minLon,minLat,maxLon,maxLat; regional ADS-B coverage"),
    ) -> dict[str, Any]:
        """Regional ADS-B observations from adsb.lol; not a global-coverage guarantee."""
        try:
            parts = tuple(float(x.strip()) for x in bbox.split(","))
            if len(parts) != 4:
                raise ValueError("bbox must contain minLon,minLat,maxLon,maxLat")
            key = "adsb:" + ",".join(f"{value:.3f}" for value in parts)
            return _cached_public_source(key, 15, lambda: aircraft_for_bbox(parts))
        except (ValueError, PublicSourceError) as exc:
            status_code = 502 if isinstance(exc, PublicSourceError) else 400
            raise HTTPException(status_code, str(exc)) from exc

    @app.get("/sources/orbital")
    def public_orbital_objects() -> dict[str, Any]:
        """Propagated station-group orbital positions; output is derived, not observed."""
        try:
            return _cached_public_source("celestrak-stations", 60, orbital_objects)
        except OrbitalSourceError as exc:
            raise HTTPException(502, str(exc)) from exc

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

    @app.get("/search")
    def search(
        q: str = Query(..., min_length=2, max_length=128, description="Search map feature type, source, identifier or indexed properties"),
        limit: int = Query(default=25, ge=1, le=100),
    ) -> dict[str, Any]:
        try:
            result = service.search(q, limit=limit)
        except AnalystQueryError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            _LOG.exception("analyst global search failed")
            raise HTTPException(503, "global search is temporarily unavailable") from exc
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
