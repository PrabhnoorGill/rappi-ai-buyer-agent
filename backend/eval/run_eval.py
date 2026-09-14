"""
Evaluation harness.

Runs the agent against every scenario in backend/scenarios/, resetting the
mock DB to that scenario's seed data first, and grades each run on:
  - decision correctness      (did it pick the expected accept/modify/reject/investigate?)
  - quantity correctness      (if modify/accept, is the quantity in the expected range?)
  - information-gathering     (did it call the read tools before deciding, rather than guessing?)
  - constraint respect        (did the pre-execution validator pass?)
  - action taken correctly    (was a PO actually created when expected, and did post-execution validation pass?)

Usage:
    cd backend
    python -m eval.run_eval
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import db
from app.agent import run_agent

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"


def grade(scenario: dict, result: dict) -> dict:
    expected = scenario["expected"]
    final = result["final_decision"]
    notes = []

    decision_ok = final["decision"] == expected["decision"]
    if not decision_ok and final["decision"] in expected.get("acceptable_alternates", []):
        decision_ok = "partial"
        notes.append(f"Chose acceptable alternate '{final['decision']}' instead of '{expected['decision']}'.")

    quantity_ok = True
    if expected.get("quantity_range") and final["decision"] in ("accept", "modify"):
        lo, hi = expected["quantity_range"]
        qty = final.get("quantity") or 0
        quantity_ok = lo <= qty <= hi
        if not quantity_ok:
            notes.append(f"Quantity {qty} outside expected range [{lo}, {hi}].")

    gathered_info = any(step["type"] == "tool_call" for step in result["trace"])
    if not gathered_info:
        notes.append("Agent did not call any read tools before deciding.")

    constraints_respected = result["validation"]["passed"] if result["validation"] else False

    action_expected = expected["decision"] in ("accept", "modify")
    action_taken = result["action_result"] is not None
    action_ok = (action_expected == action_taken) or result["escalated"]
    exec_validation_ok = True
    if result["action_result"]:
        exec_validation_ok = result["action_result"]["execution_validation"]["passed"]

    passed = (
        decision_ok in (True, "partial")
        and quantity_ok
        and gathered_info
        and constraints_respected
        and action_ok
        and exec_validation_ok
        and not result["escalated"]
    )

    return {
        "scenario": scenario["name"],
        "passed": passed,
        "decision_ok": decision_ok,
        "quantity_ok": quantity_ok,
        "gathered_info": gathered_info,
        "constraints_respected": constraints_respected,
        "action_ok": action_ok,
        "exec_validation_ok": exec_validation_ok,
        "escalated": result["escalated"],
        "expected_decision": expected["decision"],
        "actual_decision": final["decision"],
        "actual_quantity": final.get("quantity"),
        "revisions": len(result["decision_history"]) - 1,
        "notes": notes,
    }


def run_all():
    scenario_files = sorted(SCENARIOS_DIR.glob("scenario_*.json"))
    report = []

    for path in scenario_files:
        scenario = json.loads(path.read_text())
        db.reset(scenario["seed"])

        try:
            result = run_agent(scenario["recommendation"])
            grade_result = grade(scenario, result)
            grade_result["reasoning"] = result["final_decision"]["reasoning"]
        except Exception as e:
            grade_result = {"scenario": scenario["name"], "passed": False, "error": str(e)}

        report.append(grade_result)
        status = "PASS" if grade_result.get("passed") else "FAIL"
        print(f"[{status}] {scenario['name']}")
        if grade_result.get("notes"):
            for n in grade_result["notes"]:
                print(f"    - {n}")
        if grade_result.get("error"):
            print(f"    ERROR: {grade_result['error']}")

    n_passed = sum(1 for r in report if r.get("passed"))
    print(f"\n{n_passed}/{len(report)} scenarios passed")

    out_path = Path(__file__).resolve().parent / "eval_report.json"
    out_path.write_text(json.dumps(report, indent=2))
    print(f"Full report written to {out_path}")
    return report


if __name__ == "__main__":
    run_all()
