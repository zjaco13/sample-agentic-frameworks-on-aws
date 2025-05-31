import asyncio
import argparse
import json
import logging
import os
import sys
import subprocess
import time
from typing import Dict, List, Any, Optional
from contextlib import AsyncExitStack

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp-sse-test")

# Import MCP client libraries
try:
    from mcp import ClientSession
    from mcp.client.sse import sse_client
except ImportError:
    logger.error("MCP client libraries not found. Please install them with: pip install mcp")
    sys.exit(1)

# Server information
SERVER_INFO = {
    "news": {
        "name": "Financial News",
        "port": 8085,
        "server_path": "libs/mcp-servers/web_news_server.py",
        "tools": ["financial_news", "web_search"]
    },
    "analysis": {
        "name": "Financial Analysis",
        "port": 8086,
        "server_path": "libs/mcp-servers/financial_analysis_server.py",
        "tools": ["fundamental_data_by_category", "technical_data_by_category", "comprehensive_analysis"]
    },
    "stock": {
        "name": "Stock Market",
        "port": 8083,
        "server_path": "libs/mcp-servers/stock_market_server.py",
        "tools": ["yahoo_stock_quote", "yahoo_market_data", "yahoo_stock_history"]
    }
}

# Default test parameters if none provided
TEST_PARAMS = {
    "financial_news": [
        {"symbol": "AMZN", "count": 3}
    ],
    "web_search": {"query": "financial markets news", "max_results": 3},
    
    # Financial Analysis tools
    "fundamental_data_by_category": {"equity": "AMZN", "categories": "company_info"},
    "technical_data_by_category": {"equity": "AMZN", "categories": "price"},
    "comprehensive_analysis": {"equity": "AMZN"},
    
    # Stock Market tools
    "yahoo_stock_quote": {"symbol": "AAPL"},
    "yahoo_market_data": {"indices": ["^GSPC", "^DJI", "^IXIC"]},
    "yahoo_stock_history": {"symbol": "TSLA", "period": "1mo", "interval": "1d"}
}

class MCPServerTester:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.server_process = None
        self._session_context = None
        self._streams_context = None
    
    async def start_server(self, server_key: str) -> bool:
        """
        Start the MCP server in a subprocess
        """
        if server_key not in SERVER_INFO:
            logger.error(f"Unknown server key: {server_key}")
            return False
        
        server_info = SERVER_INFO[server_key]
        current_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(current_dir, server_info["server_path"])
        
        if not os.path.exists(script_path):
            logger.error(f"{server_info['name']} server script not found at: {script_path}")
            return False
        
        port = server_info["port"]
        logger.info(f"Starting {server_info['name']} server on port {port}")
        
        try:
            # Start the server process
            self.server_process = subprocess.Popen(
                [sys.executable, script_path, "--port", str(port), "--sse"], 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Give the server a moment to start
            logger.info(f"Waiting for server to start...")
            time.sleep(3)
            
            # Check if process is still running
            if self.server_process.poll() is not None:
                stdout, stderr = self.server_process.communicate()
                logger.error(f"Server failed to start. Return code: {self.server_process.returncode}")
                logger.error(f"STDOUT: {stdout}")
                logger.error(f"STDERR: {stderr}")
                return False
            
            logger.info(f"{server_info['name']} server started successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error starting server: {str(e)}")
            return False
    
    async def connect_to_server(self, server_key: str) -> bool:
        """
        Connect to the MCP server using SSE transport
        """
        if server_key not in SERVER_INFO:
            logger.error(f"Unknown server key: {server_key}")
            return False
        
        server_info = SERVER_INFO[server_key]
        port = server_info["port"]
        server_url = f"http://localhost:{port}/sse"
        
        try:
            logger.info(f"Connecting to {server_info['name']} server at {server_url}")
            
            # Create SSE client connection
            self._streams_context = sse_client(url=server_url)
            streams = await self._streams_context.__aenter__()
            
            # Create client session
            self._session_context = ClientSession(*streams)
            self.session = await self._session_context.__aenter__()
            
            # Initialize the session
            await self.session.initialize()
            
            logger.info(f"Connected to {server_info['name']} server successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to server: {str(e)}")
            await self.cleanup_connection()
            return False
    
    async def list_tools(self) -> List[str]:
        """
        List all available tools on the server
        """
        if not self.session:
            logger.error("Not connected to any server")
            return []
        
        try:
            # Get tools list
            response = await self.session.list_tools()
            tools = response.tools
            
            if not tools:
                logger.warning("No tools found on server")
                return []
            
            # Print tool information
            logger.info(f"Found {len(tools)} tools:")
            for tool in tools:
                logger.info(f"  - {tool.name}: {tool.description.split('.')[0]}")
            
            return [tool.name for tool in tools]
            
        except Exception as e:
            logger.error(f"Error listing tools: {str(e)}")
            return []
    
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> bool:
        """
        Call a specific tool with parameters
        """
        if not self.session:
            logger.error("Not connected to any server")
            return False
        
        try:
            logger.info(f"Calling tool: {tool_name}")
            logger.info(f"Parameters: {params}")
            
            # Call the tool
            result = await self.session.call_tool(tool_name, params)
            
            # Process and display results
            logger.info("\nTool results:")
            print("=" * 80)
            for content_item in result.content:
                if content_item.type == "text":
                    print(content_item.text)
            print("=" * 80 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {str(e)}")
            return False
    
    async def test_all_tools(self, server_key: str) -> bool:
        """
        Test all tools for a specific server
        """
        if server_key not in SERVER_INFO:
            logger.error(f"Unknown server key: {server_key}")
            return False
        
        # Get available tools
        tools = await self.list_tools()
        
        if not tools:
            return False
        
        # Test each tool
        success_count = 0
        for tool_name in tools:
            params = TEST_PARAMS.get(tool_name, {})
            
            if isinstance(params, list):
                test_params = params[0]  
                logger.info(f"Testing tool {tool_name} with parameters: {test_params} (scenario 1 of {len(params)})")
            else:
                test_params = params
                logger.info(f"Testing tool {tool_name} with parameters: {test_params}")
            
            if await self.call_tool(tool_name, test_params):
                success_count += 1
            
            # Wait between calls to avoid rate limits
            await asyncio.sleep(1)
        
        logger.info(f"Tested {len(tools)} tools with {success_count} successful calls")
        return success_count > 0
    
    async def cleanup_connection(self):
        """
        Clean up connection resources
        """
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
            self._session_context = None
        
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)
            self._streams_context = None
    
    def cleanup_server(self):
        """
        Clean up server process
        """
        if self.server_process:
            logger.info("Terminating server process")
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                logger.warning("Server didn't terminate gracefully, forcing...")
                self.server_process.kill()
            self.server_process = None
    
    async def cleanup(self):
        """
        Clean up all resources
        """
        await self.cleanup_connection()
        self.cleanup_server()

async def main():
    parser = argparse.ArgumentParser(description="Test MCP servers using SSE transport")
    parser.add_argument("--server", choices=["news", "analysis", "stock"], default="news",
                        help="Server to test (news, analysis, or stock) [default: news]")
    parser.add_argument("--tool", help="Specific tool to test (optional)")
    parser.add_argument("--params", help="JSON parameters for the tool (optional)")
    parser.add_argument("--no-start", action="store_true",
                        help="Don't start the server (connect to already running server)")
    
    args = parser.parse_args()
    
    # Parse JSON parameters if provided
    tool_params = None
    if args.params:
        try:
            tool_params = json.loads(args.params)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON parameters: {args.params}")
            return
    
    tester = MCPServerTester()
    
    try:
        # Start server if needed
        if not args.no_start:
            if not await tester.start_server(args.server):
                return
        
        # Connect to server
        if not await tester.connect_to_server(args.server):
            return
        
        # Test tools
        if args.tool:
            # Test specific tool
            params = tool_params or TEST_PARAMS.get(args.tool, {})
            await tester.call_tool(args.tool, params)
        else:
            # Test all tools
            await tester.test_all_tools(args.server)
            
    finally:
        # Clean up resources
        await tester.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")