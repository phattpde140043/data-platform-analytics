"""Tests for the GraphQL analytics API."""

import pytest
from fastapi.testclient import TestClient

from src.warehouse.schema import DataWarehouse
from src.api.graphql_api import create_app


@pytest.fixture
def client():
    """TestClient backed by an in-memory warehouse seeded with fixture data."""
    wh = DataWarehouse(db_path=":memory:")
    _seed_warehouse(wh)
    app = create_app(warehouse=wh)
    yield TestClient(app)
    wh.close()


def _seed_warehouse(wh: DataWarehouse) -> None:
    """Insert a handful of rows into every analytics table."""
    for i in range(5):
        wh.insert_user_activity({
            "event_id": f"login-{i}",
            "event_type": "user_login",
            "user_id": f"U00{i}",
            "session_id": f"sess-{i}",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "device": "mobile",
        })
        wh.insert_product_interaction({
            "event_id": f"view-{i}",
            "event_type": "product_view",
            "user_id": f"U00{i}",
            "session_id": f"sess-{i}",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "product_id": "P001",
            "product_name": "Wireless Headphones",
            "category": "Electronics",
            "price": 79.99,
            "quantity": None,
        })
    for i in range(3):
        wh.insert_sales_transaction({
            "event_id": f"pur-{i}",
            "event_type": "checkout_purchase",
            "user_id": f"U00{i}",
            "session_id": f"sess-{i}",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "product_id": "P001",
            "product_name": "Wireless Headphones",
            "category": "Electronics",
            "price": 79.99,
            "quantity": 1,
            "total_amount": 79.99,
            "order_id": f"ord-{i}",
            "payment_method": "credit_card",
        })


class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestGraphQLQueries:
    def _gql(self, client, query: str) -> dict:
        resp = client.post("/graphql", json={"query": query})
        assert resp.status_code == 200
        return resp.json()

    def test_most_viewed_products(self, client):
        result = self._gql(client, "{ mostViewedProducts { productId productName viewCount } }")
        data = result["data"]["mostViewedProducts"]
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["viewCount"] >= 1

    def test_top_selling_products(self, client):
        result = self._gql(client, "{ topSellingProducts { productId unitsSold totalRevenue } }")
        data = result["data"]["topSellingProducts"]
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["unitsSold"] >= 1

    def test_conversion_rate(self, client):
        result = self._gql(client, "{ conversionRate { rate } }")
        rate = result["data"]["conversionRate"]["rate"]
        assert 0.0 <= rate <= 1.0

    def test_revenue_by_category(self, client):
        result = self._gql(client, "{ revenueByCategory { category totalRevenue transactionCount } }")
        data = result["data"]["revenueByCategory"]
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["category"] == "Electronics"
        assert data[0]["totalRevenue"] > 0
