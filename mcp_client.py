import requests


MCP_URL="http://localhost:9000/mcp"



def list_tools():


    r=requests.post(
        MCP_URL,
        json={
            "method":"tools/list"
        }
    )


    return r.json()["tools"]




def call_tool(name,args):


    r=requests.post(
        MCP_URL,
        json={
            "method":"tools/call",
            "params":{
                "name":name,
                "arguments":args
            }
        }
    )


    return r.json()["result"]