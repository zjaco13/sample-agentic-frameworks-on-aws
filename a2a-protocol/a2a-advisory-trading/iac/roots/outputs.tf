output "api_endpoint" {
  value = "https://${aws_api_gateway_rest_api.agent_api.id}.execute-api.${var.aws_region}.amazonaws.com/dev/tasks/send"
}