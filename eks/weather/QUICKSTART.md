# Demo AI Agents on EKS

<details>
<summary>Quick demo TLDR;</summary>

```bash
source ./scripts/infra.sh
source ./scripts/env.sh
source ./scripts/containers.sh
source ./scripts/kubernetes.sh
source ./scripts/ui.sh
# open http://localhost:8000/chat
# Login in UI with username: Alice password: Passw0rd@
# Prompt: What's the weather like in San Francisco for the next few days?
```
</details>




# Enable Bedrock Model on the Console

Enable a model that support tool callig, see [Supported models and model features](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-supported-models-features.html).

For this example, request model access for **Claude 3.7 Sonnet** in the [AWS Bedrock Console](https://console.aws.amazon.com/bedrock/home#/modelaccess)

# Setup Infra including EKS Auto Mode Cluster
```bash
terraform -chdir=../terraform apply --auto-approve
```

Review the new EKS cluster in the console by visiting the [AWS EKS Console](https://console.aws.amazon.com/eks/home)


# Agent Code

Open the Agent code, go to line 162
```bash
code -g src/agent.py:162:9
```

This is how an Agent gets created:
```python
        agent = Agent(
            name=agent_name,
            description=agent_description,
            model=bedrock_model,
            system_prompt=system_prompt,
            tools=[agent_tools]+mcp_tools,
            messages=messages,
            conversation_manager=conversation_manager
        )
```


# Build and Push Images (Agent, MCP, UI) to ECR
>Make sure your docker cli is login into ecr and configured for buildx(MacOS only). See [README.md](README.md) for more details


Get the enviroment variables for your ECR repositories
```bash
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
export AWS_REGION=${aws configure get region}
```


```bash
docker build --platform linux/amd64 -t ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/agents-on-eks/weather-agent .
```

```bash
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/agents-on-eks/weather-agent
```

Build and push the other mcp server and ui images the same way see [README.md](README.md) for specific commands

Review the new images cluster in the console by visiting the [AWS ECR Console](https://console.aws.amazon.com/ecr/private-registry/repositories)

# Deploy the Containers (Agent, MCP, UI)

Review the `helm/agent-values.yaml`

```bash
code helm/agent-values.yaml
```

The values specifies the mcp server running on the EKS cluster; the repository depends on account and region:
```yaml
image:
  repository: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/agents-on-eks/weather-agent
  tag: latest
env:
  DYNAMODB_AGENT_STATE_TABLE_NAME: ${DYNAMODB_AGENT_STATE_TABLE_NAME}
  OAUTH_JWKS_URL: ${OAUTH_JWKS_URL}
mcp:
  mcp.json: |
    {
      "mcpServers": {
        "weather-mcp-http": {
          "url": "http://weather-mcp:8080/mcp"
        }
      }
    }
```

```bash
cd helm/
helm install weather-agent . -n weather-agent -f agent-values.yaml
cd ..
```

Review the 3 pods running (MCP, Agent, UI) or go to [AWS EKS Console Resource view](https://console.aws.amazon.com/eks/clusters/agentic-ai-on-eks?&selectedResourceId=pods&selectedTab=cluster-resources-tab)

Or check in the terminal
```bash
kubectl get pods -A
```

# Start the UI to access your Agent

```bash
kubectl port-forward svc/agent-ui 8000:fastapi -n agent-ui
```

Open the Agent UI [http://localhost:8000/chat](http://localhost:8000/chat)

Login with `Alice` and password `Passw0rd@`

Ask the question:
```prompt
How's the weather looking in San Francisco for the next few days?
```

Check the agent logs
```bash
kubectl logs -n weather-agent deploy/weather-agent -f
```

You can ask another question about weather forecast or alerts, without specifying the city, since the Agent remembers.
```prompt
Any weather alerts?
```
