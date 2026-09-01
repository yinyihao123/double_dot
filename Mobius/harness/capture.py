import time
from .models import AgentTrace, TraceEvent

class TraceObserver:
    def __init__(self, trace: AgentTrace, max_result_chars: int | None = 4000):
        self.trace, self.max_result_chars = trace, max_result_chars

    def _add(self, event_type, step, data=None, duration_ms=0.0, error=None):
        self.trace.events.append(TraceEvent(event_type, step, duration_ms, data or {}, error))

    def on_llm_call(self, step, context_length, response, duration_ms):
        self._add("llm_call", step, {"context_length": context_length, "response": response}, duration_ms)
    def on_action(self, step, action): self._add("action", step, {"action": action})
    def on_tool_call(self, step, name, arguments): self._add("tool_call", step, {"name": name, "arguments": arguments})
    def on_tool_result(self, step, name, result, duration_ms):
        value = result
        if self.max_result_chars is not None:
            value = str(value)[:self.max_result_chars]
        self._add("tool_result", step, {"name": name, "result": value}, duration_ms)
    def on_final(self, step, answer):
        self.trace.final_answer = answer
        self._add("final", step, {"answer": answer})
    def on_error(self, step, layer, error, duration_ms=0.0):
        self.trace.error = error
        self._add("error", step, {"layer": layer}, duration_ms, error)
