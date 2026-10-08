variable "aws_region" { type = string description = "AWS region containing the Bedrock model." default = "ap-south-1" }
variable "name_prefix" { type = string description = "Prefix for autonomous engineering IAM resources." default = "gods-eye" }
variable "github_repository" {
  type = string
  description = "GitHub repository in owner/name form."
  validation { condition = can(regex("^[^/]+/[^/]+$", var.github_repository)) error_message = "github_repository must use owner/name form." }
}
variable "github_actions_oidc_provider_arn" { type = string description = "ARN of the GitHub Actions OIDC provider in this AWS account." }
variable "bedrock_model_arn" { type = string description = "Exact ARN of the Bedrock foundation model the agent may invoke." }

variable "bedrock_inference_profile_arns" {
  type        = list(string)
  description = "Explicit Bedrock inference-profile ARNs the autonomous worker may invoke."
  default     = []
}
