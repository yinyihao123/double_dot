# Mobius Agent

> A lightweight Agent framework based on MCP architecture.

Mobius is an experimental Agent system that enables LLMs to interact with external tools through MCP (Model Context Protocol).

The core idea:

```
User
 |
 v
Agent
 |
 v
MCP Client
 |
 HTTP
 |
 v
MCP Server
 |
 v
Tools
```

The Agent is responsible for:

- Understanding user intent
- Selecting appropriate tools
- Calling tools through MCP
- Processing tool results
- Generating final answers


# Architecture

```
                 +-------------+
                 |    User     |
                 +------+------+
                        |
                        v
              +----------------+
              |  FastAPI API   |
              |   main.py      |
              +----------------+
                        |
                        v
              +----------------+
              |     Agent      |
              |   agent.py     |
              +----------------+
                        |
                        v
              +----------------+
              |  MCP Client    |
              |mcp_client.py   |
              +----------------+
                        |
                    HTTP Request
                        |
                        v
              +----------------+
              |  MCP Server    |
              |  mcp_api.py    |
              +----------------+
                        |
                        v
              +----------------+
              |     Tools      |
              |    tools.py    |
              +----------------+
```


# Project Structure

```
Mobius/

├── agent.py              # Agent reasoning loop
├── main.py               # Agent API service
├── llm.py                # LLM interface
├── config.py             # Configuration
│
├── mcp_api.py            # MCP HTTP server
├── mcp_client.py         # MCP client
├── mcp_core.py           # MCP core logic
│
├── tools.py              # Tool definitions
├── tool_registry.py      # Tool registry
├── tool_result.py        # Tool execution result
│
├── requirements.txt      # Python dependencies
│
├── workspace/            # Agent workspace
│
└── README.md
```


# Environment Setup


## Create virtual environment

```bash
python3 -m venv venv
```


## Activate environment

```bash
source venv/bin/activate
```


## Install dependencies

```bash
pip install -r requirements.txt
```


# Run Mobius


Mobius contains two services:

1. MCP Server
2. Agent Server


## Start MCP Server

Open terminal 1:

```bash
cd ~/workspace/my-agent/Mobius

source venv/bin/activate

uvicorn mcp_api:app \
--host 0.0.0.0 \
--port 9000
```


MCP Server:

```
http://localhost:9000
```


## Start Agent Server

Open terminal 2:

```bash
cd ~/workspace/my-agent/Mobius

source venv/bin/activate

uvicorn main:app \
--host 0.0.0.0 \
--port 8080
```


Agent Server:

```
http://localhost:8080
```


# Test


Example:

```
http://localhost:8080/chat?question=现在几点
```


Execution flow:

```
User Question

      |
      v

Agent analyzes request

      |
      v

LLM generates tool action

      |
      v

MCP Client calls MCP Server

      |
      v

Tool execution

      |
      v

Result returned to Agent

      |
      v

Final Answer
```


# Current Features


## Agent

- LLM based reasoning loop
- Tool selection
- JSON action protocol
- Tool result feedback


## MCP

- Tool discovery
- Tool calling
- HTTP based communication


## Tools

Current tools:

- get_time
- search_file


# Development Roadmap


## Phase 1: Core Agent

- [x] Agent loop
- [x] MCP communication
- [x] Tool calling
- [ ] Better error handling


## Phase 2: Tool System

- [ ] Automatic tool registration
- [ ] Tool schema standardization
- [ ] Tool permission control
- [ ] Multiple MCP servers


## Phase 3: Agent Capability

- [ ] Memory
- [ ] Planning
- [ ] Task decomposition
- [ ] Reflection


## Phase 4: Production

- [ ] Docker deployment
- [ ] Authentication
- [ ] Logging
- [ ] Monitoring


# Design Philosophy


Mobius follows a simple principle:


> LLM should not directly execute actions.  
> LLM should reason and select tools.  
> Tools execute deterministic operations.


The Agent provides intelligence.

MCP provides capability.

Tools provide execution.


# License

MIT