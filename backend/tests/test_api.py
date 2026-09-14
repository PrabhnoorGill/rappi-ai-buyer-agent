import unittest

from fastapi.testclient import TestClient

from app.main import app


class ApiTests(unittest.TestCase):
    def test_state_and_agent_boundary(self):
        # Context management runs the FastAPI startup hook and seeds the demo.
        with TestClient(app) as client:
            state = client.get("/api/state")
            self.assertEqual(state.status_code, 200)
            self.assertEqual(state.json()["products"][0]["product_id"], "P-001")

            # Demo mode runs end-to-end with no secret or paid API account.
            review = client.post("/api/agent/review", json={
                "product_id": "P-001", "node_id": "N-BOG-01",
                "supplier_id": "S-01", "recommended_qty": 800,
            })
            self.assertEqual(review.status_code, 200)
            self.assertEqual(review.json()["final_decision"]["decision"], "modify")
            self.assertIsNotNone(review.json()["action_result"])

            # Order writes are intentionally unavailable outside the validated
            # agent orchestrator.
            bypass = client.post("/api/purchase-orders", json={
                "product_id": "P-001", "node_id": "N-BOG-01",
                "supplier_id": "S-01", "quantity": 800,
            })
            self.assertEqual(bypass.status_code, 405)

            invalid = client.post("/api/agent/review", json={
                "product_id": "P-001", "node_id": "N-BOG-01",
                "supplier_id": "S-01", "recommended_qty": 0,
            })
            self.assertEqual(invalid.status_code, 422)


if __name__ == "__main__":
    unittest.main()
