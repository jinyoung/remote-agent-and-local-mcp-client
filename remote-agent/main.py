from fastapi import FastAPI, Request
from sse_starlette.sse import EventSourceResponse
from typing import Dict, Set
import asyncio
import json
import uuid
import uvicorn

app = FastAPI()

# Store connected clients
CLIENTS: Dict[str, Set[asyncio.Queue]] = {}

async def send_command_to_client(client_id: str, command: dict):
    if client_id in CLIENTS:
        for queue in CLIENTS[client_id]:
            await queue.put(command)

@app.get("/connect/{client_id}")
async def connect_client(client_id: str):
    if client_id not in CLIENTS:
        CLIENTS[client_id] = set()
    
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
            print(f"Client {client_id} disconnected")
            
    return EventSourceResponse(event_generator())

@app.post("/result/{client_id}")
async def receive_result(client_id: str, request: Request):
    result = await request.json()
    print(f"Received result from client {client_id}: {result}")
    return {"status": "received"}

# Test endpoint to send a command to a client
@app.post("/test/send_command/{client_id}")
async def test_send_command(client_id: str, request: Request):
    command = await request.json()
    print(f"Sending command to client {client_id}: {command}")
    await send_command_to_client(client_id, command)
    return {"status": "command sent"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug") 