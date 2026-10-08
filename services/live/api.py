"""Live public-data gateway for God's Eye View.

This surface is intentionally separate from authoritative world-state storage:
third-party live feeds are volatile, may be delayed, and are never promoted to
truth without the normal evidence/ingestion boundary.
"""
from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import os
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Query

UA = "QuantSoil-GodsEye/0.2 (+public-data; evidence-first)"
CACHE: dict[str, tuple[float, Any]] = {}


def _get_json(url: str, *, ttl: int = 10) -> Any:
    now = time.monotonic()
    cached = CACHE.get(url)
    if cached and now - cached[0] < ttl:
        return cached[1]
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=20) as response:
            if response.status != 200:
                raise HTTPException(502, f"provider returned HTTP {response.status}")
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"provider unavailable: {type(exc).__name__}") from exc
    CACHE[url] = (now, payload)
    return payload


def _bbox(value: str) -> tuple[float, float, float, float]:
    try:
        parts = tuple(float(x.strip()) for x in value.split(","))
    except ValueError as exc:
        raise HTTPException(400, "bbox must be minLon,minLat,maxLon,maxLat") from exc
    if len(parts) != 4:
        raise HTTPException(400, "bbox must contain four coordinates")
    west, south, east, north = parts
    if not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
        raise HTTPException(400, "bbox outside WGS84 bounds")
    return west, south, east, north


def _aircraft_feature(state: list[Any], source: str) -> dict[str, Any] | None:
    # OpenSky state vector schema, documented by the provider.
    if len(state) < 8 or state[5] is None or state[6] is None:
        return None
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [state[5], state[6], state[7] or 0]},
        "properties": {
            "entity_type": "aircraft",
            "source": source,
            "icao24": state[0],
            "callsign": (state[1] or "").strip(),
            "origin_country": state[2],
            "last_contact": state[4],
            "altitude_m": state[7],
            "velocity_mps": state[9] if len(state) > 9 else None,
            "heading_deg": state[10] if len(state) > 10 else None,
            "vertical_rate_mps": state[11] if len(state) > 11 else None,
            "squawk": state[14] if len(state) > 14 else None,
        },
    }


def create_app() -> FastAPI:
    app = FastAPI(title="QuantSoil — God's Eye View Live Gateway", version="0.2.0")

    @app.get("/status")
    def status() -> dict[str, Any]:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "layers": {
                "aircraft_opensky": {"enabled": True, "auth": "anonymous"},
                "aircraft_adsblol": {"enabled": True, "auth": "keyless"},
                "earthquakes_usgs": {"enabled": True, "auth": "keyless"},
                "satellites_celestrak": {"enabled": True, "auth": "keyless"},
                "weather_openmeteo": {"enabled": True, "auth": "keyless"},
                "ships_aisstream": {"enabled": bool(os.getenv("AISSTREAM_API_KEY")), "auth": "api_key"},
                "fires_nasa_firms": {"enabled": bool(os.getenv("NASA_FIRMS_MAP_KEY")), "auth": "map_key"},
                "voice_openai_realtime": {"enabled": bool(os.getenv("OPENAI_API_KEY")), "auth": "api_key"},
                "google_photorealistic_3d": {"enabled": bool(os.getenv("GOOGLE_MAPS_API_KEY")), "auth": "api_key"},
            },
        }

    @app.get("/catalog")
    def catalog() -> dict[str, Any]:
        return {
            "name": "God's Eye View",
            "version": "0.2.0",
            "modules": [
                {"id": "geolens", "name": "GeoLens", "role": "spatial catalog / datasets"},
                {"id": "world-monitor", "name": "World Monitor", "role": "global event and news context"},
                {"id": "iron-sight", "name": "Iron Sight", "role": "conflict-monitoring workspace"},
                {"id": "pythia", "name": "Pythia", "role": "forecast / scenario workspace"},
                {"id": "wanderer", "name": "Wanderer", "role": "trail / route workspace"},
                {"id": "open-meteo", "name": "Open-Meteo", "role": "weather / marine / air-quality context"},
            ],
            "governance": {
                "named_person_search": False,
                "face_recognition": False,
                "private_tracking": False,
                "authoritative_claims_from_live_feeds": False,
            },
        }

    @app.get("/aircraft")
    def aircraft(
        bbox: str = Query(default="-180,-90,180,90"),
        provider: str = Query(default="opensky"),
    ) -> dict[str, Any]:
        west, south, east, north = _bbox(bbox)
        if provider == "opensky":
            query = urlencode({"lomin": west, "lamin": south, "lomax": east, "lamax": north, "extended": 1})
            payload = _get_json(f"https://opensky-network.org/api/states/all?{query}", ttl=10)
            features = [
                feature
                for state in (payload.get("states") or [])
                if (feature := _aircraft_feature(state, "opensky"))
            ]
            return {
                "type": "FeatureCollection",
                "source": "opensky",
                "observed_at": datetime.fromtimestamp(payload.get("time", time.time()), tz=timezone.utc).isoformat(),
                "count": len(features),
                "features": features,
            }
        if provider == "adsblol":
            raise HTTPException(400, "use /aircraft/near for ADSB.lol point queries")
        raise HTTPException(400, "provider must be opensky or adsblol")

    @app.get("/aircraft/near")
    def aircraft_near(
        lat: float,
        lon: float,
        radius_nm: int = Query(default=100, ge=1, le=250),
    ) -> dict[str, Any]:
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise HTTPException(400, "invalid coordinates")
        payload = _get_json(
            f"https://api.adsb.lol/v2/point/{lat}/{lon}/{radius_nm}",
            ttl=5,
        )
        return {
            "source": "adsb.lol",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "count": len(payload.get("ac") or []),
            "aircraft": payload.get("ac") or [],
        }

    @app.get("/earthquakes")
    def earthquakes(feed: str = Query(default="all_day")) -> Any:
        allowed = {"all_hour", "all_day", "all_week"}
        if feed not in allowed:
            raise HTTPException(400, "feed must be all_hour, all_day, or all_week")
        return _get_json(
            f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{feed}.geojson",
            ttl=30,
        )

    @app.get("/weather")
    def weather(lat: float, lon: float) -> Any:
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise HTTPException(400, "invalid coordinates")
        query = urlencode({
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m",
            "hourly": "temperature_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_direction_10m",
            "forecast_days": 2,
            "timezone": "UTC",
        })
        return {
            "source": "open-meteo",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "data": _get_json(f"https://api.open-meteo.com/v1/forecast?{query}", ttl=60),
        }

    @app.get("/satellites")
    def satellites(
        group: str = Query(default="active"),
        limit: int = Query(default=1000, ge=1, le=3000),
    ) -> dict[str, Any]:
        groups = {"active", "stations", "starlink", "gps-ops", "weather", "resource"}
        if group not in groups:
            raise HTTPException(400, f"group must be one of {sorted(groups)}")
        url = f"https://celestrak.org/NORAD/elements/gp.php?GROUP={group.upper()}&FORMAT=JSON"
        payload = _get_json(url, ttl=300)
        rows = payload if isinstance(payload, list) else payload.get("data", [])
        return {
            "source": "celestrak",
            "group": group,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "count": min(len(rows), limit),
            "objects": rows[:limit],
            "note": "CelesTrak JSON/OMM is preferred for current catalogs; legacy TLE cannot represent 6-digit catalog numbers.",
        }

    @app.get("/ships")
    def ships() -> dict[str, Any]:
        if not os.getenv("AISSTREAM_API_KEY"):
            raise HTTPException(503, "AISStream is optional and requires AISSTREAM_API_KEY")
        raise HTTPException(501, "AISStream websocket ingestion is not enabled in this build yet")

    return app
