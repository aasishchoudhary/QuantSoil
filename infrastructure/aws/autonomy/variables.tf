variable "aws_region" { type = string default = "ap-south-1" }
variable "name_prefix" { type = string default = "gods-eye" }
variable "github_repository" { type = string }
variable "github_actions_oidc_provider_arn" { type = string }
variable "bedrock_model_arn" { type = string }
variable "bedrock_inference_profile_arns" {
  type        = list(string)
  description = "Explicit Bedrock inference-profile ARNs the autonomous worker may invoke."
  default     = []
}
