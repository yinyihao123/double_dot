import dataclasses

def summarize(results):
    total = len(results)
    passed = sum(result.passed for result in results)
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": (passed / total * 100) if total else 0.0,
        "llm_calls": sum(r.llm_calls for r in results),
        "tool_calls": sum(r.tool_calls for r in results),
        "average_duration_ms": (sum(r.trace.duration_ms for r in results) / total) if total else 0.0,
    }

def summarize_with_gate(results, gates):
    summary = summarize(results)
    summary.update({"pass_count": sum(g.status == "PASS" for g in gates),
                    "warn_count": sum(g.status == "WARN" for g in gates),
                    "fail_count": sum(g.status == "FAIL" for g in gates),
                    "gate_status": "FAIL" if any(g.status == "FAIL" for g in gates) else ("WARN" if any(g.status == "WARN" for g in gates) else "PASS")})
    return summary

def to_dict(results):
    return {"summary": summarize(results), "cases": [dataclasses.asdict(r) for r in results]}
