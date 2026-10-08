from datetime import datetime, timezone
import pytest
from packages.contracts.entity_ontology import EntityAlias, EntityIdentifier, EntityRelation, OntologyEntity, OntologyError
from packages.contracts.world_state import EntityState
from services.world_state.query import diff_states, get_state_at, WorldStateQueryError
from packages.repositories.world_state_memory import WorldStateReplayRepository

T = datetime(2026, 1, 1, tzinfo=timezone.utc)

def state(i, start, end=None, **props):
    return EntityState(i, "e-1", "aircraft", start, end, start, start, props or {"status":"active"}, None, None, ("ev-"+i,))

def test_ontology_requires_supported_types_and_evidence():
    with pytest.raises(OntologyError): OntologyEntity("e-1", "unknown", ("ev-1",))
    with pytest.raises(OntologyError): OntologyEntity("e-1", "asset", ())

def test_ontology_identifiers_aliases_and_relationships_are_temporal():
    e = OntologyEntity("e-1", "asset", ("ev-1",), (EntityIdentifier("icao","ABC"),), (EntityAlias("Test"),))
    relation = EntityRelation("r-1", "e-1", "located_at", "p-1", ("ev-2",), T)
    assert e.identifiers[0].value == "ABC"
    assert relation.is_valid_at(T)

def test_query_returns_reproducible_historical_state_and_evidence():
    repo = WorldStateReplayRepository()
    repo.append(state("s-1", T, T.replace(day=2), status="active"))
    result = get_state_at(repo, "e-1", T.replace(hour=12))
    assert result.state.state_id == "s-1"
    assert result.state.evidence_refs == ("ev-s-1",)

def test_query_diff_is_temporal_and_deterministic():
    repo = WorldStateReplayRepository()
    t2 = T.replace(day=2)
    repo.append(state("s-1", T, t2, status="active"))
    repo.append(state("s-2", t2, None, status="inactive", owner="x"))
    result = diff_states(repo, "e-1", T, T.replace(day=3))
    assert len(result) == 2
    assert result[1].changed_properties == ("owner","status")

def test_query_rejects_naive_or_invalid_time():
    repo = WorldStateReplayRepository()
    with pytest.raises(WorldStateQueryError): get_state_at(repo, "e-1", datetime(2026,1,1))
    with pytest.raises(WorldStateQueryError): diff_states(repo, "e-1", T, T)
