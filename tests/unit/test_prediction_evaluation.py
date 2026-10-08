from services.prediction.evaluation import evaluate

def test_evaluation_is_horizon_specific_and_calibrated():
    report=evaluate(((.8,1,3600),(.2,0,3600),(.9,0,7200)),horizon_seconds=3600)
    assert report.count==2
    assert round(report.brier,10)==.04
    assert len(report.calibration)==2

def test_empty_horizon_is_rejected():
    try: evaluate(((.8,1,3600),),horizon_seconds=7200)
    except ValueError: pass
    else: raise AssertionError("wrong horizon accepted")
