import os
from datetime import datetime, timezone, timedelta
import pytest

psycopg = pytest.importorskip("psycopg")
from packages.repositories.map_postgres import PostgresMapRepository
from packages.repositories.world_state_postgres import PostgresWorldStateRepository
from services.analyst.query import AnalystService

pytestmark = pytest.mark.integration

T = datetime(2026, 1, 1, tzinfo=timezone.utc)

@pytest.fixture()
def db():
    dsn=os.getenv("DATABASE_URL")
    if not dsn: pytest.skip("DATABASE_URL not configured")
    conn=psycopg.connect(dsn)
    with conn.cursor() as c:
        c.execute("DELETE FROM entity_state WHERE entity_id='analyst-integration'")
        c.execute("DELETE FROM map_features WHERE feature_id='00000000-0000-0000-0000-000000000001'")
    conn.commit()
    yield conn
    with conn.cursor() as c:
        c.execute("DELETE FROM entity_state WHERE entity_id='analyst-integration'")
        c.execute("DELETE FROM map_features WHERE feature_id='00000000-0000-0000-0000-000000000001'")
    conn.commit()
    conn.close()

def test_analyst_queries_use_migrated_world_state_and_postgis(db):
    with db.cursor() as c:
        c.execute(
            """INSERT INTO entity_state
            (state_id,entity_id,entity_type,valid_from,valid_to,observed_at,recorded_at,
             properties,geometry,confidence,evidence_refs)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,NULL,%s,%s::jsonb)""",
            ("as1","analyst-integration","facility",T,T+timedelta(hours=1),T,T,'{"status":"open"}',.9,'["usgs:e1"]'),
        )
        c.execute(
            """INSERT INTO entity_state
            (state_id,entity_id,entity_type,valid_from,valid_to,observed_at,recorded_at,
             properties,geometry,confidence,evidence_refs)
            VALUES (%s,%s,%s,%s,NULL,%s,%s,%s::jsonb,NULL,%s,%s::jsonb)""",
            ("as2","analyst-integration","facility",T+timedelta(hours=1),T+timedelta(hours=1),T+timedelta(hours=1),'{"status":"closed"}',.8,'["usgs:e2"]'),
        )
        c.execute(
            """INSERT INTO map_features
            (feature_id,feature_type,source,source_record_id,geometry,properties,confidence,
             observed_at,raw_payload_hash,parser_version,license_class)
            VALUES (%s,'facility','usgs','r1',
              ST_SetSRID(ST_GeomFromGeoJSON(%s),4326),%s::jsonb,%s,%s,%s,%s,%s)""",
            ("00000000-0000-0000-0000-000000000001",
             '{"type":"Point","coordinates":[1,2]}','{"name":"test"}',.9,T,'a'*64,'p1','public/open'),
        )
    db.commit()

    service=AnalystService(PostgresWorldStateRepository(db),PostgresMapRepository(db))
    snapshot=service.snapshot(("analyst-integration",),at=T)
    timeline=service.timeline("analyst-integration",start=T,end=T+timedelta(hours=2))
    spatial=service.spatial((0,0,3,3),at=T)
    tile=PostgresMapRepository(db).tile(2,2,1,at=T)

    assert snapshot.states[0].properties["status"]=="open"
    assert timeline.changes[-1].changed_properties==("status",)
    assert any(
        feature.feature_id == "00000000-0000-0000-0000-000000000001"
        and feature.source == "usgs"
        for feature in spatial.features
    )
    assert isinstance(tile, bytes)
