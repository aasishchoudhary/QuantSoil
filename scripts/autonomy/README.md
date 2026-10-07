# Autonomous Engineering Control Plane

This directory contains the bounded implementation worker used by the repository's 24/7 engineering loop.

## Trust model

- GitHub Actions supplies the scheduler, isolated job, repository token, logs and PR gate.
- Amazon Bedrock supplies model inference through the AWS SDK credential chain.
- No static AI API key is stored in the repository.
- The agent may read repository files and write only approved implementation/test/docs areas.
- Policy files and workflow definitions are protected from autonomous modification.
- The agent cannot execute arbitrary shell commands.
- Tests are deterministic and run before a branch is offered for review.
- Main is never modified directly by the agent.

AWS authentication should use short-lived OIDC/STS credentials or an IAM instance role.
The default model is Amazon Nova Pro in ap-south-1; model access remains an AWS account configuration concern.
