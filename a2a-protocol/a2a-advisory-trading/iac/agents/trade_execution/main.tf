resource "random_id" "suffix" {
  byte_length = 8
}

module "shared_layer" {
  source = "../../shared"
}

module "trade_execution" {
  source                = "../../roots"
  app_name              = var.app_name
  env_name              = var.env_name
  aws_region            = var.aws_region
  agent_name            = "TradeExecutionAgent"
  agent_type            = "trade_execution"
  agent_intro           = "Executes trade requests and logs them to DynamoDB."
  lambda_key_handler    = "lambda/trade_execution"
  lambda_key_card       = "lambda/agent_card_trade_execution"
  lambda_bucket_handler = "${var.app_name}-${var.env_name}-lambda-trade-execution-${random_id.suffix.hex}"
  lambda_bucket_card    = "${var.app_name}-${var.env_name}-lambda-trade-execution-agent-card-${random_id.suffix.hex}"
  capabilities          = ["ExecuteTrade"]
  memory_size           = 512
  timeout               = 29
  custom_layer          = [module.shared_layer.a2a_core_layer_arn]
  trade_log_table_name  = "${var.app_name}-${var.env_name}-trade-execution"
}