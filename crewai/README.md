## CrewAI 
![3p-agent-frameworks](assets/crewai-aws.png)

CrewAI, a Python-based open-source framework, simplifies the creation and management of multi-agent systems, enabling agents to work together seamlessly, tackling complex tasks through collaborative intelligence.

## CrewAI Official Documentation

Docs: https://docs.crewai.com/introduction 

## CrewAI + AWS

# Importing LLMs from Amazon Bedrock

Model ID: https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html

```
AWS_ACCESS_KEY_ID=<your-access-key>
AWS_SECRET_ACCESS_KEY=<your-secret-key>
AWS_DEFAULT_REGION=<your-region>

llm = LLM(
    model="bedrock/{model-id}"
)
```