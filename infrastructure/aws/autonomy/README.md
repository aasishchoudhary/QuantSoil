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

## Workflow profile selection fallback

The workflow supports the optional GitHub repository variable `GODS_EYE_BEDROCK_PROFILE_ID` when the runtime role intentionally does not have `bedrock:ListInferenceProfiles` discovery permission. The value must be one of the workflow's allowlisted IDs (`apac.amazon.nova-lite-v1:0` or `apac.amazon.nova-micro-v1:0`). Before setting it, confirm that the profile is available in `ap-south-1` and that the role's invocation policy contains the exact corresponding profile ARN. This fallback does not grant permissions; if invocation is denied, use the least-privilege Terraform policy and runbook.
