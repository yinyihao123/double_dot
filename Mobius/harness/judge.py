from .models import AgentCase, AgentTrace, CaseResult

class RuleJudge:
    def judge(self, case: AgentCase, trace: AgentTrace) -> CaseResult:
        failures = []
        actual_tools = [e.data["name"] for e in trace.events if e.event_type == "tool_call"]
        allowed = set(case.expected_tools)
        for event in (e for e in trace.events if e.event_type == "action"):
            action = event.data["action"]
            if (action.get("action") not in allowed
                    and action.get("action") not in case.expected_invalid_tools
                    and action.get("action") != "final"):
                failures.append(f"unexpected action/tool: {action.get('action')}")
        if actual_tools != case.expected_tools:
            failures.append(f"expected tools {case.expected_tools}, got {actual_tools}")
        for event in (e for e in trace.events if e.event_type == "tool_call"):
            expected = case.expected_arguments.get(event.data["name"])
            if expected is not None and event.data["arguments"] != expected:
                failures.append(f"arguments mismatch for {event.data['name']}")
        if case.expect_final and trace.final_answer is None:
            failures.append("agent did not return final")
        if case.expected_final is not None and trace.final_answer != case.expected_final:
            failures.append("final answer mismatch")
        for text in case.expected_final_contains:
            if not trace.final_answer or text not in trace.final_answer:
                failures.append(f"final answer missing: {text}")
        steps = [e.step for e in trace.events] or [0]
        if max(steps) > case.max_steps:
            failures.append("max_steps exceeded")
        if case.expect_max_steps and max(steps) != case.max_steps:
            failures.append(f"expected max_steps {case.max_steps}, got {max(steps)}")
        if any(e.event_type == "error" for e in trace.events):
            failures.append("trace contains error")
        return CaseResult(case, trace, not failures, failures)
