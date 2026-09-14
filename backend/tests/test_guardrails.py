import json
import unittest
from pathlib import Path

from app.db import db
from app.validator import validate_business_decision


SCENARIOS = Path(__file__).resolve().parents[1] / "scenarios"


class GuardrailTests(unittest.TestCase):
    def seed(self, filename: str) -> dict:
        scenario = json.loads((SCENARIOS / filename).read_text())
        db.reset(scenario["seed"])
        return scenario

    def test_valid_accept_passes(self):
        scenario = self.seed("scenario_1_clean_accept.json")
        result = validate_business_decision(scenario["recommendation"], "accept", 800)
        self.assertTrue(result["passed"], result["violations"])

    def test_accept_cannot_silently_change_quantity(self):
        scenario = self.seed("scenario_1_clean_accept.json")
        result = validate_business_decision(scenario["recommendation"], "accept", 750)
        self.assertFalse(result["passed"])
        self.assertIn("use modify", result["violations"][0])

    def test_action_requires_positive_integer_quantity(self):
        scenario = self.seed("scenario_1_clean_accept.json")
        for quantity in (None, 0, -1):
            with self.subTest(quantity=quantity):
                result = validate_business_decision(scenario["recommendation"], "modify", quantity)
                self.assertFalse(result["passed"])

    def test_non_order_decision_cannot_contain_quantity(self):
        scenario = self.seed("scenario_2_already_covered_reject.json")
        result = validate_business_decision(scenario["recommendation"], "reject", 1)
        self.assertFalse(result["passed"])

    def test_storage_limit_accounts_for_existing_supply(self):
        scenario = self.seed("scenario_3_storage_constrained_modify.json")
        allowed = validate_business_decision(scenario["recommendation"], "modify", 350)
        blocked = validate_business_decision(scenario["recommendation"], "modify", 351)
        self.assertTrue(allowed["passed"], allowed["violations"])
        self.assertFalse(blocked["passed"])
        self.assertIn("storage capacity", blocked["violations"][0])

    def test_po_only_debits_its_own_budget_category(self):
        scenario = self.seed("scenario_1_clean_accept.json")
        db.budgets[("N-01", "secondary")] = {
            "node_id": "N-01", "category": "secondary", "available_amount": 999.0
        }
        db.create_po("P-001", "N-01", "S-01", 100, "default")
        self.assertEqual(db.get_budget("N-01", "default")["available_amount"], 4800.0)
        self.assertEqual(db.get_budget("N-01", "secondary")["available_amount"], 999.0)


if __name__ == "__main__":
    unittest.main()
