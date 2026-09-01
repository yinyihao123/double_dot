import requests
from requests import RequestException
from config import MCP_TIMEOUT, MCP_URL

class MCPClientError(Exception):
    pass

class MCPClient:
    def __init__(self, url=MCP_URL, timeout=MCP_TIMEOUT):
        self.url, self.timeout = url, timeout
        self.session = requests.Session()
        self.session.trust_env = False

    def _post(self, payload):
        try:
            response = self.session.post(self.url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            body = response.json()
        except (RequestException, ValueError) as exc:
            raise MCPClientError(f"MCP request failed: {exc}") from exc
        if not isinstance(body, dict):
            raise MCPClientError("MCP response must be an object")
        if "error" in body:
            raise MCPClientError(str(body["error"]))
        return body

    def list_tools(self):
        body = self._post({"method": "tools/list"})
        if not isinstance(body.get("tools"), list):
            raise MCPClientError("MCP tools/list response missing tools")
        return body["tools"]

    def call_tool(self, name, args):
        body = self._post({"method": "tools/call", "params": {"name": name, "arguments": args}})
        if "result" not in body:
            raise MCPClientError("MCP tools/call response missing result")
        return body["result"]

_default_client = MCPClient()
list_tools = _default_client.list_tools
call_tool = _default_client.call_tool
