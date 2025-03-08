from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import logging
from openai import AsyncOpenAI
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Enable logging
logging.basicConfig(level=logging.DEBUG)

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="python",  # Executable
    args=["src/server/example_server.py"],  # relative path to the server script
    env=None  # Optional environment variables
)

# Initialize OpenAI client with API key from environment variable
openai_client = AsyncOpenAI(
    # If OPENAI_API_KEY is set as an environment variable, it will be used automatically
    # Otherwise, you can specify a different env variable name
    api_key=os.getenv("OPENAI_API_KEY")
)

# Define a local dummy prompt - this simulates what would normally come from the server
DUMMY_PROMPTS = {
    "weather-assistant": {
        "template": "You are a weather assistant. The current weather in {location} is {temperature}°C with {conditions}. Please provide a friendly weather report and clothing recommendation.",
        "required_args": ["location", "temperature", "conditions"]
    },
    "code-helper": {
        "template": "You are a coding assistant. Please help the user with their {language} code problem: {problem}",
        "required_args": ["language", "problem"]
    }
}

async def run():
    print("Starting client...")
    async with stdio_client(server_params) as (read, write):
        print("Connected to server via stdio")
        
        # Create a sampling callback that uses OpenAI
        async def handle_openai_sampling(message: types.CreateMessageRequestParams) -> types.CreateMessageResult:
            try:
                # Get the user's message content - fixed extraction method
                user_content = ""
                if message.messages and len(message.messages) > 0:
                    last_message = message.messages[-1]
                    if hasattr(last_message, "content"):
                        # Handle different content types
                        for content_item in last_message.content:
                            if content_item.type == "text":
                                user_content += content_item.text
                
                # Fall back to a default message if we couldn't extract content
                if not user_content:
                    user_content = "Hello, please assist me."
                
                print(f"Sending to OpenAI: {user_content}")
                
                # Call OpenAI API
                response = await openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": user_content}
                    ]
                )
                
                # Get the generated text from OpenAI
                ai_text = response.choices[0].message.content
                
                return types.CreateMessageResult(
                    role="assistant",
                    content=types.TextContent(
                        type="text",
                        text=ai_text,
                    ),
                    model="gpt-3.5-turbo",
                    stopReason="endTurn",
                )
            except Exception as e:
                print(f"Error in OpenAI sampling: {e}")
                return types.CreateMessageResult(
                    role="assistant",
                    content=types.TextContent(
                        type="text",
                        text=f"I encountered an error: {str(e)}",
                    ),
                    model="gpt-3.5-turbo",
                    stopReason="error",
                )
        
        # Add a custom method to handle local prompts
        async def process_local_prompt(prompt_id, args):
            if prompt_id not in DUMMY_PROMPTS:
                raise Exception(f"Unknown prompt: {prompt_id}")
            
            prompt_info = DUMMY_PROMPTS[prompt_id]
            
            # Check if all required arguments are provided
            for arg in prompt_info["required_args"]:
                if arg not in args:
                    raise Exception(f"Missing required argument: {arg}")
            
            # Fill in the template with the provided arguments
            prompt_text = prompt_info["template"]
            for arg_name, arg_value in args.items():
                prompt_text = prompt_text.replace(f"{{{arg_name}}}", str(arg_value))
            
            print(f"Processed prompt template: {prompt_text}")
            
            # Send the filled prompt to OpenAI
            response = await openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": prompt_text},
                    {"role": "user", "content": "Please help me based on this information."}
                ]
            )
            
            return response.choices[0].message.content
        
        async with ClientSession(read, write, sampling_callback=handle_openai_sampling) as session:
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
            
            # List available prompts from server
            print("Listing server prompts...")
            prompts = await session.list_prompts()
            print("Available server prompts:", prompts)
            
            # Demo local prompts instead of relying on server prompts
            print("\n--- DEMONSTRATING LOCAL PROMPT HANDLING ---")
            print("Available local prompts:", json.dumps(list(DUMMY_PROMPTS.keys()), indent=2))
            
            try:
                # Process a weather assistant prompt locally
                print("\nProcessing weather-assistant prompt locally...")
                weather_args = {
                    "location": "New York",
                    "temperature": 22,
                    "conditions": "partly cloudy"
                }
                weather_response = await process_local_prompt("weather-assistant", weather_args)
                print(f"Weather assistant response:\n{weather_response}\n")
                
                # Process a code helper prompt locally
                print("Processing code-helper prompt locally...")
                code_args = {
                    "language": "Python",
                    "problem": "How do I read a JSON file in Python?"
                }
                code_response = await process_local_prompt("code-helper", code_args)
                print(f"Code helper response:\n{code_response}\n")
                
                # Try to get a prompt from server (this might fail)
                print("Attempting to get prompt from server (may fail if not supported)...")
                try:
                    prompt = await session.get_prompt("example-prompt", arguments={"arg1": "value"})
                    print("Server prompt result:", prompt)
                except Exception as e:
                    print(f"Server doesn't support this prompt: {e}")
                    print("This is expected with the example server")
                
            except Exception as e:
                print(f"Error processing local prompts: {e}")
            
            # List available resources
            print("\nListing resources...")
            resources = await session.list_resources()
            print("Available resources:", resources)
            
            # Since reading a resource will likely fail, we'll just log this
            print("\nNote: Reading resource 'file://some/path' would normally fail")
            print("with the example server as it doesn't have resource capabilities.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
