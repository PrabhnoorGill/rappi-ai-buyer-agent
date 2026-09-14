"""Default dataset loaded when the API server starts, used by the demo UI."""

DEFAULT_SEED = {
    "products": [
        {"product_id": "P-001", "name": "Oat Milk 1L", "unit_cost": 2.10, "unit_storage_volume": 1.0},
    ],
    "suppliers": [
        {
            "supplier_id": "S-01",
            "name": "NordicDairy Co.",
            "lead_time_days": 7,
            "min_order_qty": 200,
            "unit_price": 2.10,
            "reliability_score": 0.94,
        },
        {
            "supplier_id": "S-02",
            "name": "PlantBev Regional",
            "lead_time_days": 3,
            "min_order_qty": 100,
            "unit_price": 2.35,
            "reliability_score": 0.88,
        },
    ],
    "inventory": [
        {"product_id": "P-001", "node_id": "N-BOG-01", "on_hand_qty": 220},
    ],
    "forecasts": [
        {
            "product_id": "P-001",
            "node_id": "N-BOG-01",
            "horizon_days": 14,
            "forecast_qty": 900,
            "daily_avg": 64.3,
            "trend": "rising",
        },
    ],
    "purchase_orders": [
        {
            "po_id": "PO-0001",
            "product_id": "P-001",
            "node_id": "N-BOG-01",
            "supplier_id": "S-01",
            "quantity": 150,
            "status": "confirmed",
            "expected_delivery_days": 5,
        },
    ],
    "budgets": [
        {"node_id": "N-BOG-01", "category": "default", "available_amount": 3000.0},
    ],
    "storage": [
        {"node_id": "N-BOG-01", "available_units": 1000},
    ],
}

DEFAULT_RECOMMENDATION = {
    "product_id": "P-001",
    "node_id": "N-BOG-01",
    "supplier_id": "S-01",
    "recommended_qty": 800,
    "category": "default",
}
