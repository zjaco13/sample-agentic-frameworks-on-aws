module "dynamodb_table" {
  source = "terraform-aws-modules/dynamodb-table/aws"

  name     = local.name
  hash_key = "id"

  attributes = [
    {
      name = "id"
      type = "N"
    }
  ]

  tags = local.tags
}

resource "random_pet" "weather" {
  length = 2
  prefix = var.weather_prefix
}

resource "aws_dynamodb_table" "weather_agent_state_table" {
  name         = random_pet.weather.id
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  tags = var.tags
}
