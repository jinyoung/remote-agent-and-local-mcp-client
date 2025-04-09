import { MultiServerMCPClient } from "@langchain/mcp-adapters";
import EventSource from "eventsource";
import fetch from "node-fetch";

const CLOUD_HOST = "http://127.0.0.1:8000";
const CLIENT_ID = "test-client-1";

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
        const tools = await client.getTools();
        console.log("Available tools:", tools.map(t => t.name));

        // Connect to cloud agent via SSE
        const eventSource = new EventSource(`${CLOUD_HOST}/connect/${CLIENT_ID}`, {
            headers: {
                'Accept': 'text/event-stream'
            }
        });

        console.log(`Connecting to ${CLOUD_HOST}/connect/${CLIENT_ID}`);

        eventSource.onopen = () => {
            console.log("SSE connection established successfully");
        };

        eventSource.addEventListener("command", async (event) => {
            try {
                const data = JSON.parse(event.data) as CommandData;
                console.log("Command event received:", data);

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

        // 하트비트 이벤트도 처리
        eventSource.addEventListener("heartbeat", (event) => {
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

main().catch(console.error); 