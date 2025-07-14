#!/bin/bash

WEATHER_DST_FILE_NAME=${WEATHER_DST_FILE_NAME:-../weather/.env}
echo "> Injecting values into $WEATHER_DST_FILE_NAME"
echo "" > $WEATHER_DST_FILE_NAME

echo "> Parsing Terraform outputs"
TERRAFORM_OUTPUTS_MAP=$(terraform output --json outputs_map)
#echo $TERRAFORM_OUTPUTS_MAP
OAUTH_JWKS_URL=$(echo "$TERRAFORM_OUTPUTS_MAP" | jq -r ".cognito_jwks_url")
BEDROCK_MODEL_ID=$(terraform output -json bedrock_model_id)
DYNAMODB_AGENT_STATE_TABLE_NAME=$(terraform output -json weather_agent_table_name)
echo "OAUTH_JWKS_URL=$OAUTH_JWKS_URL"
echo "BEDROCK_MODEL_ID=$BEDROCK_MODEL_ID"
echo "DYNAMODB_AGENT_STATE_TABLE_NAME=$DYNAMODB_AGENT_STATE_TABLE_NAME"

echo "OAUTH_JWKS_URL=\"$OAUTH_JWKS_URL\"" >> $WEATHER_DST_FILE_NAME
echo "BEDROCK_MODEL_ID=$BEDROCK_MODEL_ID" >> $WEATHER_DST_FILE_NAME
echo "DYNAMODB_AGENT_STATE_TABLE_NAME=$DYNAMODB_AGENT_STATE_TABLE_NAME" >> $WEATHER_DST_FILE_NAME

echo "> Done"

# I want to create the following file in ../weather/helm/agent-values.yaml with the following content
# image:
#   repository: 015299085168.dkr.ecr.us-west-2.amazonaws.com/agents-on-eks/weather-agent
# env:
#   DYNAMODB_AGENT_STATE_TABLE_NAME: weather-agent-huge-fish
#   OAUTH_JWKS_URL: https://cognito-idp.us-west-2.amazonaws.com/us-west-2_sel2iyxmz/.well-known/jwks.json
WEATHER_HELM_VALUES_DST_FILE_NAME=${WEATHER_HELM_VALUES_DST_FILE_NAME:-../weather/.env}
ECR_REPO_WEATHER_AGENT_URI=$(terraform output -json ecr_weather_agent_repository_url)
echo "> Creating $WEATHER_HELM_VALUES_DST_FILE_NAME"
echo "ECR_REPO_WEATHER_AGENT_URI=$ECR_REPO_WEATHER_AGENT_URI"
cat <<EOF > ../weather/helm/agent-values.yaml
image:
  repository: $ECR_REPO_WEATHER_AGENT_URI
env:
  DYNAMODB_AGENT_STATE_TABLE_NAME: $DYNAMODB_AGENT_STATE_TABLE_NAME
  OAUTH_JWKS_URL: "$OAUTH_JWKS_URL"
mcp:
  mcp.json: |
    {
      "mcpServers": {
        "weather-mcp-http": {
          "url": "http://weather-mcp:8080/mcp/"
        }
      }
    }
EOF
