import time
from agent import run_agent
from .capture import TraceObserver
from .judge import RuleJudge
from .models import AgentCase, AgentTrace, CaseResult

class HarnessRunner:
    def __init__(self, llm, client, judge=None):
        self.llm, self.client, self.judge = llm, client, judge or RuleJudge()

    def run_case(self, case: AgentCase) -> CaseResult:
        trace = AgentTrace(case.question)
        observer = TraceObserver(trace)
        started = time.monotonic()
        try:
            run_agent(case.question, llm=self.llm, client=self.client,
                      max_steps=case.max_steps, trace_callback=observer)
        except Exception as exc:
            trace.error = str(exc)
        trace.duration_ms = (time.monotonic() - started) * 1000
        return self.judge.judge(case, trace)

    def run_all(self, cases):
        return [self.run_case(case) for case in cases]
