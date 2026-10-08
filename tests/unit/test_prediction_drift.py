from services.prediction.drift import compare_metric

def test_drift_threshold_is_explicit():
    signal=compare_metric("brier",.10,.16,.05)
    assert signal.breached
    assert signal.delta==.06
