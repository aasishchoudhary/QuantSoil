from datetime import datetime, timezone
from packages.connectors.nasa_eonet import NASAEONETConnector

def test_eonet_parses_geojson_event():
    document={
        "type":"FeatureCollection",
        "features":[{
            "type":"Feature",
            "id":"EONET_1",
            "geometry":{"type":"Point","coordinates":[1,2]},
            "properties":{"id":"EONET_1","title":"Wildfire","date":"2026-01-01T00:00:00Z"}
        }]
    }
    records=list(NASAEONETConnector(fetcher=lambda _:document).fetch())
    assert len(records)==1
    assert records[0].source_record_id=="EONET_1"
    assert records[0].observed_at==datetime(2026,1,1,tzinfo=timezone.utc)
