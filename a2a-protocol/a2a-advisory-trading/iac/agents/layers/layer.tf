resource "random_id" "suffix" {
  byte_length = 8
}

resource "aws_s3_bucket" "layer_bucket" {
  bucket = "${var.app_name}-${var.env_name}-layer-${random_id.suffix.hex}"
}

resource "aws_s3_object" "a2a_layer" {
  bucket = aws_s3_bucket.layer_bucket.id
  key    = "layers/a2a_layer.zip"
  source = "${path.module}/a2a_layer.zip"
  etag   = filemd5("${path.module}/a2a_layer.zip")
}

resource "aws_lambda_layer_version" "a2a_layer" {
  layer_name          = "a2a_layer"
  s3_bucket          = aws_s3_bucket.layer_bucket.id
  s3_key             = aws_s3_object.a2a_layer.key
  description        = "Layer containing a2a_core and dependencies"
  compatible_runtimes = ["python3.12"]
  compatible_architectures = ["arm64"]
}
