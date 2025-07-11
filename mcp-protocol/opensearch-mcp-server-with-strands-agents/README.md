# OpenSearch MCP Server

OpenSearch MCP Server enables AI assistants to seamlessly interact with OpenSearch clusters. It provides a robust interface for AI models to perform essential OpenSearch operations through natural language interactions.

For detailed implementation, examples, and documentation, visit the official repository:
[opensearch-mcp-server-py](https://github.com/opensearch-project/opensearch-mcp-server-py)

## Overview

The server acts as a bridge between AI models and OpenSearch clusters, supporting:
- Seamless integration with AI assistants and LLMs through the MCP protocol
- Support for both stdio and streaming server transports (SSE and Streamable HTTP)
- Built-in tools for common OpenSearch operations
- Easy integration with Q Developer CLI, Claude Desktop, LangChain, and Strands Agents
- Secure authentication using basic auth or IAM roles
- Multi-cluster support
- Tool filtering capabilities

## Installing opensearch-mcp-server-py
Opensearch-mcp-server-py can be installed from [PyPI](https://pypi.org/project/opensearch-mcp-server-py/) via pip:
```bash
pip install opensearch-mcp-server-py
```

## Available Tools
- [ListIndexTool](https://docs.opensearch.org/docs/latest/api-reference/cat/cat-indices/): Lists all indices in OpenSearch with full information including docs.count, docs.deleted, store.size, etc. If an index parameter is provided, returns detailed information about that specific index.
- [IndexMappingTool](https://docs.opensearch.org/docs/latest/ml-commons-plugin/agents-tools/tools/index-mapping-tool/): Retrieves index mapping and setting information for an index in OpenSearch.
- [SearchIndexTool](https://docs.opensearch.org/docs/latest/ml-commons-plugin/agents-tools/tools/search-index-tool/): Searches an index using a query written in query domain-specific language (DSL) in OpenSearch.
- [GetShardsTool](https://docs.opensearch.org/docs/latest/api-reference/cat/cat-shards/): Gets information about shards in OpenSearch.
- [ClusterHealthTool](https://docs.opensearch.org/docs/latest/api-reference/cluster-api/cluster-health/): Returns basic information about the health of the cluster.
- [CountTool](https://docs.opensearch.org/docs/latest/api-reference/search-apis/count/): Returns number of documents matching a query.
- [ExplainTool](https://docs.opensearch.org/docs/latest/api-reference/search-apis/explain/): Returns information about why a specific document matches (or doesn't match) a query.
- [MsearchTool](https://docs.opensearch.org/docs/latest/api-reference/search-apis/multi-search/): Allows to execute several search operations in one request.

## Integration with Strands Agents

See [opensearch_mcp_server](opensearch_mcp_server.ipynb) notebook for a comprehensive demonstration of integrating OpenSearch MCP server with Strands Agents.