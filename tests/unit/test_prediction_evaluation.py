from datetime import datetime, timezone, timedelta
from packages.contracts.world_state import EntityState
from services.prediction.baseline import PersistenceBaseline
from services.prediction.evaluation import resolve_binary_outcome, calibration_report

T=datetime(2026,1,1,tzinfo=timezone.utc)

def test_forecast_outcome_links_to_authoritative_state():
    s1=EntityState("s1","e1","facility",T,None,T,T,{"status":"closed"},None,.9,("e1",))
    forecast=PersistenceBaseline().forecast((s1,),property_name="status",target_value="closed",
        horizon=timedelta(hours=1),generated_at=T)
    assert resolve_binary_outcome(forecast,s1,property_name="status")==1

def test_calibration_report_is_deterministic():
    report=calibration_report(((.1,0),(.2,0),(.9,1),(.8,1)),bins=2)
    assert report.score.count==4
    assert len(report.bins)==2
    assert report.bins[0].observed_frequency==0
    assert report.bins[1].observed_frequency==1
