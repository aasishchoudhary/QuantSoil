#!/usr/bin/env python3
"""Repository-level production acceptance gate.

This gate verifies static production invariants that do not require a target
cluster. It deliberately does not claim cloud, Kubernetes, DNS, TLS, OIDC,
or backup/PITR readiness; those require target infrastructure execution.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUIRED = [
    "ARCHITECTURE.md",
    "DATA_GOVERNANCE.md",
    "SECURITY.md",
    "DEFINITION_OF_DONE.md",
    "EVALUATION_POLICY.md",
    "Dockerfile",
    "k8s/namespace.yaml",
    "k8s/network-policy.yaml",
    "k8s/runtime.yaml",
    "k8s/web.yaml",
    "k8s/pdb.yaml",
    "scripts/backup_postgres.sh",
    "scripts/restore_postgres.sh",
    "scripts/production_cluster_acceptance.sh",
    "infrastructure/aws/evidence/main.tf",
    "infrastructure/aws/evidence/variables.tf",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            fail(f"required production artifact missing: {rel}")

    schema_dir = ROOT / "schemas"
    for path in sorted(schema_dir.glob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(f"invalid JSON schema {path}: {exc}")

    # Validate the same union of migration directories used by the runtime loader.
    migration_paths = sorted((ROOT / "db" / "migrations").glob("*.sql"))
    migration_paths += sorted((ROOT / "migrations").glob("*.sql"))
    if not migration_paths:
        fail("no SQL migration files found in migrations/ or db/migrations/")
    numbered = []
    pattern = re.compile(r"^(\d+)(?:[_-]|$)")
    for path in migration_paths:
        match = pattern.match(path.stem)
        if not match:
            fail(f"migration filename must begin with a numeric sequence: {path}")
        numbered.append((int(match.group(1)), path))
    numbered.sort(key=lambda item: (item[0], item[1].as_posix()))
    seen = {}
    for number, path in numbered:
        if number in seen:
            fail(f"duplicate migration sequence {number:03d}: {seen[number]} and {path}")
        seen[number] = path
    numbers = [number for number, _ in numbered]
    expected = list(range(numbers[0], numbers[-1] + 1))
    if numbers != expected:
        fail(f"migration chain has a numeric gap: found={numbers}, expected={expected}")

    namespace = (ROOT / "k8s/namespace.yaml").read_text(encoding="utf-8")
    network = (ROOT / "k8s/network-policy.yaml").read_text(encoding="utf-8")
    runtime = (ROOT / "k8s/runtime.yaml").read_text(encoding="utf-8")
    web = (ROOT / "k8s/web.yaml").read_text(encoding="utf-8")

    for label in ("pod-security.kubernetes.io/enforce: restricted",
                  "pod-security.kubernetes.io/audit: restricted",
                  "pod-security.kubernetes.io/warn: restricted"):
        if label not in namespace:
            fail(f"namespace missing Pod Security label: {label}")

    if "runtime-default-deny" not in network:
        fail("default-deny NetworkPolicy is missing")
    if "policyTypes: [Ingress, Egress]" not in network:
        fail("default-deny policy must cover ingress and egress")

    for name, manifest in (("runtime", runtime), ("web", web)):
        if "runAsNonRoot: true" not in manifest:
            fail(f"{name} workload is not explicitly non-root")
        if "allowPrivilegeEscalation: false" not in manifest:
            fail(f"{name} workload permits privilege escalation")
        if 'drop: ["ALL"]' not in manifest:
            fail(f"{name} workload does not drop ALL Linux capabilities")
        if "readOnlyRootFilesystem: true" not in manifest:
            fail(f"{name} workload does not use a read-only root filesystem")
        if "type: RuntimeDefault" not in manifest:
            fail(f"{name} workload does not explicitly select RuntimeDefault seccomp")

    for rel in ("scripts/backup_postgres.sh", "scripts/restore_postgres.sh", "scripts/production_cluster_acceptance.sh"):
        result = subprocess.run(["bash", "-n", str(ROOT / rel)], capture_output=True, text=True)
        if result.returncode:
            fail(f"{rel} has shell syntax errors: {result.stderr.strip()}")

    evidence_tf = (ROOT / "infrastructure/aws/evidence/main.tf").read_text(encoding="utf-8")
    for invariant in (
        "object_lock_enabled = true",
        'status = "Enabled"',
        "aws_s3_bucket_public_access_block",
        "aws_s3_bucket_server_side_encryption_configuration",
        "DenyInsecureTransport",
        'variable = "aws:SecureTransport"',
    ):
        if invariant not in evidence_tf:
            fail(f"S3 evidence Terraform baseline missing invariant: {invariant}")

    forbidden = re.compile(r"(AKIA[0-9A-Z]{16}|-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----)")
    for rel in ("Dockerfile", "k8s/runtime.yaml", "k8s/web.yaml"):
        if forbidden.search((ROOT / rel).read_text(encoding="utf-8")):
            fail(f"possible embedded credential detected in {rel}")

    print("PASS: repository production acceptance invariants")
    print(f"PASS: migration chain ({len(numbered)} files): {", ".join(path.as_posix() for _, path in numbered)}")
    print("PASS: schemas, Kubernetes hardening, network deny, S3 evidence baseline, shell syntax, secret scan")
    print("DEFERRED: target-cluster/OIDC/TLS/load/PITR acceptance requires real infrastructure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
