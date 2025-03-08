# MCP Client Example ☀️ 

This project demonstrates a simple client-server implementation using the Model Context Protocol (MCP), which is a standardized way to connect large language models with tools and data.

## Overview

This example shows how to:
- Create an MCP server with custom tools
- Connect to the server using an MCP client
- Call tools and get responses from the server

## Tutorial Video

[![MCP Tutorial Video](https://img.youtube.com/vi/oq3dkNm51qc/0.jpg)](https://youtu.be/oq3dkNm51qc)

Click the image above to watch a tutorial on MCP implementation.

## Project Structure

```
.
├── pyproject.toml
├── README.md
├── src
│   ├── client
│   │   └── mcp_client.py      # MCP client implementation
│   └── server
│       └── example_server.py  # MCP server with tools
└── uv.lock
```

## Server Implementation

The server exposes two tools:
1. `calculate_bmi` - A simple calculator that computes Body Mass Index
2. `fetch_weather` - An async tool that retrieves weather data from an external API

## Client Implementation

The client connects to the server via stdio, initializes a session, and calls the server's tools.

## Getting Started

### Prerequisites

- Python 3.9+
- uv (Python package manager)

### Installation

```bash
# Install dependencies
uv install -e .
```

### Running the Example

1. Start the client (which will automatically start the server):

```bash
uv run src/client/mcp_client.py
```

## Usage

The client will:
1. Connect to the server
2. List available tools
3. Call the BMI calculator with sample data
4. Call the weather tool with sample coordinates

## Example Response

```
Available tools: meta=None nextCursor=None tools=[...]
BMI calculation result: 22.857142857142858
Weather data: {"current_weather":{"temperature":14.2,"windspeed":12.6, ...}}
```
## Test with MCP Inspector 
( run command below and then visit http://localhost:5173 )

```
  ❯ mcp dev src/server/example_server.py
Starting MCP inspector...
Proxy server listening on port 3000

🔍 MCP Inspector is up and running at http://localhost:5173 🚀
New SSE connection
Query parameters: {
  transportType: 'stdio',
  command: 'uv',
  args: 'run --with mcp mcp run src/server/example_server.py',
```

## Resources

This project uses:
- [Model Context Protocol Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Official Documentation](https://modelcontextprotocol.io)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
