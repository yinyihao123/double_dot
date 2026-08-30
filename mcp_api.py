from fastapi import FastAPI
from mcp_core import MCPServer


app = FastAPI()


mcp = MCPServer()



@app.post("/mcp")
def handle_mcp(request:dict):


    method=request.get("method")


    if method=="tools/list":


        return {
            "tools":mcp.list_tools()
        }



    elif method=="tools/call":


        params=request["params"]


        result=mcp.call_tool(
            params["name"],
            params.get("arguments",{})
        )


        return {
            "result":result
        }



    else:

        return {
            "error":"unknown method"
        }