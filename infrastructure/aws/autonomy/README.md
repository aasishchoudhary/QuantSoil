# Autonomous Engineering AWS Runtime

This module provisions the minimum AWS trust boundary for the GitHub Actions engineering worker.

GitHub Actions exchanges its OIDC identity for a short-lived AWS role session. The role can
invoke only the explicitly supplied Bedrock model ARN. It has no S3, EC2, Secrets Manager,
IAM administration, or broad Bedrock permissions.

Apply with an administrator-controlled Terraform identity. Copy the resulting
github_actions_role_arn into the repository variable GODS_EYE_AWS_ROLE_ARN.

The trust policy is restricted to this repository's main branch. Do not commit Terraform
state, credentials, or account-specific secrets.


## Bedrock inference profiles

The autonomous workflow runs in ap-south-1 and uses an ACTIVE APAC system-defined inference profile (for example, `apac.amazon.nova-lite-v1:0`). Set `bedrock_inference_profile_arns` to the exact profile ARN(s) permitted for invocation. The role also needs `bedrock:GetInferenceProfile` and `bedrock:ListInferenceProfiles` for discovery. Apply this module with an administrator-controlled Terraform identity before expecting the autonomous workflow to execute.

## Workflow discovery fallback

The autonomous workflow first discovers ACTIVE APAC Nova Lite/Micro system-defined inference profiles. The role needs bedrock:ListInferenceProfiles for that discovery. If policy intentionally omits discovery, set the GitHub repository variable GODS_EYE_BEDROCK_PROFILE_ID to an approved ID (apac.amazon.nova-lite-v1:0 or apac.amazon.nova-micro-v1:0) after confirming it is available in the target region and that the role's resource policy allows invocation of its profile ARN. This variable does not grant AWS permissions; IAM remains authoritative. Never use an unrestricted administrator policy to work around discovery failures.
