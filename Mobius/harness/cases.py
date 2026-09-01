from .models import AgentCase


TOOLS = [
    {"name": "get_time", "description": "time", "parameters": {}, "required": []},
    {"name": "get_cpu_usage", "description": "cpu", "parameters": {}, "required": []},
]


class FakeMCPClient:
    def __init__(self):
        self.calls = []

    def list_tools(self):
        return TOOLS

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if name == "get_time":
            return "2026-01-01 12:00:00"
        if name == "get_cpu_usage":
            return "CPU:10.0%"
        raise AssertionError("unexpected tool execution: " + name)


class FakeLLM:
    def __init__(self, responses):
        self.responses = iter(responses)

    def __call__(self, context):
        return next(self.responses)


def _case(name, question, responses, **kwargs):
    return AgentCase(name=name, question=question, **kwargs), FakeLLM(responses), FakeMCPClient()


def build_cases():
    return [
        _case("direct_final", "你好，你是谁？", ['{"action":"final","answer":"我是 Mobius Agent。"}'], expected_final_contains=["Mobius"]),
        _case("get_time", "现在几点？", ['{"action":"get_time","args":{}}', '{"action":"final","answer":"现在是 2026-01-01 12:00:00。"}'], expected_tools=["get_time"], expected_arguments={"get_time": {}}, expected_final_contains=["12:00:00"]),
        _case("get_cpu", "当前 CPU 使用率？", ['{"action":"get_cpu_usage","args":{}}', '{"action":"final","answer":"CPU:10.0%"}'], expected_tools=["get_cpu_usage"], expected_arguments={"get_cpu_usage": {}}, expected_final_contains=["10.0%"]),
        _case("multi_tool", "时间和 CPU？", ['{"action":"get_time","args":{}}', '{"action":"get_cpu_usage","args":{}}', '{"action":"final","answer":"12:00:00，CPU:10.0%"}'], expected_tools=["get_time", "get_cpu_usage"], expected_final_contains=["12:00:00", "10.0%"]),
        _case("unsupported", "今天比特币价格？", ['{"action":"final","answer":"当前没有查询比特币价格的工具。"}'], expected_tools=[]),
        _case("invalid_tool", "调用不存在工具？", ['{"action":"missing","args":{}}', '{"action":"final","answer":"不存在该工具。"}'], expected_tools=[], expected_invalid_tools=["missing"]),
        _case("max_steps", "反复执行", ['{"action":"get_time","args":{}}'] * 3, expected_tools=["get_time", "get_time", "get_time"], max_steps=3, expect_final=False, expect_max_steps=True),
    ]
