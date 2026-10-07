# Definition of Done

A production change requires applicable code, data, security, reliability, observability, testing, and release gates to pass.

## Code
- Follows current architecture and contracts
- Explicit errors and failure modes
- Externalized configuration
- No secrets

## Data
- Source identity and provenance preserved
- Correct observation/acquisition time
- License metadata preserved
- Hash/version retained where applicable
- Historical data never silently overwritten

## Security
- Authentication/authorization requirements defined
- Least privilege
- Sensitive-data handling documented
- Audit requirements satisfied
- Dependency/container security considered

## Reliability
- Bounded timeouts/retries
- Idempotency defined
- Recovery documented
- Health/readiness where applicable
- Backup/recovery implications documented

## Observability
- Structured logs
- Relevant metrics
- Correlation IDs where applicable
- Data-quality failures observable

## Testing
- Unit
- Contract/schema
- Integration
- Replay/regression for data pipelines
- Security where applicable
- Performance for critical paths

## Release
- CI passes
- Deployment/migration order documented
- Rollback/recovery documented
- Documentation updated
- Reproducible acceptance evidence attached
