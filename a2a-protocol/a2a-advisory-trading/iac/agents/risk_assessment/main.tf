resource "random_id" "suffix" {
  byte_length = 8
}

module "layers" {
  source = "../layers"
  app_name = var.app_name
  env_name = var.env_name
}

module "risk_assessment" {
  source                = "../../roots"
  app_name              = var.app_name
  env_name              = var.env_name
  aws_region            = var.aws_region
  agent_name            = "RiskAssessmentAgent"
  agent_type            = "risk_assessment"
  agent_intro           = "Provides risk evaluation insights."
  lambda_key_handler    = "lambda/risk_assessment"
  lambda_key_card       = "lambda/agent_card_risk_assessment"
  lambda_bucket_handler = "${var.app_name}-${var.env_name}-lambda-risk-assessment-${random_id.suffix.hex}"
  lambda_bucket_card    = "${var.app_name}-${var.env_name}-lambda-risk-assessment-agent-card-${random_id.suffix.hex}"
  skills                = ["RiskEvaluation"]
  memory_size           = 512
  timeout               = 29
  bedrock_model_id      = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
  custom_layer          = [module.layers.layer_arn]
  trade_log_table_name  = "${var.app_name}-${var.env_name}-risk-assessment"
}
