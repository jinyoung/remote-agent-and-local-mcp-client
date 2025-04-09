import asyncio
import json
import requests
from typing import Dict, Any

async def test_browser(client_id: str) -> Dict[str, Any]:
    """Test the browser automation with LangGraph agent."""
    url = f"http://localhost:8000/agent/{client_id}"
    
    # A complex task that demonstrates browser automation
    user_input = """
    Follow these steps:
    1. Open a browser
    2. Navigate to https://www.example.com
    3. Take a screenshot
    4. Wait 2 seconds
    5. Navigate to https://openai.com
    6. Take another screenshot
    """
    
    data = {"input": user_input}
    response = requests.post(url, json=data)
    return response.json()

async def main():
    """Main function to test browser automation."""
    # Use a unique client ID for testing
    client_id = "test-client-1"
    
    print(f"Testing browser automation for client {client_id}")
    response = await test_browser(client_id)
    print(f"Response: {json.dumps(response, indent=2)}")
    
    # Wait for the agent to process the request
    print("Waiting for the agent to complete the browser automation task...")
    await asyncio.sleep(60)  # Wait longer for the complex task

if __name__ == "__main__":
    asyncio.run(main()) 