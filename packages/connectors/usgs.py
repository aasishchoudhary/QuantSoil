"""Governed USGS earthquake GeoJSON public connector."""
from __future__ import annotations
from datetime import datetime, timezone
import json
from typing import Any, Iterable, Mapping
from urllib.request import Request, urlopen
from packages.connectors.contracts import ConnectorError, SourceRecord, SourceSpec, utc_now

class USGSEarthquakeConnector:
    spec = SourceSpec(
        source="usgs-earthquake-geojson",
        license_class="public/open",
        schema_version="usgs-geojson-v1",
        parser_version="usgs-parser-v1",
        max_age_seconds=None,
    )

    def __init__(
        self,
        url: str = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson",
        *,
        user_agent: str = "GodsEyeWorldIntelligence/0.1",
        fetcher=None,
    ) -> None:
        self.url = url
        self.user_agent = user_agent
        self._fetcher = fetcher

    def fetch(self, *, since: datetime | None = None) -> Iterable[SourceRecord]:
        document = (self._fetcher or self._default_fetch)(self.url)
        if not isinstance(document, Mapping) or document.get("type") != "FeatureCollection":
            raise ConnectorError("invalid USGS GeoJSON FeatureCollection")
        for feature in document.get("features", []):
            if not isinstance(feature, Mapping):
                continue
            source_record_id = feature.get("id")
            properties = feature.get("properties")
            if not source_record_id or not isinstance(properties, Mapping):
                continue
            observed_at = _milliseconds_timestamp(properties.get("time"))
            if observed_at is None:
                continue
            if since is not None and observed_at < since:
                continue
            yield SourceRecord(
                str(source_record_id),
                {"feature": feature, "feed_generated": document.get("metadata", {}).get("generated")},
                observed_at,
                max(utc_now(), observed_at),
            )

    def _default_fetch(self, url: str) -> Mapping[str, Any]:
        request = Request(url, headers={
            "User-Agent": self.user_agent,
            "Accept": "application/geo+json, application/json",
        })
        try:
            with urlopen(request, timeout=15) as response:
                if response.status != 200:
                    raise ConnectorError(f"USGS HTTP status {response.status}")
                return json.loads(response.read().decode("utf-8"))
        except ConnectorError:
            raise
        except Exception as exc:
            raise ConnectorError(f"USGS transport failure: {type(exc).__name__}") from exc

def _milliseconds_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
