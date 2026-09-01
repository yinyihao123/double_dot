from dataclasses import dataclass, field
from typing import Any

@dataclass
class TraceEvent:
    event_type: str
    step: int
    duration_ms: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

@dataclass
class AgentTrace:
    question: str
    events: list[TraceEvent] = field(default_factory=list)
    final_answer: str | None = None
    duration_ms: float = 0.0
    error: str | None = None

@dataclass
class AgentCase:
    name: str
    question: str
    expected_tools: list[str] = field(default_factory=list)
    expected_arguments: dict[str, dict] = field(default_factory=dict)
    expected_final_contains: list[str] = field(default_factory=list)
    expected_final: str | None = None
    max_steps: int = 5
    expect_final: bool = True
    expect_max_steps: bool = False
    expected_invalid_tools: list[str] = field(default_factory=list)
    max_llm_calls: int | None = None
    max_tool_calls: int | None = None

@dataclass
class CaseResult:
    case: AgentCase
    trace: AgentTrace
    passed: bool
    failures: list[str] = field(default_factory=list)

    @property
    def llm_calls(self): return sum(e.event_type == "llm_call" for e in self.trace.events)
    @property
    def tool_calls(self): return sum(e.event_type == "tool_call" for e in self.trace.events)
