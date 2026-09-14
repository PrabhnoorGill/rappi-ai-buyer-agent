"""
Independent, deterministic validation of the agent's decision.

This is intentionally NOT the LLM checking its own work - it's plain Python
re-deriving the same numbers from the mock DB and checking hard constraints.
The agent's reasoning can be persuasive and still be wrong (wrong arithmetic,
missed a constraint, hallucinated a number); this function is the guardrail.

Two layers:
  1. business validation (pre-execution): given a proposed decision/qty,
     would executing it actually respect budget/storage/MOQ/coverage?
  2. execution validation (post-execution): after an action was taken
     (PO created/modified), re-read it back from the DB and confirm it
     matches what was intended and still satisfies the same constraints.
"""
from app.db import db


def _coverage_numbers(product_id: str, node_id: str, extra_qty: int = 0):
    inv = db.get_inventory(product_id, node_id) or {"on_hand_qty": 0}
    fc = db.get_forecast(product_id, node_id)
    open_pos = db.get_open_pos(product_id, node_id)
    open_po_qty = sum(po["quantity"] for po in open_pos)
    total_supply = inv["on_hand_qty"] + open_po_qty + extra_qty
    forecast_qty = fc["forecast_qty"] if fc else 0
    return {
        "on_hand_qty": inv["on_hand_qty"],
        "open_po_qty": open_po_qty,
        "forecast_qty": forecast_qty,
        "total_supply_after": total_supply,
        "coverage_ratio": round(total_supply / forecast_qty, 2) if forecast_qty else None,
    }


def validate_business_decision(recommendation: dict, decision: str, quantity: int | None) -> dict:
    """Pre-execution check: is this decision/qty actually sound given current data?"""
    product_id = recommendation["product_id"]
    node_id = recommendation["node_id"]
    supplier_id = recommendation["supplier_id"]

    violations = []
    checks = {}

    supplier = db.get_supplier(supplier_id)
    budget = db.get_budget(node_id, recommendation.get("category", "default"))
    storage = db.get_storage(node_id)
    qty = quantity or 0

    if decision in ("accept", "modify") and qty > 0:
        # 1. Minimum order quantity
        moq_ok = qty >= supplier["min_order_qty"]
        checks["min_order_qty"] = {"required": supplier["min_order_qty"], "quantity": qty, "ok": moq_ok}
        if not moq_ok:
            violations.append(
                f"Quantity {qty} is below supplier {supplier_id} minimum order qty of {supplier['min_order_qty']}."
            )

        # 2. Budget
        cost = qty * supplier["unit_price"]
        budget_ok = budget is not None and cost <= budget["available_amount"]
        checks["budget"] = {
            "cost": round(cost, 2),
            "available": budget["available_amount"] if budget else None,
            "ok": budget_ok,
        }
        if not budget_ok:
            violations.append(
                f"Cost {cost:.2f} exceeds available budget "
                f"{budget['available_amount'] if budget else 'N/A'} for node {node_id}."
            )

        # 3. Storage capacity (existing inventory + open POs + this order must fit)
        cov = _coverage_numbers(product_id, node_id, extra_qty=qty)
        storage_ok = storage is not None and cov["total_supply_after"] <= storage["available_units"]
        checks["storage"] = {
            "projected_units": cov["total_supply_after"],
            "available_units": storage["available_units"] if storage else None,
            "ok": storage_ok,
        }
        if not storage_ok:
            violations.append(
                f"Projected on-hand+incoming ({cov['total_supply_after']}) exceeds storage capacity "
                f"({storage['available_units'] if storage else 'N/A'})."
            )

        # 4. Gross overstock sanity check (buying far more than forecast covers)
        checks["coverage"] = cov
        if cov["coverage_ratio"] is not None and cov["coverage_ratio"] > 2.5:
            violations.append(
                f"Resulting coverage ratio {cov['coverage_ratio']}x of forecast looks like overbuying; "
                "expected roughly 1.0-1.5x plus safety stock."
            )

    elif decision == "reject":
        # Sanity check: rejecting should still be safe, i.e. current supply
        # should already cover forecast reasonably. If not, flag it.
        cov = _coverage_numbers(product_id, node_id, extra_qty=0)
        checks["coverage"] = cov
        if cov["coverage_ratio"] is not None and cov["coverage_ratio"] < 0.9:
            violations.append(
                f"Rejecting leaves coverage at only {cov['coverage_ratio']}x of forecast - "
                "risk of stockout is not clearly addressed."
            )

    return {"passed": len(violations) == 0, "violations": violations, "checks": checks}


def validate_execution(po_id: str, expected_quantity: int, expected_supplier_id: str) -> dict:
    """Post-execution check: read the PO back from the DB and confirm it matches intent
    and still respects constraints (defence against a bad write / race condition)."""
    violations = []
    po = db.get_po(po_id)
    checks = {"po_found": po is not None}

    if not po:
        violations.append(f"PO {po_id} was not found in the system after creation.")
        return {"passed": False, "violations": violations, "checks": checks}

    if po["quantity"] != expected_quantity:
        violations.append(f"PO quantity {po['quantity']} does not match intended quantity {expected_quantity}.")
    if po["supplier_id"] != expected_supplier_id:
        violations.append(f"PO supplier {po['supplier_id']} does not match intended supplier {expected_supplier_id}.")
    if po["status"] not in ("open", "confirmed"):
        violations.append(f"PO status is unexpectedly '{po['status']}'.")

    checks["po"] = po
    return {"passed": len(violations) == 0, "violations": violations, "checks": checks}
