from datetime import datetime, timezone, timedelta
from packages.contracts.world_state import EntityState
from services.derived.rules import PropertyTransitionRule, evaluate_history

T=datetime(2026,1,1,tzinfo=timezone.utc)

def make(sid, start, end, value, ref):
    return EntityState(sid,"e1","facility",start,end,start,start,{"status":value},None,.8,(ref,))

def test_property_transition_creates_evidence_backed_derived_event():
    states=(make("s1",T,T+timedelta(hours=1),"open","src:a"),
            make("s2",T+timedelta(hours=1),None,"closed","src:b"))
    events=evaluate_history(states,PropertyTransitionRule("r1","status","open","closed","facility_closed"))
    assert len(events)==1
    assert events[0].state=="derived"
    assert events[0].evidence_refs==("src:a","src:b")
    assert events[0].payload["from_state_id"]=="s1"

def test_unmatched_transition_produces_nothing():
    states=(make("s1",T,T+timedelta(hours=1),"open","src:a"),
            make("s2",T+timedelta(hours=1),None,"open","src:b"))
    assert evaluate_history(states,PropertyTransitionRule("r1","status","open","closed","facility_closed"))==()
