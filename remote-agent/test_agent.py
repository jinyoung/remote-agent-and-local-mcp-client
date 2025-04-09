import asyncio
import json
import requests
from typing import Dict, Any

async def test_agent(client_id: str, user_input: str) -> Dict[str, Any]:
    """Test the agent endpoint."""
    url = f"http://localhost:8000/agent/{client_id}"
    data = {"input": user_input}
    
    response = requests.post(url, json=data)
    return response.json()

async def main():
    """Main function to test the agent."""
    # Use a unique client ID for testing
    client_id = "test-client-1"
    
    # Test with a simple browser automation task
    user_input = "browser_navigate to https://www.example.com"
    
    print(f"Sending request for client {client_id} with input: {user_input}")
    response = await test_agent(client_id, user_input)
    print(f"Response: {json.dumps(response, indent=2)}")
    
    # Wait for some time to see the background task output
    print("Waiting for background task to complete...")
    await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main()) 