import json

from agent import run_agent
from mcp_core import MCPServer
from tool_core import Tool
from tool_registry import ToolRegistry


def test_tool_registry_and_schema():
    tool = Tool("echo", "Echo", lambda value: value, {"value": {"type": "string"}}, ["value"])
    registry = ToolRegistry()
    registry.register(tool)
    assert registry.get("echo") is tool
    assert registry.list_tools()[0]["required"] == ["value"]
    assert registry.call("echo", {"value": "ok"}) == "ok"


def test_mcp_list_and_call():
    registry = ToolRegistry()
    registry.register(Tool("echo", "Echo", lambda value: value, {"value": {"type": "string"}}, ["value"]))
    server = MCPServer(registry)
    assert server.list_tools()[0]["name"] == "echo"
    assert server.call_tool("echo", {"value": "ok"}) == "ok"


class FakeMCP:
    def list_tools(self):
        return [{"name": "echo", "description": "Echo", "parameters": {"value": {"type": "string"}}, "required": ["value"]}]

    def call_tool(self, name, args):
        return {"success": True, "data": args["value"], "error": None}


def test_agent_tool_then_final():
    responses = iter(['{"action":"echo","args":{"value":"hello"}}', '{"action":"final","answer":"done"}'])
    assert run_agent("say", llm=lambda _: next(responses), client=FakeMCP()) == "done"


def test_agent_direct_final():
    assert run_agent("hi", llm=lambda _: '{"action":"final","answer":"ok"}', client=FakeMCP()) == "ok"


def test_invalid_json_and_max_steps():
    assert "非法 JSON" in run_agent("x", llm=lambda _: "not json", client=FakeMCP(), max_json_retries=1)
    assert "最大步骤数" in run_agent("x", llm=lambda _: '{"action":"echo","args":{"value":"x"}}', client=FakeMCP(), max_steps=1)


def test_invalid_action_shape_is_bounded():
    result = run_agent("x", llm=lambda _: '{"foo":1}', client=FakeMCP(), max_json_retries=1)
    assert "非法 action" in result


def test_agent_invalid_tool_reaches_limit():
    assert "最大步骤数" in run_agent("x", llm=lambda _: '{"action":"missing","args":{}}', client=FakeMCP(), max_steps=2)
