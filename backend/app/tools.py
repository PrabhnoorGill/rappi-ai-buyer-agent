"""
Tools available to the agent, plus their Anthropic tool-use schemas.

Each tool mirrors a real endpoint in app/main.py (inventory, forecast, open
POs, supplier terms, budget, storage, create/modify PO). The agent calls
these functions directly in-process; main.py exposes the same operations
over HTTP so the same "tools" are also usable as a normal internal API.
"""
from app.db import db

TOOL_SCHEMAS = [
    {
        "name": "get_inventory",
        "description": "Get current on-hand inventory for a product at a fulfillment node.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string"},
                "node_id": {"type": "string"},
            },
            "required": ["product_id", "node_id"],
        },
    },
    {
        "name": "get_demand_forecast",
        "description": "Get the expected demand forecast for a product at a node, including trend.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string"},
                "node_id": {"type": "string"},
            },
            "required": ["product_id", "node_id"],
        },
    },
    {
        "name": "get_open_purchase_orders",
        "description": "Get all open/confirmed/partially-fulfilled purchase orders already in flight for a product at a node.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string"},
                "node_id": {"type": "string"},
            },
            "required": ["product_id", "node_id"],
        },
    },
    {
        "name": "get_supplier_terms",
        "description": "Get a supplier's lead time, minimum order quantity, unit price, and reliability score.",
        "input_schema": {
            "type": "object",
            "properties": {"supplier_id": {"type": "string"}},
            "required": ["supplier_id"],
        },
    },
    {
        "name": "get_budget_status",
        "description": "Get the remaining purchasing budget available for a node/category.",
        "input_schema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string"},
                "category": {"type": "string", "default": "default"},
            },
            "required": ["node_id"],
        },
    },
    {
        "name": "get_storage_capacity",
        "description": "Get remaining free storage capacity (in product storage units) at a fulfillment node.",
        "input_schema": {
            "type": "object",
            "properties": {"node_id": {"type": "string"}},
            "required": ["node_id"],
        },
    },
    {
        "name": "submit_decision",
        "description": (
            "Submit your final decision on the recommendation. Call this exactly once, after you have "
            "gathered enough information from the read-only tools above. You do NOT create the purchase "
            "order yourself - a separate validation step will execute 'accept'/'modify' decisions once "
            "your reasoning and quantity have been checked against the live constraints."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "decision": {
                    "type": "string",
                    "enum": ["accept", "modify", "reject", "investigate"],
                },
                "quantity": {
                    "type": ["integer", "null"],
                    "description": "Final quantity ordered, if decision is accept or modify. Null otherwise.",
                },
                "reasoning": {
                    "type": "string",
                    "description": "Clear explanation of why, referencing the specific numbers you looked up.",
                },
                "key_factors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Short bullet list of the factors that drove the decision.",
                },
            },
            "required": ["decision", "quantity", "reasoning", "key_factors"],
        },
    },
]


def execute_tool(name: str, tool_input: dict) -> dict:
    if name == "get_inventory":
        rec = db.get_inventory(tool_input["product_id"], tool_input["node_id"])
        return rec or {"error": "no inventory record found"}

    if name == "get_demand_forecast":
        rec = db.get_forecast(tool_input["product_id"], tool_input["node_id"])
        return rec or {"error": "no forecast found"}

    if name == "get_open_purchase_orders":
        pos = db.get_open_pos(tool_input["product_id"], tool_input["node_id"])
        return {"open_purchase_orders": pos, "total_open_qty": sum(p["quantity"] for p in pos)}

    if name == "get_supplier_terms":
        rec = db.get_supplier(tool_input["supplier_id"])
        return rec or {"error": "supplier not found"}

    if name == "get_budget_status":
        rec = db.get_budget(tool_input["node_id"], tool_input.get("category", "default"))
        return rec or {"error": "no budget record found"}

    if name == "get_storage_capacity":
        rec = db.get_storage(tool_input["node_id"])
        return rec or {"error": "no storage record found"}

    if name == "create_purchase_order":
        po = db.create_po(
            tool_input["product_id"],
            tool_input["node_id"],
            tool_input["supplier_id"],
            tool_input["quantity"],
        )
        return po

    raise ValueError(f"Unknown tool: {name}")
