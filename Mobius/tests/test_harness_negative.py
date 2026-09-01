from harness.models import AgentCase
from harness.runner import HarnessRunner


class FakeMCP:
    def __init__(self, tools, results=None):
        self.tools = tools
        self.results = results or {}
        self.calls = []

    def list_tools(self):
        return self.tools

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return self.results.get(name, "ok")


def execute(case, responses, client):
    return HarnessRunner(lambda _: responses.pop(0), client).run_case(case)


def test_negative_wrong_tool_is_caught():
    tools = [{"name": "get_time", "parameters": {}, "required": []}, {"name": "get_cpu_usage", "parameters": {}, "required": []}]
    result = execute(AgentCase("get_time", "time", ["get_time"]), [
        '{"action":"get_cpu_usage","args":{}}', '{"action":"final","answer":"x"}'
    ], FakeMCP(tools))
    assert not result.passed
    assert "expected tools ['get_time'], got ['get_cpu_usage']" in result.failures


def test_negative_wrong_arguments_are_caught():
    tools = [{"name": "search_file", "parameters": {"keyword": {"type": "string"}}, "required": ["keyword"]}]
    result = execute(AgentCase("search", "find", ["search_file"], {"search_file": {"keyword": "error"}}, expected_final="done"), [
        '{"action":"search_file","args":{"keyword":"warning"}}', '{"action":"final","answer":"done"}'
    ], FakeMCP(tools))
    assert not result.passed and "arguments mismatch for search_file" in result.failures


def test_negative_wrong_order_is_caught():
    tools = [{"name": "get_time", "parameters": {}, "required": []}, {"name": "get_cpu_usage", "parameters": {}, "required": []}]
    result = execute(AgentCase("multi", "both", ["get_time", "get_cpu_usage"]), [
        '{"action":"get_cpu_usage","args":{}}', '{"action":"get_time","args":{}}', '{"action":"final","answer":"ok"}'
    ], FakeMCP(tools))
    assert not result.passed and "expected tools ['get_time', 'get_cpu_usage']" in result.failures[0]


def test_negative_illegal_tool_is_caught():
    result = execute(AgentCase("illegal", "bad", []), [
        '{"action":"does_not_exist","args":{}}', '{"action":"final","answer":"not executed"}'
    ], FakeMCP([]))
    assert not result.passed
    assert "unexpected action/tool: does_not_exist" in result.failures


def test_negative_unused_tool_result_is_caught():
    tools = [{"name": "get_time", "parameters": {}, "required": []}]
    result = execute(AgentCase("unused", "time", ["get_time"], expected_final_contains=["2026-01-01 12:00:00"]), [
        '{"action":"get_time","args":{}}', '{"action":"final","answer":"I do not know."}'
    ], FakeMCP(tools, {"get_time": "2026-01-01 12:00:00"}))
    assert not result.passed and "final answer missing: 2026-01-01 12:00:00" in result.failures


def test_negative_max_steps_and_explicit_expected_semantics():
    tools = [{"name": "get_time", "parameters": {}, "required": []}]
    responses = ['{"action":"get_time","args":{}}'] * 3
    failed = execute(AgentCase("limit-fail", "time", ["get_time"] * 3, max_steps=3), list(responses), FakeMCP(tools))
    assert not failed.passed and "agent did not return final" in failed.failures
    passed = execute(AgentCase("limit-ok", "time", ["get_time"] * 3, max_steps=3, expect_final=False, expect_max_steps=True), list(responses), FakeMCP(tools))
    assert passed.passed
