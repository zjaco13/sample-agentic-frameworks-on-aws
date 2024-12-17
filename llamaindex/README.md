## LlamaIndex
![3p-agentic-frameworks](assets/llamaindex-aws.png)

LlamaIndex is a framework for building context-augmented generative AI applications with LLMs including agents and workflows.

## LlamaIndex Official Documentation

**Docs:** https://docs.llamaindex.ai/en/stable/

## LlamaIndex + AWS

### Importing LLMs from Amazon Bedrock

**Model IDs Supported:** https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html

**LLM Configuration:** 
Boto3:
```
from llama_index.llms.bedrock import Bedrock

llm = Bedrock(
    model="amazon.titan-text-express-v1",
    aws_access_key_id="AWS Access Key ID to use",
    aws_secret_access_key="AWS Secret Access Key to use",
    aws_session_token="AWS Session Token to use",
    region_name="AWS Region to use, eg. us-east-1",
)

resp = llm.complete("Paul Graham is ")
```