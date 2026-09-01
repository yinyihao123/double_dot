from dataclasses import dataclass, field
from .models import AgentCase, CaseResult

@dataclass
class GateResult:
    status: str
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

class DeterministicGate:
    def evaluate(self, result: CaseResult) -> GateResult:
        case, trace = result.case, result.trace
        failures = list(result.failures)
        warnings = []
        llm_calls, tool_calls = result.llm_calls, result.tool_calls
        if case.max_llm_calls is not None and llm_calls > case.max_llm_calls:
            warnings.append(f"LLM calls higher than expected: {llm_calls} > {case.max_llm_calls}")
        if case.max_tool_calls is not None and tool_calls > case.max_tool_calls:
            warnings.append(f"Tool calls higher than expected: {tool_calls} > {case.max_tool_calls}")
        names = [e.data.get("name") for e in trace.events if e.event_type == "tool_call"]
        if (not case.expect_max_steps and len(names) >= 3
                and any(names[i] == names[i + 1] == names[i + 2] for i in range(len(names) - 2))):
            failures.append("repeated tool call loop")
        if trace.error:
            failures.append(f"unhandled error: {trace.error}")
        status = "FAIL" if failures else ("WARN" if warnings else "PASS")
        return GateResult(status, failures, warnings, {"llm_calls": llm_calls, "tool_calls": tool_calls, "duration_ms": trace.duration_ms})

    def evaluate_all(self, results):
        gates = [self.evaluate(r) for r in results]
        status = "FAIL" if any(g.status == "FAIL" for g in gates) else ("WARN" if any(g.status == "WARN" for g in gates) else "PASS")
        return GateResult(status, [f for g in gates for f in g.failures], [w for g in gates for w in g.warnings], {"cases": gates})
