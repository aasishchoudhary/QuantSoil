from packages.evaluation.gates import run_release_evaluation, _gate

def test_release_evaluation_passes_all_core_gates():
    report = run_release_evaluation()
    assert report.passed
    assert report.failed_gate_ids == ()
    assert len(report.gates) == 4

def test_gate_failure_is_reported_without_aborting_other_gates():
    result = _gate("synthetic-failure", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert not result.passed
    assert "RuntimeError" in result.detail
