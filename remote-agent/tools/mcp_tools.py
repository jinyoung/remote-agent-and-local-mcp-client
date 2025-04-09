import uuid
import asyncio
import inspect
from typing import Any, Dict, List, Optional, Callable, Type, get_type_hints, ClassVar
from pydantic import BaseModel, Field, create_model
from langchain.tools import BaseTool, Tool
import httpx
    
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

class MCPToolInput(BaseModel):
    """Default input model for MCP tools."""
    pass

# Instead of subclassing BaseTool, we'll use Tool factory function to avoid Pydantic issues
async def create_mcp_tool_function(
    client: MCPClient,
    tool_name: str,
    display_name: str,
    description: str,
    args_schema: Type[BaseModel],
) -> Callable:
    """Create an MCP tool function that can be used with the Tool class."""
    
    async def _func(**kwargs):
        """The actual function that will be executed."""
        try:
            if not client:
                return {"error": "MCP client not provided"}
            result = await client.send_command(tool_name, kwargs)
            return result
        except Exception as e:
            return {"error": str(e)}
    
    # Set proper function name and docstring
    _func.__name__ = display_name
    _func.__doc__ = description
    
    return _func

async def fetch_mcp_tools(client_id: str) -> List[Dict[str, Any]]:
    """Fetch tool definitions from the local MCP client."""
    # This is kept for backward compatibility but is no longer the primary method
    # of getting tool definitions, as they should now be registered by the client
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:3000/tools")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to fetch MCP tools: {response.status_code}")
                return []
    except Exception as e:
        print(f"Error fetching MCP tools: {e}")
        # Return a default tool definition for fallback
        return [
            {
                "name": "mcp__playwright__browser_navigate",
                "display_name": "browser_navigate",
                "description": "Navigate to a URL",
                "parameters": {
                    "url": {
                        "type": "string",
                        "description": "The URL to navigate to"
                    }
                }
            }
        ]

def create_args_schema(tool_def: Dict[str, Any]) -> Type[BaseModel]:
    """Dynamically create a Pydantic model for tool arguments."""
    fields = {}
    for param_name, param_def in tool_def.get("parameters", {}).items():
        param_type = str  # Default to string
        if param_def.get("type") == "number":
            param_type = float
        elif param_def.get("type") == "integer":
            param_type = int
        elif param_def.get("type") == "boolean":
            param_type = bool
            
        fields[param_name] = (param_type, Field(..., description=param_def.get("description", "")))
    
    # Create a dynamic Pydantic model for the arguments
    model_name = f"{tool_def.get('display_name', 'MCPTool')}Input"
    return create_model(model_name, **fields)

async def create_mcp_tools(
    client_id: str = "default-client", 
    send_command_func: Optional[Callable] = None, 
    tool_definitions: Optional[List[Dict[str, Any]]] = None
) -> List[BaseTool]:
    """Create a list of MCP tools dynamically based on tool definitions."""
    # Create a single client instance that will be shared by all tools
    mcp_client = MCPClient(client_id=client_id, send_command_func=send_command_func)
    
    # Use provided tool definitions if available, otherwise try to fetch them
    tool_defs = tool_definitions
    
    tools = []
    for tool_def in tool_defs:
        try:
            # Create a Pydantic model for the tool's arguments
            args_schema = create_args_schema(tool_def)
            
            # Get tool metadata
            display_name = tool_def.get("display_name", tool_def.get("name"))
            mcp_tool_name = tool_def.get("name")
            description = tool_def.get("description", "")
            
            # Create the tool function
            tool_func = await create_mcp_tool_function(
                client=mcp_client,
                tool_name=mcp_tool_name,
                display_name=display_name,
                description=description,
                args_schema=args_schema
            )
            
            # Create a Tool using the factory function instead of subclassing BaseTool
            tool = Tool(
                name=display_name,
                description=description,
                func=tool_func,
                coroutine=tool_func,
                args_schema=args_schema
            )
                
            tools.append(tool)
        except Exception as e:
            print(f"Error creating tool for {tool_def.get('name')}: {e}")
    
    if not tools:
        # Fallback to the default browser_navigate tool if no tools were fetched
        try:
            print("No tools fetched or provided, using fallback browser_navigate tool")
            default_schema = create_model("BrowserNavigateInput", url=(str, Field(..., description="The URL to navigate to")))
            
            # Create fallback tool function
            fallback_func = await create_mcp_tool_function(
                client=mcp_client,
                tool_name="mcp__playwright__browser_navigate",
                display_name="browser_navigate",
                description="Navigate to a URL",
                args_schema=default_schema
            )
            
            # Create a Tool using the factory function
            default_tool = Tool(
                name="browser_navigate",
                description="Navigate to a URL",
                func=fallback_func,
                coroutine=fallback_func,
                args_schema=default_schema
            )
            
            tools.append(default_tool)
        except Exception as e:
            print(f"Error creating fallback tool: {e}")
    
    return tools
