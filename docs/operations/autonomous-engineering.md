# Autonomous Engineering — 24/7 Control Plane

## Objective

Continuously advance God's Eye through small, reviewable, evidence-backed engineering tasks while keeping main protected by deterministic CI and human review.

## Runtime

GitHub Actions runs the control loop on a five-minute schedule. GitHub documents five minutes as the shortest supported scheduled interval. Scheduled runs execute from the default branch, so the workflow itself must be merged to main before the loop activates.

The implementation worker uses Amazon Bedrock through the AWS SDK credential chain. The recommended deployment is GitHub OIDC -> tightly scoped AWS IAM role -> Bedrock. No long-lived AI API key is required.

## Safety boundaries

1. Start from main.
2. Use a unique autonomous run branch.
3. Read repository policy before implementation.
4. Receive one bounded task.
5. Edit only approved implementation, test, schema, migration, documentation and explicitly allowed project files.
6. Never edit policy or workflow files.
7. Never execute arbitrary shell commands.
8. Run the deterministic test suite.
9. Inspect the diff.
10. Push only the isolated branch.
11. Open a pull request; never merge main.

## Failure behavior

A failed model call, test suite, invalid write, permission failure, or timeout stops the current run. The next scheduled run can retry after the repository state is unchanged. Concurrent runs are serialized with GitHub Actions concurrency.

## Operational truth

24/7 means the control plane is scheduled continuously. It does not mean GitHub guarantees a job starts at the exact second every five minutes: scheduled workflows can be delayed or dropped under GitHub load. For strict continuous availability, a second runner/queue layer should be added later. This distinction is intentional and prevents false readiness claims.
