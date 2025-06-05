resource "aws_s3_bucket" "lambda_bucket_handler" {
  bucket = var.lambda_bucket_handler
}

data "archive_file" "lambda_zip_handler" {
  type        = "zip"
  source_dir  = "${path.root}/main"
  output_path = "${path.root}/lambda/handler.zip"
}

resource "aws_s3_object" "lambda_zip_handler" {
  bucket = aws_s3_bucket.lambda_bucket_handler.id
  key    = var.lambda_key_handler
  source = data.archive_file.lambda_zip_handler.output_path
  etag   = filemd5(data.archive_file.lambda_zip_handler.output_path)
}

resource "aws_lambda_function" "agent_handler_lambda" {
  function_name = "${var.app_name}-${var.env_name}-${var.agent_name}"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  architectures = ["arm64"]
  timeout       = var.timeout
  memory_size   = var.memory_size
  s3_bucket     = var.lambda_bucket_handler
  s3_key        = var.lambda_key_handler

  environment {
    variables = merge(
      {
        SKILLS             = join(",", var.skills)
        AWS_PRIMARY_REGION = var.aws_region
        BEDROCK_MODEL_ID   = var.bedrock_model_id
      },
        var.agent_name == "TradeExecutionAgent" ? {
        TRADE_LOG_TABLE = var.trade_log_table_name
      } : {}
    )
  }

  layers = var.custom_layer

  depends_on = [
    aws_s3_object.lambda_zip_handler,
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy.lambda_s3_dynamodb_access,
    aws_iam_role_policy.lambda_bedrock_access
  ]
}

resource "null_resource" "invoke_lambda" {
  depends_on = [aws_lambda_function.agent_handler_lambda]

  provisioner "local-exec" {
    command = <<EOT
      aws lambda invoke \
        --function-name ${aws_lambda_function.agent_handler_lambda.function_name} \
        --payload '{"RequestType": "Create"}' \
        --invocation-type RequestResponse \
        --cli-binary-format raw-in-base64-out \
        --region ${var.aws_region} \
        response.json
    EOT
  }

  triggers = {
    always_run = timestamp()
  }
}

resource "aws_s3_bucket" "lambda_bucket_card" {
  bucket = var.lambda_bucket_card
}

data "archive_file" "lambda_zip_card" {
  type        = "zip"
  source_file = "${path.root}/agent_card.py"
  output_path = "${path.root}/lambda/agent_card.zip"
}

resource "aws_s3_object" "lambda_zip_card" {
  bucket = aws_s3_bucket.lambda_bucket_card.id
  key    = var.lambda_key_card
  source = data.archive_file.lambda_zip_card.output_path
  etag   = filemd5(data.archive_file.lambda_zip_card.output_path)
}

resource "aws_lambda_function" "agent_card_lambda" {
  function_name = "${var.app_name}-${var.env_name}-${var.agent_name}-card-handler"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "agent_card.lambda_handler"
  runtime       = "python3.12"
  architectures = ["arm64"]
  timeout       = var.timeout
  memory_size   = var.memory_size
  s3_bucket     = var.lambda_bucket_card
  s3_key        = var.lambda_key_card

  environment {
    variables = {
      AWS_PRIMARY_REGION = var.aws_region
      BEDROCK_MODEL_ID   = var.bedrock_model_id
    }
  }

  depends_on = [
    aws_s3_object.lambda_zip_card,
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy.lambda_s3_dynamodb_access
  ]
}