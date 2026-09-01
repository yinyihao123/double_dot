from harness.models import AgentCase
from harness.runner import HarnessRunner
from harness.judge import RuleJudge

class FakeMCP:
    def list_tools(self):
        return [{"name":"get_time","description":"time","parameters":{},"required":[]}, {"name":"get_cpu_usage","description":"cpu","parameters":{},"required":[]}]
    def call_tool(self, name, args): return {"value": "12:00"} if name == "get_time" else {"value": "10%"}

def run(responses, case):
    return HarnessRunner(lambda _: responses.pop(0), FakeMCP()).run_case(case)

def test_harness_cases():
    assert run(['{"action":"get_time","args":{}}','{"action":"final","answer":"12:00"}'], AgentCase('time','time', ['get_time'], {'get_time':{}}, ['12:00'])).passed
    assert run(['{"action":"final","answer":"hello"}'], AgentCase('final','hi', expected_final='hello')).passed
    multi = run(['{"action":"get_time","args":{}}','{"action":"get_cpu_usage","args":{}}','{"action":"final","answer":"12:00 10%"}'], AgentCase('multi','both',['get_time','get_cpu_usage'], expected_final_contains=['12:00','10%']))
    assert multi.passed and any(e.event_type == 'tool_result' for e in multi.trace.events)
    assert not run(['{"action":"missing","args":{}}'] * 3, AgentCase('bad','x', max_steps=2)).passed
    assert not run(['{"action":"get_time","args":{}}'] * 3, AgentCase('limit','x', ['get_time'], max_steps=2)).passed

def test_harness_uses_fakes_only():
    result = run(['{"action":"final","answer":"offline"}'], AgentCase('offline','x', expected_final='offline'))
    assert result.passed and result.llm_calls == 1
