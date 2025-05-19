resource "aws_iam_role" "lambda_exec" {
  name = "${var.app_name}-${var.env_name}-${var.agent_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_log_access" {
  name = "${var.app_name}-${var.env_name}-${var.agent_name}-lambda-log"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = [
          "*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_s3_dynamodb_access" {
  name = "${var.app_name}-${var.env_name}-${var.agent_name}-s3-policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "dynamodb:PutItem",
          "dynamodb:GetItem"
        ],
        Resource = [
          "arn:aws:s3:::${var.lambda_bucket_handler}",
          "arn:aws:s3:::${var.lambda_bucket_handler}/*",
          "arn:aws:s3:::${var.lambda_bucket_card}",
          "arn:aws:s3:::${var.lambda_bucket_card}/*",
          "arn:aws:dynamodb:${var.aws_region}:*:table/${var.trade_log_table_name}"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_apigateway_access" {
  name = "${var.app_name}-${var.env_name}-apigateway-access"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "apigateway:GET",
          "apigateway:HEAD",
          "apigateway:OPTIONS"
        ],
        Resource = [
          "arn:aws:apigateway:${var.aws_region}::/restapis",
          "arn:aws:apigateway:${var.aws_region}::/restapis/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_bedrock_access" {
  name = "${var.app_name}-${var.env_name}-${var.agent_name}-bedrock-policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ],
        Resource = "*"
      }
    ]
  })
}
