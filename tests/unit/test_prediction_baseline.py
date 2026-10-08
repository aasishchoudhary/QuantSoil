from datetime import datetime, timezone, timedelta
from packages.contracts.world_state import EntityState
from services.prediction.baseline import PersistenceBaseline, score_binary_forecasts

T=datetime(2026,1,1,tzinfo=timezone.utc)
def state(sid,start,end,value,ref):
    return EntityState(sid,"e1","facility",start,end,start,start,{"status":value},None,.8,(ref,))
def test_persistence_forecast_is_deterministic_and_provenance_backed():
    history=(state("s1",T,T+timedelta(hours=1),"open","e1"),
             state("s2",T+timedelta(hours=1),T+timedelta(hours=2),"closed","e2"),
             state("s3",T+timedelta(hours=2),None,"closed","e3"))
    forecast=PersistenceBaseline().forecast(history,property_name="status",target_value="closed",
                                            horizon=timedelta(hours=1),generated_at=T)
    assert forecast.prediction.state=="predicted"
    assert forecast.prediction.evidence_refs==("e3",)
    assert forecast.probability==2/3
def test_probability_scores():
    score=score_binary_forecasts(((.8,1),(.2,0)))
    assert round(score.brier,10)==.04
    assert score.log_loss>0
