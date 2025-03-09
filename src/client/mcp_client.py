from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import logging
import json
import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
logging.basicConfig(level=logging.INFO)

server_params = StdioServerParameters(
    command="python",
    args=["src/server/example_server.py"],
)

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


LOCAL_FUNCTIONS = {
    "calculate_bmi": {
        "keywords": ["bmi", "body mass index"],
        "tool_name": "calculate_bmi",
        "prompts": ["Enter weight in kg: ", "Enter height in meters: "],
        "format_args": lambda w, h: {"weight_kg": float(w), "height_m": float(h)},
        "response_format": lambda res: f"Your BMI is: {res}",
    },
    "get_weather": {
        "keywords": ["weather", "forecast"],
        "tool_name": "fetch_weather",
        "prompts": ["Enter latitude: ", "Enter longitude: "],
        "format_args": lambda lat, lon: {"latitude": float(lat), "longitude": float(lon)},
        "response_format": lambda res: (
            f"{json.loads(res).get('current_weather', {}).get('temperature', 'N/A')}°C"
            if res and isinstance(res, str) and res.strip() else "Error: No response from API"
        ),
    },
}


logging.getLogger().setLevel(logging.INFO)  # This ensures no debug level logs are shown

conversation_history = [{"role": "system", "content": "You are a helpful assistant."}]

async def handle_openai_sampling(message: types.CreateMessageRequestParams) -> types.CreateMessageResult:
    try:
        user_content = next((c.text for m in message.messages for c in getattr(m, "content", []) if c.type == "text"), "Hello, please assist me.")
        conversation_history.append({"role": "user", "content": user_content})

        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo", messages=conversation_history
        )

        ai_text = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": ai_text})
        
        return types.CreateMessageResult(role="assistant", content=types.TextContent(type="text", text=ai_text), model="gpt-3.5-turbo", stopReason="endTurn")
    except Exception as e:
        logging.error(f"OpenAI API error: {e}")
        return types.CreateMessageResult(role="assistant", content=types.TextContent(type="text", text=f"Error: {e}"), model="gpt-3.5-turbo", stopReason="error")

async def detect_and_handle_local_function(user_input, session):
    user_input_lower = user_input.lower()
    for func_name, func_info in LOCAL_FUNCTIONS.items():
        if any(keyword in user_input_lower for keyword in func_info["keywords"]):
            print(f"\n[USING LOCAL FUNCTION: {func_name}]")
            try:
                args = func_info["format_args"](*[input(p) for p in func_info["prompts"]])
                tool_result = await session.call_tool(func_info["tool_name"], arguments=args)
                
                # For weather function
                if func_name == "get_weather":
                    # Extract the content text from the tool_result (based on the debug output)
                    content_list = tool_result.content
                    if content_list and len(content_list) > 0:
                        text_content = content_list[0].text
                        
                        # Parse the JSON and extract just the temperature
                        try:
                            weather_data = json.loads(text_content)
                            temperature = weather_data.get('current_weather', {}).get('temperature', 'N/A')
                            
                            # Print ONLY the temperature value
                            print(f"\n{temperature}°C")
                            
                            # Add to conversation history
                            conversation_history.extend([
                                {"role": "user", "content": user_input}, 
                                {"role": "assistant", "content": f"{temperature}°C"}
                            ])
                        except json.JSONDecodeError:
                            print("\nError: Invalid JSON received.")
                            logging.error(f"Invalid JSON received: {text_content}")
                    else:
                        print("\nError: No content in response.")
                else:
                    # For non-weather functions like BMI
                    content_list = tool_result.content
                    if content_list and len(content_list) > 0:
                        result = content_list[0].text
                        formatted_response = func_info["response_format"](result)
                        print(f"\nAssistant: {formatted_response}")
                        
                        # Add to conversation history
                        conversation_history.extend([
                            {"role": "user", "content": user_input}, 
                            {"role": "assistant", "content": formatted_response}
                        ])
                    else:
                        print("\nError: No content in response.")
                        
                return True
            except Exception as e:
                logging.error(f"Error calling {func_name}: {e}")
                print(f"\nAssistant: Error processing request.")
                return True
    return False

async def run():
    print("\n===== MCP CLIENT =====\n")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write, sampling_callback=handle_openai_sampling) as session:
            await session.initialize()
            print(f"Available tools: {[tool.name for tool in (await session.list_tools()).tools]}")
            
            while True:
                user_input = input("\nYou: ").strip()
                if user_input.lower() == "exit":
                    print("Exiting...")
                    break
                if not await detect_and_handle_local_function(user_input, session):
                    print("\n[USING OpenAI]")
                    conversation_history.append({"role": "user", "content": user_input})
                    response = await openai_client.chat.completions.create(
                        model="gpt-3.5-turbo", messages=conversation_history
                    )
                    assistant_response = response.choices[0].message.content
                    print(f"\nAssistant: {assistant_response}")
                    conversation_history.append({"role": "assistant", "content": assistant_response})

if __name__ == "__main__":
    asyncio.run(run())
