resource "aws_dynamodb_table" "trade_log_table" {
  name           = "${var.app_name}-${var.env_name}-trade-execution"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "confirmationId"

  attribute {
    name = "confirmationId"
    type = "S"
  }

  tags = {
    Environment = var.env_name
  }
}