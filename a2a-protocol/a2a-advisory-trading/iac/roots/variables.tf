variable "aws_region" {
  type        = string
  description = "AWS region to deploy into"
}

variable "app_name" {
  type        = string
  description = "Application name for resource naming"
}

variable "env_name" {
  type        = string
  description = "Environment name for resource naming"
}

variable "agent_type" {
  description = "Type of agent (market_analysis, portfolio_manager, etc.)"
  type        = string
}

variable "agent_name" {
  type        = string
  description = "Name of the agent (used for naming Lambda and API Gateway)"
}

variable "agent_intro" {
  type        = string
  description = "Description of the agent"
}

variable "skills" {
  type        = list(string)
  description = "skills advertised by the agent"
}

variable "memory_size" {
  type        = number
  default     = 512
  description = "Lambda memory size (in MB)"
}

variable "timeout" {
  type        = number
  default     = 10
  description = "Lambda timeout (in seconds)"
}

variable "lambda_bucket_handler" {
  type        = string
  description = "S3 bucket name for lambda code"
}

variable "lambda_bucket_card" {
  type        = string
  description = "S3 bucket name for agent card"
}

variable "lambda_key_handler" {
  type        = string
  description = "S3 key (path) to the handler zip file"
}

variable "lambda_key_card" {
  type        = string
  description = "S3 key (path) to the agent card zip file"
}

variable "custom_layer" {
  type        = list(string)
  description = "ARN(s) of the custom layer(s)"
  default     = []
}

variable "bedrock_model_id" {
  type        = string
  description = "Bedrock model ID used by the agent"
  default     = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
}

variable "trade_log_table_name" {
  type        = string
  description = "Name of the DynamoDB table to write trade decision"
}
