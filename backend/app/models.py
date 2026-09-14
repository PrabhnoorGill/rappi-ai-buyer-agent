from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class Product(BaseModel):
    product_id: str
    name: str
    unit_cost: float
    unit_storage_volume: float  # storage units consumed per unit of product


class Supplier(BaseModel):
    supplier_id: str
    name: str
    lead_time_days: int
    min_order_qty: int
    unit_price: float
    reliability_score: float  # 0-1, historical on-time-in-full rate


class Inventory(BaseModel):
    product_id: str
    node_id: str
    on_hand_qty: int


class DemandForecast(BaseModel):
    product_id: str
    node_id: str
    horizon_days: int
    forecast_qty: int  # total expected demand over horizon_days
    daily_avg: float
    trend: Literal["stable", "rising", "falling"] = "stable"


class PurchaseOrder(BaseModel):
    po_id: str
    product_id: str
    node_id: str
    supplier_id: str
    quantity: int
    status: Literal["open", "confirmed", "partially_fulfilled", "cancelled"] = "open"
    expected_delivery_days: int  # days from creation


class Budget(BaseModel):
    node_id: str
    category: str
    available_amount: float


class StorageCapacity(BaseModel):
    node_id: str
    available_units: int  # total capacity, in the same unit as unit_storage_volume


class Recommendation(BaseModel):
    product_id: str
    node_id: str
    supplier_id: str
    recommended_qty: int = Field(gt=0)
    category: str = "default"


class AgentDecision(BaseModel):
    decision: Literal["accept", "modify", "reject", "investigate"]
    quantity: Optional[int] = None
    reasoning: str
    key_factors: List[str]


class ValidationResult(BaseModel):
    passed: bool
    violations: List[str]
    checks: dict


class AgentRunResult(BaseModel):
    recommendation: Recommendation
    trace: List[dict]
    decision_history: List[dict]
    final_decision: AgentDecision
    validation: Optional[ValidationResult] = None
    action_result: Optional[dict] = None
    escalated: bool = False
