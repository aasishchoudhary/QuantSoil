"""Governed NASA EONET natural-event public connector."""
from __future__ import annotations
from datetime import datetime, timezone
import json
from typing import Any, Iterable, Mapping
from urllib.request import Request, urlopen
from packages.connectors.contracts import ConnectorError, SourceRecord, SourceSpec, utc_now

class NASAEONETConnector:
    spec=SourceSpec(
        source="nasa-eonet-natural-events",
        license_class="public/open",
        schema_version="nasa-eonet-geojson-v3",
        parser_version="nasa-eonet-parser-v1",
        max_age_seconds=None,
    )

    def __init__(self,url="https://eonet.gsfc.nasa.gov/api/v3/events/geojson",
                 *,user_agent="GodsEyeWorldIntelligence/0.1",fetcher=None):
        self.url=url
        self.user_agent=user_agent
        self._fetcher=fetcher

    def fetch(self,*,since:datetime|None=None)->Iterable[SourceRecord]:
        document=(self._fetcher or self._default_fetch)(self.url)
        if not isinstance(document,Mapping) or document.get("type")!="FeatureCollection":
            raise ConnectorError("invalid NASA EONET GeoJSON FeatureCollection")
        for feature in document.get("features",[]):
            if not isinstance(feature,Mapping): continue
            props=feature.get("properties")
            if not isinstance(props,Mapping): continue
            event_id=props.get("id") or feature.get("id")
            observed=_event_time(props)
            if not event_id or observed is None: continue
            if since is not None and observed < since: continue
            yield SourceRecord(str(event_id),{"feature":feature},observed,max(utc_now(),observed))

    def _default_fetch(self,url):
        request=Request(url,headers={"User-Agent":self.user_agent,"Accept":"application/geo+json, application/json"})
        try:
            with urlopen(request,timeout=15) as response:
                if response.status!=200: raise ConnectorError(f"EONET HTTP status {response.status}")
                return json.loads(response.read().decode("utf-8"))
        except ConnectorError: raise
        except Exception as exc:
            raise ConnectorError(f"EONET transport failure: {type(exc).__name__}") from exc

def _event_time(properties:Mapping[str,Any])->datetime|None:
    for key in ("date","closed"):
        value=properties.get(key)
        if isinstance(value,str) and value.strip():
            try:
                dt=datetime.fromisoformat(value.replace("Z","+00:00"))
                if dt.tzinfo is not None: return dt.astimezone(timezone.utc)
            except ValueError: pass
    dates=properties.get("geometryDates")
    if isinstance(dates,list):
        for value in dates:
            if isinstance(value,str):
                try:
                    dt=datetime.fromisoformat(value.replace("Z","+00:00"))
                    if dt.tzinfo is not None: return dt.astimezone(timezone.utc)
                except ValueError: pass
    return None
