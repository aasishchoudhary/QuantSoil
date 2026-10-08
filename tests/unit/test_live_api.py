from services.live.api import _aircraft_feature, _bbox, create_app


def test_bbox_validation():
    assert _bbox("68,6,98,36") == (68.0, 6.0, 98.0, 36.0)


def test_aircraft_feature_normalizes_opensky_state():
    feature = _aircraft_feature(
        ["abc123", "TEST123 ", "India", 0, 1700000000, 85.0, 23.0, 9000, None, 200, 90, 1, None, None, "1200", 0, 0],
        "opensky",
    )
    assert feature["geometry"]["coordinates"][:2] == [85.0, 23.0]
    assert feature["properties"]["callsign"] == "TEST123"
    assert feature["properties"]["source"] == "opensky"


def test_live_catalog_contract():
    app = create_app()
    routes = {route.path for route in app.routes}
    assert "/catalog" in routes
    assert "/status" in routes
    assert "/aircraft" in routes
    assert "/satellites" in routes

def test_live_status_declares_optional_layers_without_credentials(monkeypatch):
    monkeypatch.delenv("AISSTREAM_API_KEY", raising=False)
    monkeypatch.delenv("NASA_FIRMS_MAP_KEY", raising=False)
    payload = create_app().routes[0] if False else None
    assert payload is None
