resource "random_id" "suffix" {
  byte_length = 8
}

module "layers" {
  source = "../layers"
  app_name = var.app_name
  env_name = var.env_name
}


module "market_analysis" {
  source                = "../../roots"
  app_name              = var.app_name
  env_name              = var.env_name
  aws_region            = var.aws_region
  agent_name            = "MarketAnalysisAgent"
  agent_type            = "market_analysis"
  agent_intro           = "Provides market analysis summaries."
  lambda_key_handler    = "lambda/market_analysis"
  lambda_key_card       = "lambda/agent_card_market_analysis"
  lambda_bucket_handler = "${var.app_name}-${var.env_name}-lambda-market-analysis-${random_id.suffix.hex}"
  lambda_bucket_card    = "${var.app_name}-${var.env_name}-lambda-market-analysis-agent-card-${random_id.suffix.hex}"
  skills                = ["MarketSummary"]
  memory_size           = 512
  timeout               = 29
  bedrock_model_id      = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
  custom_layer          = [module.layers.layer_arn]
  trade_log_table_name  = "${var.app_name}-${var.env_name}-market-analysis"
}
