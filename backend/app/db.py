"""
In-memory mock database.

This stands in for the buyer's real systems (inventory, forecasting, PO
management, supplier master, budget/storage). It's intentionally a plain
Python dict store rather than a real DB so that:
  - each test scenario can seed a fresh, isolated state
  - there's no setup burden for a 6-8h assignment / local reviewer

Swapping this for Postgres/SQLite later only touches this file - every
route and tool function goes through the functions below.
"""
import itertools
from typing import Optional


class MockDB:
    def __init__(self):
        self._po_counter = itertools.count(1)
        self.reset({})

    def reset(self, seed: dict):
        """Wipe and reseed all tables from a scenario dict."""
        self.products = {p["product_id"]: dict(p) for p in seed.get("products", [])}
        self.suppliers = {s["supplier_id"]: dict(s) for s in seed.get("suppliers", [])}
        self.inventory = {
            (i["product_id"], i["node_id"]): dict(i) for i in seed.get("inventory", [])
        }
        self.forecasts = {
            (f["product_id"], f["node_id"]): dict(f) for f in seed.get("forecasts", [])
        }
        self.purchase_orders = {po["po_id"]: dict(po) for po in seed.get("purchase_orders", [])}
        self.budgets = {
            (b["node_id"], b["category"]): dict(b) for b in seed.get("budgets", [])
        }
        self.storage = {s["node_id"]: dict(s) for s in seed.get("storage", [])}
        self._po_counter = itertools.count(len(self.purchase_orders) + 1)

    # ---- reads ----
    def get_product(self, product_id: str) -> Optional[dict]:
        return self.products.get(product_id)

    def get_supplier(self, supplier_id: str) -> Optional[dict]:
        return self.suppliers.get(supplier_id)

    def get_inventory(self, product_id: str, node_id: str) -> Optional[dict]:
        return self.inventory.get((product_id, node_id))

    def get_forecast(self, product_id: str, node_id: str) -> Optional[dict]:
        return self.forecasts.get((product_id, node_id))

    def get_open_pos(self, product_id: str, node_id: str) -> list:
        return [
            po for po in self.purchase_orders.values()
            if po["product_id"] == product_id
            and po["node_id"] == node_id
            and po["status"] in ("open", "confirmed", "partially_fulfilled")
        ]

    def get_budget(self, node_id: str, category: str) -> Optional[dict]:
        return self.budgets.get((node_id, category))

    def get_storage(self, node_id: str) -> Optional[dict]:
        return self.storage.get(node_id)

    def get_po(self, po_id: str) -> Optional[dict]:
        return self.purchase_orders.get(po_id)

    # ---- writes (actions) ----
    def create_po(self, product_id: str, node_id: str, supplier_id: str, quantity: int,
                  category: str = "default") -> dict:
        supplier = self.suppliers[supplier_id]
        po_id = f"PO-{next(self._po_counter):04d}"
        po = {
            "po_id": po_id,
            "product_id": product_id,
            "node_id": node_id,
            "supplier_id": supplier_id,
            "quantity": quantity,
            "status": "open",
            "expected_delivery_days": supplier["lead_time_days"],
        }
        self.purchase_orders[po_id] = po
        # Buying spends budget and reserves storage against incoming stock.
        budget = self.budgets.get((node_id, category))
        if budget:
            budget["available_amount"] -= quantity * supplier["unit_price"]
        return po

    def modify_po(self, po_id: str, quantity: int) -> Optional[dict]:
        po = self.purchase_orders.get(po_id)
        if not po:
            return None
        supplier = self.suppliers[po["supplier_id"]]
        delta = quantity - po["quantity"]
        po["quantity"] = quantity
        for (n, cat), b in self.budgets.items():
            if n == po["node_id"]:
                b["available_amount"] -= delta * supplier["unit_price"]
        return po


db = MockDB()
