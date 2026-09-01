from fastapi import FastAPI
from mcp_core import MCPServer
from tools import registry


app = FastAPI()


mcp = MCPServer(registry)



@app.post("/mcp")
def handle_mcp(request:dict):


    method=request.get("method")


    if method=="tools/list":


        return {
            "tools":mcp.list_tools()
        }



    elif method=="tools/call":


        params=request["params"]

        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            return {
                "error": {
                    "type": "invalid_request",
                    "message": "missing tool name"
                }
            }

        if not mcp.registry.has_tool(tool_name):
            return {
                "error": {
                    "type": "tool_not_found",
                    "message": f"Tool不存在:{tool_name}"
                }
            }

        try:
            result=mcp.call_tool(tool_name, arguments)
        except Exception as exc:
            return {
                "error": {
                    "type": "tool_execution_failed",
                    "message": str(exc)
                }
            }


        return {
            "result":result
        }



    else:

        return {
            "error":"unknown method"
        }
