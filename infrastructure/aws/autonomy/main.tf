terraform {
  required_version = ">= 1.8.0"
  required_providers { aws = { source = "hashicorp/aws", version = "~> 6.0" } }
}
provider "aws" { region = var.aws_region }
data "aws_iam_policy_document" "github_oidc_trust" {
  statement {
    effect = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals { type = "Federated" identifiers = [var.github_actions_oidc_provider_arn] }
    condition { test = "StringEquals" variable = "token.actions.githubusercontent.com:aud" values = ["sts.amazonaws.com"] }
    condition { test = "StringLike" variable = "token.actions.githubusercontent.com:sub" values = ["repo:${var.github_repository}:ref:refs/heads/main"] }
  }
}
resource "aws_iam_role" "autonomous_engineer" {
  name = "${var.name_prefix}-autonomous-engineer"
  assume_role_policy = data.aws_iam_policy_document.github_oidc_trust.json
  max_session_duration = 3600
}
data "aws_iam_policy_document" "bedrock" {
  statement {
    effect    = "Allow"
    actions   = ["bedrock:InvokeModel", "bedrock:Converse"]
    resources = concat([var.bedrock_model_arn], var.bedrock_inference_profile_arns)
  }

  statement {
    effect    = "Allow"
    actions   = ["bedrock:GetInferenceProfile", "bedrock:ListInferenceProfiles"]
    resources = ["*"]
  }
}
resource "aws_iam_role_policy" "bedrock" {
  name = "${var.name_prefix}-bedrock-invoke"
  role = aws_iam_role.autonomous_engineer.id
  policy = data.aws_iam_policy_document.bedrock.json
}
output "github_actions_role_arn" { value = aws_iam_role.autonomous_engineer.arn }
output "github_actions_role_name" { value = aws_iam_role.autonomous_engineer.name }
