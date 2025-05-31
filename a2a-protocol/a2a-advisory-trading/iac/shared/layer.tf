resource "aws_lambda_layer_version" "a2a_core_layer" {
  filename            = "${path.module}/../layers/a2a_core.zip"
  layer_name          = "a2a_core"
  compatible_runtimes = ["python3.11"]
  source_code_hash    = filebase64sha256("${path.module}/../layers/a2a_core.zip")
}
