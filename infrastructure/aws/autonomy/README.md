# Autonomous Engineering AWS Runtime

This module provisions the minimum AWS trust boundary for the GitHub Actions engineering worker.

GitHub Actions exchanges its OIDC identity for a short-lived AWS role session. The role can
invoke only the explicitly supplied Bedrock model ARN. It has no S3, EC2, Secrets Manager,
IAM administration, or broad Bedrock permissions.

Apply with an administrator-controlled Terraform identity. Copy the resulting
github_actions_role_arn into the repository variable GODS_EYE_AWS_ROLE_ARN.

The trust policy is restricted to this repository's main branch. Do not commit Terraform
state, credentials, or account-specific secrets.
