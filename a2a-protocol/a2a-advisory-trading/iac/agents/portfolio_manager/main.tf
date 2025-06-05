resource "random_id" "suffix" {
  byte_length = 8
}

module "layers" {
  source = "../layers"
  app_name = var.app_name
  env_name = var.env_name
}


module "portfolio_manager" {
  source                = "../../roots"
  app_name              = var.app_name
  env_name              = var.env_name
  aws_region            = var.aws_region
  agent_name            = "PortfolioManagerAgent"
  agent_type            = "portfolio_manager"
  agent_intro           = "Coordinates analysis, risk review, and trade execution."
  lambda_key_handler    = "lambda/portfolio_manager"
  lambda_key_card       = "lambda/agent_card_portfolio_manager"
  lambda_bucket_handler = "${var.app_name}-${var.env_name}-lambda-portfolio-manager-${random_id.suffix.hex}"
  lambda_bucket_card    = "${var.app_name}-${var.env_name}-lambda-portfolio-manager-agent-card-${random_id.suffix.hex}"
  custom_layer          = [module.layers.layer_arn]
  skills                = ["ReviewPortfolio"]
  memory_size           = 512
  timeout               = 29
  bedrock_model_id      = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
  trade_log_table_name  = "${var.app_name}-${var.env_name}-portfolio-manager"
}
