from harness.gate import DeterministicGate
from harness.models import AgentCase, AgentTrace, CaseResult, TraceEvent

def result(case, events, final='ok'):
    trace=AgentTrace(case.question, events=events, final_answer=final)
    return CaseResult(case, trace, True, [])

def test_gate_pass_warn_fail():
    gate=DeterministicGate()
    passed=result(AgentCase('ok','x'), [TraceEvent('final',1)])
    assert gate.evaluate(passed).status == 'PASS'
    warned=result(AgentCase('slow','x', max_llm_calls=1), [TraceEvent('llm_call',1), TraceEvent('llm_call',2), TraceEvent('final',2)])
    assert gate.evaluate(warned).status == 'WARN'
    failed=result(AgentCase('bad','x'), [TraceEvent('action',1,data={'action': 'missing'}), TraceEvent('final',1)])
    failed.failures=['unexpected action/tool: missing']
    assert gate.evaluate(failed).status == 'FAIL'

def test_gate_max_steps_missing_final_and_illegal_tool_fail():
    gate=DeterministicGate()
    case=AgentCase('limit','x', max_steps=2)
    trace=AgentTrace('x', [TraceEvent('tool_call',1,data={'name':'x'}), TraceEvent('tool_call',2,data={'name':'x'})])
    r=CaseResult(case,trace,False,['agent did not return final'])
    assert gate.evaluate(r).status == 'FAIL'
