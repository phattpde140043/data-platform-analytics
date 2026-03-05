"""Tests for the data warehouse schema."""

import pytest

from src.warehouse.schema import DataWarehouse


@pytest.fixture
def warehouse():
    """In-memory DuckDB warehouse, discarded after each test."""
    wh = DataWarehouse(db_path=":memory:")
    yield wh
    wh.close()


def _login_event(n: int = 0) -> dict:
    return {
        "event_id": f"evt-login-{n}",
        "event_type": "user_login",
        "user_id": f"U00{n}",
        "session_id": f"sess-{n}",
        "timestamp": "2024-01-01T00:00:00+00:00",
        "device": "mobile",
    }


def _view_event(n: int = 0) -> dict:
    return {
        "event_id": f"evt-view-{n}",
        "event_type": "product_view",
        "user_id": f"U00{n}",
        "session_id": f"sess-{n}",
        "timestamp": "2024-01-01T00:00:00+00:00",
        "product_id": "P001",
        "product_name": "Wireless Headphones",
        "category": "Electronics",
        "price": 79.99,
        "quantity": None,
    }


def _purchase_event(n: int = 0) -> dict:
    return {
        "event_id": f"evt-pur-{n}",
        "event_type": "checkout_purchase",
        "user_id": f"U00{n}",
        "session_id": f"sess-{n}",
        "timestamp": "2024-01-01T00:00:00+00:00",
        "product_id": "P001",
        "product_name": "Wireless Headphones",
        "category": "Electronics",
        "price": 79.99,
        "quantity": 2,
        "total_amount": 159.98,
        "order_id": f"order-{n}",
        "payment_method": "credit_card",
    }


class TestInserts:
    def test_insert_user_activity(self, warehouse):
        warehouse.insert_user_activity(_login_event(1))
        rows = warehouse.conn.execute("SELECT COUNT(*) FROM user_activity").fetchone()
        assert rows[0] == 1

    def test_insert_product_interaction(self, warehouse):
        warehouse.insert_product_interaction(_view_event(1))
        rows = warehouse.conn.execute("SELECT COUNT(*) FROM product_interactions").fetchone()
        assert rows[0] == 1

    def test_insert_sales_transaction(self, warehouse):
        warehouse.insert_sales_transaction(_purchase_event(1))
        rows = warehouse.conn.execute("SELECT COUNT(*) FROM sales_transactions").fetchone()
        assert rows[0] == 1

    def test_duplicate_insert_is_ignored(self, warehouse):
        warehouse.insert_user_activity(_login_event(1))
        warehouse.insert_user_activity(_login_event(1))
        rows = warehouse.conn.execute("SELECT COUNT(*) FROM user_activity").fetchone()
        assert rows[0] == 1


class TestAnalyticsQueries:
    def _seed(self, warehouse):
        for i in range(5):
            warehouse.insert_user_activity(_login_event(i))
            warehouse.insert_product_interaction(_view_event(i))
        for i in range(3):
            warehouse.insert_sales_transaction(_purchase_event(i))
            warehouse.insert_product_interaction(
                {**_view_event(i + 10), "event_id": f"cart-{i}", "event_type": "add_to_cart"}
            )

    def test_most_viewed_products(self, warehouse):
        self._seed(warehouse)
        results = warehouse.most_viewed_products(limit=5)
        assert len(results) >= 1
        assert "product_id" in results[0]
        assert "view_count" in results[0]

    def test_top_selling_products(self, warehouse):
        self._seed(warehouse)
        results = warehouse.top_selling_products(limit=5)
        assert len(results) >= 1
        assert "units_sold" in results[0]
        assert "total_revenue" in results[0]

    def test_conversion_rate_range(self, warehouse):
        self._seed(warehouse)
        rate = warehouse.conversion_rate()
        assert 0.0 <= rate <= 1.0

    def test_conversion_rate_empty_warehouse(self, warehouse):
        assert warehouse.conversion_rate() == 0.0

    def test_revenue_by_category(self, warehouse):
        self._seed(warehouse)
        results = warehouse.revenue_by_category()
        assert len(results) >= 1
        assert "category" in results[0]
        assert "total_revenue" in results[0]

    def test_revenue_by_category_sorted_desc(self, warehouse):
        self._seed(warehouse)
        results = warehouse.revenue_by_category()
        revenues = [r["total_revenue"] for r in results]
        assert revenues == sorted(revenues, reverse=True)
