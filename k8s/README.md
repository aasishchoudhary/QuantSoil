# Runtime deployment

This manifest is a deployment template. Secrets and cloud permissions stay outside source control.

## Required external configuration

Create the `world-intelligence-runtime` Secret out of band with:
- `DATABASE_URL`: PostgreSQL 16+ connection string to a PostGIS-enabled database (PostGIS 3.x is required by the geospatial migration).
- `EVIDENCE_BUCKET`: private S3 bucket name.

Do not commit the Secret or credentials. In AWS/EKS, grant the service account only the S3 permissions required for the evidence prefix and use workload identity/IRSA rather than static AWS keys.

Pin the container image to a release digest before production rollout; the example tag is a repository-local placeholder.

## Database rollout

1. Deploy the image.
2. Run the migration Job and verify it completes successfully.
3. Deploy or roll the runtime Deployment.
4. Confirm `/health/ready` returns HTTP 200.
5. Confirm runtime jobs and ingestion audits are advancing.
6. Roll back the Deployment image if application health fails. Never roll back a database migration blindly; use a forward-compatible migration.

## Evidence storage

Keep the evidence bucket private with Block Public Access enabled. For immutable evidence, enable Versioning and Object Lock at bucket creation and apply a documented retention policy.

## Scaling

Multiple runtime replicas are supported because PostgreSQL claims use row-level `FOR UPDATE SKIP LOCKED` and enqueue uses deterministic idempotency keys. Keep lease duration longer than expected connector execution time and monitor expired-lease reclamation.

## Backup and recovery

Back up PostgreSQL with a PITR-capable managed policy and regularly test restore into an isolated environment. Protect the evidence bucket with Versioning and, where required, cross-region replication. Recovery is not complete until restored data passes schema validation, evidence hash verification, and replay/evaluation gates.

## Operational signals

Alert on readiness failures, repeated connector `error_type` values, jobs stuck in `running` past lease expiry, increasing `failed` jobs, rejected/stale records, evidence-payload persistence failures, and database connection failures.

Use UTC timestamps throughout the runtime and retain structured logs centrally.

## Recovery scripts

Use `scripts/backup_postgres.sh` for custom-format backups and `scripts/restore_postgres.sh` only against an isolated recovery target. Restore is intentionally guarded by `ALLOW_DESTRUCTIVE_RESTORE=1`. After restore, run schema validation, evidence hash verification, replay/evaluation gates, and analyst integration tests before routing traffic.

## Network isolation

Apply `k8s/namespace.yaml` and `k8s/network-policy.yaml` with the database namespace/pod labels adjusted to the actual PostgreSQL deployment. The default policy denies ingress/egress; only runtime-to-database, runtime-to-HTTPS provider access, DNS, and web-to-runtime traffic should be allowed. Validate policies in the target cluster before rollout.
