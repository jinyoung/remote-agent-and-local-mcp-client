import { MultiServerMCPClient } from "@langchain/mcp-adapters";
import cors from "cors";
import EventSource from "eventsource";
import express from "express";
import fetch from "node-fetch";

const CLOUD_HOST = "http://127.0.0.1:8000";
const CLIENT_ID = "test-client-1";
const API_PORT = 3000;

interface CommandEvent {
    data: string;
    type: string;
    lastEventId: string;
}

interface CommandData {
    id: string;
    tool: string;
    params: Record<string, unknown>;
}

// Schema interfaces for tool parameters
interface ParameterProperty {
    type?: string;
    description?: string;
    [key: string]: any;
}

interface ToolSchema {
    properties?: Record<string, ParameterProperty>;
    [key: string]: any;
}

interface Tool {
    name: string;
    description?: string;
    schema?: ToolSchema;
    invoke: (params: any) => Promise<any>;
    [key: string]: any;
}

async function main() {
    // Initialize MCP client with local tools
    const client = new MultiServerMCPClient({
        playwright: {
            transport: "stdio",
            command: "npx",
            args: ["@playwright/mcp@latest"]
        }
    });

    try {
        // Initialize tools
        const tools = await client.getTools() as Tool[];
        console.log("Available tools:", tools.map(t => t.name));

        // Start HTTP server to expose tool definitions (keep for local development)
        const app = express();
        app.use(cors());
        app.use(express.json());

        // Endpoint to get tool definitions
        app.get('/tools', (req, res) => {
            const toolDefinitions = generateToolDefinitions(tools);
            res.json(toolDefinitions);
        });

        // Start the HTTP server
        app.listen(API_PORT, () => {
            console.log(`Tool definition API listening at http://localhost:${API_PORT}`);
        });

        // Connect to cloud agent via SSE
        const eventSource = new EventSource(`${CLOUD_HOST}/connect/${CLIENT_ID}`, {
            headers: {
                'Accept': 'text/event-stream'
            }
        });

        console.log(`Connecting to ${CLOUD_HOST}/connect/${CLIENT_ID}`);

        eventSource.onopen = async () => {
            console.log("SSE connection established successfully");
            
            // Send tool definitions to remote-agent on connection
            const toolDefinitions = generateToolDefinitions(tools);
            try {
                const response = await fetch(`${CLOUD_HOST}/register_tools/${CLIENT_ID}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        tools: toolDefinitions
                    }),
                });
                
                if (response.ok) {
                    console.log("Tool definitions sent to remote-agent:", await response.json());
                } else {
                    console.error("Failed to send tool definitions:", response.status, await response.text());
                }
            } catch (error) {
                console.error("Error sending tool definitions:", error);
            }
        };

        // 명시적으로 'command' 이벤트를 리스닝합니다
        (eventSource as any).addEventListener("command", async (event: MessageEvent) => {
            try {
                console.log("Command event received with data:", event.data);
                const data = JSON.parse(event.data) as CommandData;
                console.log("Command event parsed:", data);

                // Execute the command using appropriate tool
                const exactTool = tools.find(t => t.name === data.tool);
                const partialMatchTool = exactTool || tools.find(t => 
                    t.name.includes('playwright') && 
                    (t.name.includes('navigate') || t.name.includes('browser'))
                );
                const tool = exactTool || partialMatchTool;

                if (tool) {
                    console.log(`Found tool: ${tool.name}, executing with params:`, data.params);
                    const result = await tool.invoke(data.params);
                    console.log(`Tool execution result:`, result);
                    
                    // Send result back to cloud agent
                    const response = await fetch(`${CLOUD_HOST}/result/${CLIENT_ID}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            commandId: data.id,
                            result: result
                        }),
                    });
                    console.log("Result sent:", await response.json());
                } else {
                    console.error(`Tool ${data.tool} not found. Available tools:`, tools.map(t => t.name));
                }
            } catch (error) {
                console.error("Error processing command event:", error);
            }
        });

        // 일반적인 메시지 처리 (이벤트 타입이 없는 경우)
        eventSource.onmessage = (event: MessageEvent) => {
            console.log("Generic message received:", event.data);
        };

        // 하트비트 이벤트 처리
        (eventSource as any).addEventListener("heartbeat", (event: MessageEvent) => {
            console.log("Heartbeat received:", event.data);
        });

        eventSource.onerror = (error: Event) => {
            console.error("SSE connection error:", error);
            // Implement reconnection logic if needed
            setTimeout(() => {
                console.log("Attempting to reconnect...");
                eventSource.close();
                main();
            }, 5000);
        };

        // Keep the process running
        await new Promise(() => {});
    } catch (error) {
        console.error("Error in main:", error);
        process.exit(1);
    }
}

// Helper function to generate tool definitions
function generateToolDefinitions(tools: Tool[]) {
    return tools.map(tool => {
        // Extract parameter schema from each tool
        const parameters: Record<string, any> = {};
        
        // Handle different schema formats from MCP tools
        if (tool.schema && tool.schema.properties) {
            // Handle standard schema format
            Object.entries(tool.schema.properties).forEach(([key, prop]) => {
                parameters[key] = {
                    type: prop.type || "string",
                    description: prop.description || `Parameter ${key}`
                };
            });
        } else if (tool.schema && typeof tool.schema === 'object') {
            // Try to extract from Zod schema format
            try {
                // Try to access Zod schema internal structure
                const zodShape = (tool.schema as any)._def?.shape;
                if (zodShape) {
                    Object.keys(zodShape).forEach(key => {
                        parameters[key] = {
                            type: "string", // Default to string if type is unknown
                            description: `Parameter ${key}`
                        };
                    });
                }
                
                // Or try getting JSON schema
                const jsonSchema = (tool.schema as any).jsonSchema?.();
                if (jsonSchema?.properties) {
                    Object.entries(jsonSchema.properties).forEach(([key, prop]: [string, any]) => {
                        parameters[key] = {
                            type: prop.type || "string",
                            description: prop.description || `Parameter ${key}`
                        };
                    });
                }
            } catch (error) {
                console.warn(`Could not extract schema for tool ${tool.name}:`, error);
            }
        }
        
        // Add default parameters based on tool name if none were found
        if (Object.keys(parameters).length === 0) {
            console.log(`No parameters found for tool ${tool.name}, adding defaults based on name`);
            
            // Default parameters for navigation tools
            if (tool.name.includes('navigate')) {
                parameters['url'] = {
                    type: "string",
                    description: "The URL to navigate to"
                };
            } 
            // Default parameters for click tools
            else if (tool.name.includes('click')) {
                parameters['selector'] = {
                    type: "string",
                    description: "The selector to click on"
                };
            }
            // Default parameters for type tools
            else if (tool.name.includes('type')) {
                parameters['selector'] = {
                    type: "string",
                    description: "The selector to type into"
                };
                parameters['text'] = {
                    type: "string",
                    description: "The text to type"
                };
            }
            // Add a generic parameter for other tools
            else if (!tool.name.includes('install') && !tool.name.includes('close')) {
                parameters['input'] = {
                    type: "string",
                    description: `Input for ${tool.name}`
                };
            }
        }
        
        // Log the parameters for debugging
        console.log(`Tool ${tool.name} parameters:`, parameters);
        
        return {
            name: tool.name,
            display_name: tool.name.split('__').pop() || tool.name,
            description: tool.description || `Tool ${tool.name}`,
            parameters
        };
    });
}

main().catch(console.error); 