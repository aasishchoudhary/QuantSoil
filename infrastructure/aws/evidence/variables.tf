variable "aws_region" {
  type        = string
  description = "AWS region for the evidence bucket."
  default     = "ap-south-1"
}

variable "bucket_name" {
  type        = string
  description = "Globally unique S3 bucket name for QuantSoil evidence."
}

variable "environment" {
  type        = string
  description = "Deployment environment."
  default     = "production"
}

variable "object_lock_mode" {
  type        = string
  description = "S3 Object Lock default retention mode."
  default     = "COMPLIANCE"

  validation {
    condition     = contains(["COMPLIANCE", "GOVERNANCE"], var.object_lock_mode)
    error_message = "object_lock_mode must be COMPLIANCE or GOVERNANCE."
  }
}

variable "retention_days" {
  type        = number
  description = "Default immutable retention period for evidence objects."
  default     = 30

  validation {
    condition     = var.retention_days >= 1 && var.retention_days <= 36500
    error_message = "retention_days must be between 1 and 36500."
  }
}
