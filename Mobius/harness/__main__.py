import argparse
import json
from .cases import build_cases
from .report import summarize, to_dict
from .runner import HarnessRunner
from .gate import DeterministicGate
from .report import summarize_with_gate


def main():
    parser = argparse.ArgumentParser(description="Mobius Agent Harness")
    parser.add_argument("--json", metavar="PATH", help="write JSON report")
    args = parser.parse_args()
    results = []
    for case, llm, client in build_cases():
        results.append(HarnessRunner(llm, client).run_case(case))
    gates = [DeterministicGate().evaluate(r) for r in results]
    summary = summarize_with_gate(results, gates)
    print("Mobius Agent Harness\n")
    print(f"Cases: {summary['total']}")
    print(f"PASS: {summary['pass_count']}")
    print(f"WARN: {summary['warn_count']}")
    print(f"FAIL: {summary['fail_count']}")
    print(f"Pass rate: {summary['pass_rate']:.0f}%\n")
    for result in results:
        gate = gates[len([x for x in results[:results.index(result)]])]
        print(f"[{gate.status}] {result.case.name}")
        reasons = gate.failures + gate.warnings
        if reasons: print("Reason: " + "; ".join(reasons))
    print(f"\nLLM calls: {summary['llm_calls']}")
    print(f"Tool calls: {summary['tool_calls']}")
    print(f"Duration: {summary['average_duration_ms']:.1f} ms (average)")
    print(f"\nGate: {summary['gate_status']}")
    if args.json:
        payload = to_dict(results)
        payload["gate"] = {"status": summary["gate_status"], "failures": [f for g in gates for f in g.failures], "warnings": [w for g in gates for w in g.warnings]}
        payload["summary"].update(summary)
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)
    return 0 if summary["gate_status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
