output "layer_arn" {
  value = aws_lambda_layer_version.a2a_layer.arn
}

output "layer_name" {
  value = aws_lambda_layer_version.a2a_layer.layer_name
}
