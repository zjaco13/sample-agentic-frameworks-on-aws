resource "aws_api_gateway_rest_api" "agent_api" {
  name        = "${var.agent_name}-api"
  description = "API Gateway for ${var.agent_name}"
}

resource "aws_api_gateway_resource" "tasks" {
  rest_api_id = aws_api_gateway_rest_api.agent_api.id
  parent_id   = aws_api_gateway_rest_api.agent_api.root_resource_id
  path_part   = "tasks"
}

resource "aws_api_gateway_resource" "send" {
  rest_api_id = aws_api_gateway_rest_api.agent_api.id
  parent_id   = aws_api_gateway_resource.tasks.id
  path_part   = "send"

  depends_on = [
    aws_api_gateway_resource.tasks
  ]
}

resource "aws_api_gateway_method" "post_send" {
  rest_api_id   = aws_api_gateway_rest_api.agent_api.id
  resource_id   = aws_api_gateway_resource.send.id
  http_method   = "POST"
  authorization = "NONE"

  depends_on = [
    aws_api_gateway_resource.send
  ]
}

resource "aws_api_gateway_integration" "lambda_send" {
  rest_api_id = aws_api_gateway_rest_api.agent_api.id
  resource_id = aws_api_gateway_resource.send.id
  http_method = aws_api_gateway_method.post_send.http_method
  integration_http_method = "POST"
  type        = "AWS_PROXY"
  uri         = aws_lambda_function.agent_handler_lambda.invoke_arn

  depends_on = [
    aws_api_gateway_method.post_send
  ]
}

resource "aws_lambda_permission" "apigw_lambda" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.agent_handler_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.agent_api.execution_arn}/*/*"
}

resource "aws_api_gateway_deployment" "deployment" {
  rest_api_id = aws_api_gateway_rest_api.agent_api.id

  depends_on = [
    aws_api_gateway_integration.lambda_send,
    aws_api_gateway_integration.agent_card_integration
  ]

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "stage" {
  stage_name    = "dev"
  rest_api_id   = aws_api_gateway_rest_api.agent_api.id
  deployment_id = aws_api_gateway_deployment.deployment.id
}

resource "aws_api_gateway_resource" "well_known" {
  rest_api_id = aws_api_gateway_rest_api.agent_api.id
  parent_id   = aws_api_gateway_rest_api.agent_api.root_resource_id
  path_part   = ".well-known"
}

resource "aws_api_gateway_resource" "agent_json" {
  rest_api_id = aws_api_gateway_rest_api.agent_api.id
  parent_id   = aws_api_gateway_resource.well_known.id
  path_part   = "agent.json"
}

resource "aws_api_gateway_method" "get_agent_card" {
  rest_api_id   = aws_api_gateway_rest_api.agent_api.id
  resource_id   = aws_api_gateway_resource.agent_json.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "agent_card_integration" {
  rest_api_id             = aws_api_gateway_rest_api.agent_api.id
  resource_id             = aws_api_gateway_resource.agent_json.id
  http_method             = aws_api_gateway_method.get_agent_card.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.agent_card_lambda.invoke_arn
}

resource "aws_lambda_permission" "allow_agent_card_api" {
  statement_id  = "AllowAgentCardApi"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.agent_card_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.agent_api.execution_arn}/*/GET/.well-known/agent.json"
}