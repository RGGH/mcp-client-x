from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import logging

# Enable logging
logging.basicConfig(level=logging.DEBUG)

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="python", # Executable
    args=["src/server/example_server.py"], # relative path to the server script
    env=None # Optional environment variables
)

async def run():
    print("Starting client...")
    async with stdio_client(server_params) as (read, write):
        print("Connected to server via stdio")
        async with ClientSession(read, write) as session:
            # Initialize the connection
            print("Initializing session...")
            await session.initialize()
            
            # List available tools
            print("Listing tools...")
            tools = await session.list_tools()
            print("Available tools:", tools)
            
            try:
                # Try calling the BMI calculator tool
                print("Calling calculate_bmi...")
                result = await session.call_tool("calculate_bmi", arguments={"weight_kg": 70, "height_m": 1.75})
                print("BMI calculation result:", result)
            except Exception as e:
                print(f"Error calling calculate_bmi: {e}")
            
            try:
                # Try calling the weather tool
                print("Calling fetch_weather...")
                weather = await session.call_tool("fetch_weather", arguments={"latitude": 52.07, "longitude": -1.014})
                print("Weather data:", weather)
            except Exception as e:
                print(f"Error calling fetch_weather: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
