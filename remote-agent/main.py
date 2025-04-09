from fastapi import FastAPI, Request, BackgroundTasks
from sse_starlette.sse import EventSourceResponse
from fastapi.responses import JSONResponse
from typing import Dict, Set, Optional, Any, List
import asyncio
import json
import uuid
import uvicorn
from tools import MCPClient, create_mcp_tools
from graph import run_graph

app = FastAPI()

# Store connected clients and their MCPClient instances
CLIENTS: Dict[str, Set[asyncio.Queue]] = {}
MCP_CLIENTS: Dict[str, MCPClient] = {}

async def send_command_to_client(client_id: str, command: dict):
    if client_id in CLIENTS:
        for queue in CLIENTS[client_id]:
            await queue.put(command)

@app.get("/connect/{client_id}")
async def connect_client(client_id: str):
    if client_id not in CLIENTS:
        CLIENTS[client_id] = set()
        # Create MCPClient instance for this client
        MCP_CLIENTS[client_id] = MCPClient(client_id=client_id, send_command_func=send_command_to_client)
    
    queue = asyncio.Queue()
    CLIENTS[client_id].add(queue)
    print(f"Client {client_id} connected")
    
    async def event_generator():
        try:
            while True:
                if queue.empty():
                    # Send heartbeat every 15 seconds
                    await asyncio.sleep(15)
                    yield {
                        "event": "heartbeat",
                        "data": "ping"
                    }
                else:
                    command = await queue.get()
                    yield {
                        "event": "command",
                        "data": json.dumps(command)
                    }
        except asyncio.CancelledError:
            CLIENTS[client_id].remove(queue)
            if not CLIENTS[client_id]:
                del CLIENTS[client_id]
                if client_id in MCP_CLIENTS:
                    del MCP_CLIENTS[client_id]
            print(f"Client {client_id} disconnected")
            
    return EventSourceResponse(event_generator())

@app.post("/result/{client_id}")
async def receive_result(client_id: str, request: Request):
    result_data = await request.json()
    print(f"Received result from client {client_id}: {result_data}")
    
    # Process the result using the appropriate MCPClient instance
    if client_id in MCP_CLIENTS:
        command_id = result_data.get("commandId")
        result = result_data.get("result")
        if command_id and result:
            MCP_CLIENTS[client_id].receive_result(command_id, result)
    
    return {"status": "received"}

# Endpoint for agent to process user requests
@app.post("/agent/{client_id}")
async def agent_endpoint(client_id: str, request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    user_input = data.get("input")
    
    if not user_input:
        return JSONResponse(status_code=400, content={"status": "error", "message": "No input provided"})
    
    if client_id not in MCP_CLIENTS:
        # Create MCPClient instance if it doesn't exist
        MCP_CLIENTS[client_id] = MCPClient(client_id=client_id, send_command_func=send_command_to_client)
    
    # Create MCP tools
    tools = await create_mcp_tools(client_id, send_command_func=send_command_to_client)
    
    # Run the agent in the background to avoid blocking
    background_tasks.add_task(process_agent_request, client_id, user_input, tools)
    
    return {"status": "processing", "message": f"Processing request for client {client_id}"}

async def process_agent_request(client_id: str, user_input: str, tools: List[Any]):
    try:
        # Run the graph with the user input
        result = await run_graph(client_id, user_input, tools)
        print(f"Agent result for client {client_id}: {result}")
        # Here you could send the result back to a user interface or store it
    except Exception as e:
        print(f"Error processing agent request: {e}")

# Test endpoint to send a command to a client
@app.post("/test/send_command/{client_id}")
async def test_send_command(client_id: str, request: Request):
    command = await request.json()
    print(f"Sending command to client {client_id}: {command}")
    await send_command_to_client(client_id, command)
    return {"status": "command sent"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug") 