from scripts.autonomy.validate_change import validate
def test_policy_and_workflow_changes_are_rejected():
    assert len(validate(["AGENTS.md",".github/workflows/autonomous-engineering.yml","scripts/autonomy/agent.py"])) == 3
def test_production_paths_are_allowed():
    assert validate(["packages/contracts/example.py","services/evidence/repository.py","schemas/event.schema.json","tests/unit/test_event.py","docs/architecture/event.md","db/migrations/003_event.sql","scripts/autonomy/README.md"]) == []
def test_unclassified_root_path_is_rejected():
    assert validate(["random-production-file.txt"])
