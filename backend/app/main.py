from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.db import db
from app.seed_data import DEFAULT_SEED, DEFAULT_RECOMMENDATION
from app.models import CreatePORequest, ModifyPORequest, Recommendation
from app.agent import run_agent

app = FastAPI(title="Rappi AI Purchasing Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def seed():
    db.reset(DEFAULT_SEED)


# ---------------------------------------------------------------------------
# Data APIs - these are the same "tools" the agent uses, exposed over HTTP.
# ---------------------------------------------------------------------------

@app.get("/api/inventory")
def get_inventory(product_id: str, node_id: str):
    rec = db.get_inventory(product_id, node_id)
    if not rec:
        raise HTTPException(404, "no inventory record")
    return rec


@app.get("/api/forecast")
def get_forecast(product_id: str, node_id: str):
    rec = db.get_forecast(product_id, node_id)
    if not rec:
        raise HTTPException(404, "no forecast record")
    return rec


@app.get("/api/purchase-orders")
def get_open_pos(product_id: str, node_id: str):
    return db.get_open_pos(product_id, node_id)


@app.get("/api/suppliers/{supplier_id}")
def get_supplier(supplier_id: str):
    rec = db.get_supplier(supplier_id)
    if not rec:
        raise HTTPException(404, "supplier not found")
    return rec


@app.get("/api/budget")
def get_budget(node_id: str, category: str = "default"):
    rec = db.get_budget(node_id, category)
    if not rec:
        raise HTTPException(404, "no budget record")
    return rec


@app.get("/api/storage")
def get_storage(node_id: str):
    rec = db.get_storage(node_id)
    if not rec:
        raise HTTPException(404, "no storage record")
    return rec


@app.post("/api/purchase-orders")
def create_po(req: CreatePORequest):
    return db.create_po(req.product_id, req.node_id, req.supplier_id, req.quantity)


@app.patch("/api/purchase-orders/{po_id}")
def modify_po(po_id: str, req: ModifyPORequest):
    po = db.modify_po(po_id, req.quantity)
    if not po:
        raise HTTPException(404, "PO not found")
    return po


# ---------------------------------------------------------------------------
# Demo helpers
# ---------------------------------------------------------------------------

@app.get("/api/state")
def get_state():
    """Full current mock DB state, for the demo UI to display."""
    return {
        "products": list(db.products.values()),
        "suppliers": list(db.suppliers.values()),
        "inventory": list(db.inventory.values()),
        "forecasts": list(db.forecasts.values()),
        "purchase_orders": list(db.purchase_orders.values()),
        "budgets": list(db.budgets.values()),
        "storage": list(db.storage.values()),
        "default_recommendation": DEFAULT_RECOMMENDATION,
    }


@app.post("/api/state/reset")
def reset_state():
    db.reset(DEFAULT_SEED)
    return {"status": "reset"}


# ---------------------------------------------------------------------------
# The agent endpoint
# ---------------------------------------------------------------------------

@app.post("/api/agent/review")
def agent_review(recommendation: Recommendation):
    return run_agent(recommendation.model_dump())
