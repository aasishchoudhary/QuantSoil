from datetime import datetime, timezone, timedelta
from packages.contracts.world_state import EntityState, InMemoryWorldStateRepository
from services.analyst.query import AnalystService, AnalystQueryError

T=datetime(2026,1,1,tzinfo=timezone.utc)

class MapRepo:
    def query_bbox(self,*args): return ["feature"]

def state(sid, eid, start, end, props, evidence):
    return EntityState(sid,eid,"place",start,end,start,start,props,None,.9,(evidence,))

def test_snapshot_is_deterministic_and_evidence_backed():
    repo=InMemoryWorldStateRepository()
    repo.append(state("s1","e1",T,T+timedelta(days=1),{"status":"open"},"usgs:e1"))
    result=AnalystService(repo,MapRepo()).snapshot(("e1",),at=T)
    assert result.states[0].state_id=="s1"
    assert result.states[0].evidence_refs==("usgs:e1",)

def test_timeline_and_spatial_queries():
    repo=InMemoryWorldStateRepository()
    repo.append(state("s1","e1",T,T+timedelta(days=1),{"status":"open"},"usgs:e1"))
    repo.append(state("s2","e1",T+timedelta(days=1),None,{"status":"closed"},"usgs:e2"))
    service=AnalystService(repo,MapRepo())
    timeline=service.timeline("e1",start=T,end=T+timedelta(days=2))
    assert timeline.changes[1].changed_properties==("status",)
    assert service.spatial((0,0,1,1)).features==("feature",)

def test_invalid_time_is_rejected():
    repo=InMemoryWorldStateRepository()
    try:
        AnalystService(repo,MapRepo()).snapshot(("e1",),at=datetime(2026,1,1))
    except AnalystQueryError:
        pass
    else:
        raise AssertionError("naive timestamp accepted")
