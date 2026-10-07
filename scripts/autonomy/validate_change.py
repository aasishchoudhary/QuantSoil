"""Fail-closed validation for autonomous agent diffs."""
from __future__ import annotations
import subprocess, sys
FORBIDDEN=(".github/workflows/",".github/actions/",".github/CODEOWNERS","AGENTS.md","SECURITY.md","DATA_GOVERNANCE.md","DEFINITION_OF_DONE.md","EVALUATION_POLICY.md","scripts/autonomy/agent.py","scripts/autonomy/tasks.json")
ALLOWED=("packages/","services/","connectors/","schemas/","tests/","docs/","db/migrations/","scripts/autonomy/")
def changed_files():
    r=subprocess.run(["git","diff","--name-only","origin/main...HEAD"],text=True,capture_output=True,check=True)
    return [x for x in r.stdout.splitlines() if x]
def validate(paths):
    errors=[]
    for path in paths:
        if path in FORBIDDEN or any(path.startswith(p) for p in FORBIDDEN if p.endswith("/")): errors.append(f"forbidden autonomous path: {path}")
        elif not any(path.startswith(p) for p in ALLOWED): errors.append(f"path outside autonomous scope: {path}")
    return errors
if __name__=="__main__":
    errors=validate(changed_files())
    if errors: print("\n".join(errors),file=sys.stderr); raise SystemExit(1)
    print("autonomous change scope: PASS")
