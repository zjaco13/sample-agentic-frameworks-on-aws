## Mem0 
![3p-agentic-frameworks](docs/mem0-aws.png)

Mem0 (pronounced “mem-zero”) enhances AI assistants by giving them persistent, contextual memory. AI systems using Mem0 actively learn from and adapt to user interactions over time.

Mem0’s memory layer combines LLMs with vector based storage. LLMs extract and process key information from conversations, while the vector storage enables efficient semantic search and retrieval of memories. This architecture helps AI agents connect past interactions with current context for more relevant responses.

## Mem0 Official Documentation

**Docs:** https://docs.mem0.ai/overview

## Mem0 + AWS

### Importing LLMs from Amazon Bedrock

**Strands Configuration:** 

You can use mem0 to store user and agent memories across agent runs to provide personalized experience. Below is the python implementation of using mem0 as a tool (mem0_memory) with your Strands agent:

```python
agent.tool.mem0_memory(action="store", content="Remember I like to tennis", user_id="alex")
```
