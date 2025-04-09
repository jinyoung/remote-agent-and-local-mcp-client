import uuid
import asyncio
from typing import Any, Dict, List, Optional, Callable
from pydantic import BaseModel, Field
from langchain.tools import BaseTool

class MCPToolInput(BaseModel):
    """Input for browser_navigate"""
    url: str = Field(..., description="The URL to navigate to")
    
class MCPClient:
    """Client for communicating with MCP through the FastAPI server."""
    
    def __init__(self, client_id: str = "default-client", send_command_func: Optional[Callable] = None):
        self.client_id = client_id
        self.pending_results: Dict[str, asyncio.Future] = {}
        self.send_command_func = send_command_func
    
    async def send_command(self, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a command to the MCP client and wait for the result."""
        if self.send_command_func is None:
            raise ValueError("send_command_func not provided to MCPClient")
        
        command_id = str(uuid.uuid4())
        command = {
            "id": command_id,
            "tool": tool,
            "params": params
        }
        
        # Create a future to store the result
        future = asyncio.get_event_loop().create_future()
        self.pending_results[command_id] = future
        
        # Send the command
        await self.send_command_func(self.client_id, command)
        
        # Wait for the result with a timeout
        try:
            result = await asyncio.wait_for(future, timeout=60.0)
            return result
        except asyncio.TimeoutError:
            del self.pending_results[command_id]
            raise TimeoutError(f"Timeout waiting for result of command {command_id}")
    
    def receive_result(self, command_id: str, result: Dict[str, Any]) -> None:
        """Process a result received from the MCP client."""
        if command_id in self.pending_results:
            future = self.pending_results.pop(command_id)
            if not future.done():
                future.set_result(result)

class MCPTool(BaseTool):
    """browser_navigate"""
    
    name: str = "browser_navigate"
    description: str = "Navigate to a URL"
    args_schema: type[MCPToolInput] = MCPToolInput
    client: Optional[MCPClient] = None
    
    def __init__(self, client: MCPClient):
        super().__init__(client=client)
        self.client = client
    
    async def _arun(self, url: str) -> Dict[str, Any]:
        """Execute an asynchronous operation using the MCP client."""
        try:
            result = await self.client.send_command("mcp__playwright__browser_navigate", {"url": url})
            return result
        except Exception as e:
            return {"error": str(e)}
    
    def _run(self, url: str) -> Dict[str, Any]:
        """Run in a synchronous context by creating a new event loop."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self._arun(url))
        finally:
            loop.close()

# MCP Tool Factory Functions for common operations
async def create_mcp_tools(client_id: str = "default-client", send_command_func: Optional[Callable] = None) -> List[BaseTool]:
    """Create a list of MCP tools."""
    client = MCPClient(client_id=client_id, send_command_func=send_command_func)
    
    tool = MCPTool(client=client)
    return [tool]
