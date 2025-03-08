from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import logging
import json
import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load environment variables from .env file
load_dotenv()

# Enable logging but set to INFO to reduce noise
logging.basicConfig(level=logging.INFO)

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="python",  # Executable
    args=["src/server/example_server.py"],  # relative path to the server script
    env=None  # Optional environment variables
)

# Initialize OpenAI client with API key from environment variable
openai_client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# Define a local dummy prompt templates
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

# Store conversation history
conversation_history = [
    {"role": "system", "content": "You are a helpful assistant."}
]

async def run():
    print("\n===== MCP CLIENT WITH OPENAI INTEGRATION =====")
    print("This client connects to a local MCP server and OpenAI's API")
    
    async with stdio_client(server_params) as (read, write):
        print("\nConnected to server via stdio")
        
        # Create a sampling callback that uses OpenAI
        async def handle_openai_sampling(message: types.CreateMessageRequestParams) -> types.CreateMessageResult:
            try:
                # Get the user's message content
                user_content = ""
                if message.messages and len(message.messages) > 0:
                    last_message = message.messages[-1]
                    if hasattr(last_message, "content"):
                        for content_item in last_message.content:
                            if content_item.type == "text":
                                user_content += content_item.text
                
                if not user_content:
                    user_content = "Hello, please assist me."
                
                # Update conversation history
                conversation_history.append({"role": "user", "content": user_content})
                
                # Call OpenAI API with the full conversation history
                response = await openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=conversation_history
                )
                
                # Get the generated text from OpenAI
                ai_text = response.choices[0].message.content
                
                # Update conversation history with assistant's response
                conversation_history.append({"role": "assistant", "content": ai_text})
                
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
            
            # Reset conversation history with the new system prompt
            nonlocal conversation_history
            conversation_history = [
                {"role": "system", "content": prompt_text},
                {"role": "user", "content": "Please help me based on this information."}
            ]
            
            # Send the filled prompt to OpenAI
            response = await openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=conversation_history
            )
            
            # Update conversation history
            conversation_history.append({"role": "assistant", "content": response.choices[0].message.content})
            
            return response.choices[0].message.content
        
        async with ClientSession(read, write, sampling_callback=handle_openai_sampling) as session:
            # Initialize the connection
            await session.initialize()
            
            # List available tools
            print("Checking available tools...")
            tools = await session.list_tools()
            
            # Print tools information - Modified to handle potential attribute differences
            try:
                # Try with the name attribute - common alternative to id
                tool_names = [tool.name for tool in tools.tools]
                print(f"Found {len(tools.tools)} tools: {', '.join(tool_names)}\n")
            except AttributeError:
                # If name doesn't work, try to inspect the first tool to find available attributes
                if tools.tools:
                    print(f"Found {len(tools.tools)} tools. First tool attributes: {dir(tools.tools[0])}\n")
                else:
                    print("No tools found\n")
            
            # Main interactive loop
            print("===== INTERACTIVE MENU =====")
            while True:
                print("\nChoose an option:")
                print("1. Chat with AI assistant")
                print("2. Use weather assistant prompt")
                print("3. Use code helper prompt")
                print("4. Call BMI calculator tool")
                print("5. Call weather tool")
                print("6. Exit")
                
                choice = input("\nEnter option (1-6): ").strip()
                
                if choice == "1":
                    print("\n===== CHAT MODE =====")
                    print("Type 'exit' to return to menu")
                    
                    # Reset conversation history
                    conversation_history = [
                        {"role": "system", "content": "You are a helpful assistant."}
                    ]
                    
                    while True:
                        user_input = input("\nYou: ").strip()
                        if user_input.lower() == 'exit':
                            break
                            
                        # Update conversation history
                        conversation_history.append({"role": "user", "content": user_input})
                        
                        # Call OpenAI directly for better conversation flow
                        response = await openai_client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=conversation_history
                        )
                        
                        assistant_response = response.choices[0].message.content
                        print(f"\nAssistant: {assistant_response}")
                        
                        # Update conversation history
                        conversation_history.append({"role": "assistant", "content": assistant_response})
                
                elif choice == "2":
                    print("\n===== WEATHER ASSISTANT =====")
                    location = input("Enter location (e.g., New York): ").strip()
                    try:
                        temperature = float(input("Enter temperature in °C: ").strip())
                        conditions = input("Enter weather conditions (e.g., sunny, rainy): ").strip()
                        
                        weather_args = {
                            "location": location,
                            "temperature": temperature,
                            "conditions": conditions
                        }
                        
                        print("\nGenerating weather report...")
                        weather_response = await process_local_prompt("weather-assistant", weather_args)
                        print(f"\nWeather Assistant: {weather_response}")
                    except ValueError:
                        print("Error: Please enter a valid number for temperature")
                
                elif choice == "3":
                    print("\n===== CODE HELPER =====")
                    language = input("Enter programming language: ").strip()
                    problem = input("Describe your coding problem: ").strip()
                    
                    code_args = {
                        "language": language,
                        "problem": problem
                    }
                    
                    print("\nGenerating coding help...")
                    code_response = await process_local_prompt("code-helper", code_args)
                    print(f"\nCode Assistant: {code_response}")
                
                elif choice == "4":
                    print("\n===== BMI CALCULATOR =====")
                    try:
                        weight = float(input("Enter weight in kg: ").strip())
                        height = float(input("Enter height in meters: ").strip())
                        
                        print("\nCalculating BMI...")
                        # Check what attribute to use for tool identification (modify as needed)
                        tool_name = "calculate_bmi"  # This may need to be adjusted based on the actual tool structure
                        result = await session.call_tool(tool_name, arguments={"weight_kg": weight, "height_m": height})
                        print(f"Your BMI is: {result}")
                    except ValueError:
                        print("Error: Please enter valid numbers for weight and height")
                    except Exception as e:
                        print(f"Error calling BMI calculator: {e}")
                
                elif choice == "5":
                    print("\n===== WEATHER TOOL =====")
                    try:
                        latitude = float(input("Enter latitude: ").strip())
                        longitude = float(input("Enter longitude: ").strip())
                        
                        print("\nFetching weather data...")
                        try:
                            # Check what attribute to use for tool identification (modify as needed)
                            tool_name = "fetch_weather"  # This may need to be adjusted based on the actual tool structure
                            weather = await session.call_tool(tool_name, arguments={"latitude": latitude, "longitude": longitude})
                            print(f"Weather data: {json.dumps(weather, indent=2)}")
                        except Exception as e:
                            print(f"Error calling weather tool: {e}")
                            print("Note: This tool may not be available in the example server")
                    except ValueError:
                        print("Error: Please enter valid numbers for latitude and longitude")
                
                elif choice == "6":
                    print("\nExiting program...")
                    break
                
                else:
                    print("Invalid option. Please enter a number between 1 and 6.")

if __name__ == "__main__":
    asyncio.run(run())
