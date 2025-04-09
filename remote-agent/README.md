# Remote Agent with LangGraph

This project implements a Remote Agent using LangGraph that can control local MCP (Multi-component Protocol) clients. It enables browser automation and other tasks through a language-based interface.

## Architecture

- **Remote Agent**: A FastAPI server with a LangGraph-based workflow for natural language task processing
- **Local MCP Client**: A TypeScript client that connects to the remote agent and executes MCP commands

## Setup

1. Install dependencies for the remote agent:

```bash
cd remote-agent
pip install -r requirements.txt
```

2. Install dependencies for the local MCP client:

```bash
cd local-mcp
npm install
```

## Running the System

1. Start the remote agent server:

```bash
cd remote-agent
python main.py
```

2. Start the local MCP client:

```bash
cd local-mcp
npm start
```

3. To test the system, run the test script:

```bash
cd remote-agent
python test_agent.py
```

Or the browser automation test:

```bash
cd remote-agent
python test_browser.py
```

## API Endpoints

- `/connect/{client_id}`: SSE endpoint for local clients to connect to the remote agent
- `/result/{client_id}`: Endpoint for local clients to send command results back to the remote agent
- `/agent/{client_id}`: Endpoint for sending natural language requests to the LangGraph agent
- `/test/send_command/{client_id}`: Test endpoint for sending commands directly to connected clients

## How it Works

1. The local MCP client connects to the remote agent via SSE
2. A user sends a natural language request to the remote agent's `/agent` endpoint
3. The LangGraph workflow processes the request and generates a series of tool calls
4. The remote agent sends commands to the connected MCP client
5. The MCP client executes the commands and sends results back to the remote agent
6. The LangGraph workflow continues processing until the task is complete

## Architecture Diagram

```
User Request → Remote Agent (LangGraph) → FastAPI Server → Local MCP Client → Browser/Tools
                       ↑                                          |
                       |                                          |
                       └──────────── Result ───────────────────────
``` 