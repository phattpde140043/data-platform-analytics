"""
Data Warehouse schema and storage layer backed by DuckDB.

Creates and manages three analytics tables:
  * user_activity        – login and browsing events per user
  * product_interactions – product view / cart interactions
  * sales_transactions   – completed purchases
"""

import logging
from typing import Any

import duckdb

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DDL statements
# ---------------------------------------------------------------------------

DDL_USER_ACTIVITY = """
CREATE TABLE IF NOT EXISTS user_activity (
    event_id        VARCHAR PRIMARY KEY,
    user_id         VARCHAR NOT NULL,
    session_id      VARCHAR NOT NULL,
    event_type      VARCHAR NOT NULL,
    device          VARCHAR,
    timestamp       TIMESTAMPTZ NOT NULL,
    inserted_at     TIMESTAMPTZ DEFAULT now()
);
"""

DDL_PRODUCT_INTERACTIONS = """
CREATE TABLE IF NOT EXISTS product_interactions (
    event_id        VARCHAR PRIMARY KEY,
    user_id         VARCHAR NOT NULL,
    session_id      VARCHAR NOT NULL,
    event_type      VARCHAR NOT NULL,
    product_id      VARCHAR NOT NULL,
    product_name    VARCHAR,
    category        VARCHAR,
    price           DOUBLE,
    quantity        INTEGER,
    timestamp       TIMESTAMPTZ NOT NULL,
    inserted_at     TIMESTAMPTZ DEFAULT now()
);
"""

DDL_SALES_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS sales_transactions (
    event_id        VARCHAR PRIMARY KEY,
    order_id        VARCHAR NOT NULL,
    user_id         VARCHAR NOT NULL,
    session_id      VARCHAR NOT NULL,
    product_id      VARCHAR NOT NULL,
    product_name    VARCHAR,
    category        VARCHAR,
    price           DOUBLE NOT NULL,
    quantity        INTEGER NOT NULL,
    total_amount    DOUBLE NOT NULL,
    payment_method  VARCHAR,
    timestamp       TIMESTAMPTZ NOT NULL,
    inserted_at     TIMESTAMPTZ DEFAULT now()
);
"""


class DataWarehouse:
    """
    Thin wrapper around a DuckDB connection that provides schema management
    and row-level upsert helpers.

    Args:
        db_path: Path to the DuckDB file.  Use ``":memory:"`` for testing.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        self._create_tables()

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------

    def _create_tables(self) -> None:
        for ddl in (DDL_USER_ACTIVITY, DDL_PRODUCT_INTERACTIONS, DDL_SALES_TRANSACTIONS):
            self.conn.execute(ddl)
        logger.debug("Warehouse tables created / verified.")

    # ------------------------------------------------------------------
    # Insert helpers
    # ------------------------------------------------------------------

    def insert_user_activity(self, row: dict[str, Any]) -> None:
        """Insert (or ignore duplicate) a user-activity row."""
        self.conn.execute(
            """
            INSERT OR IGNORE INTO user_activity
                (event_id, user_id, session_id, event_type, device, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                row["event_id"],
                row["user_id"],
                row["session_id"],
                row["event_type"],
                row.get("device"),
                row["timestamp"],
            ],
        )

    def insert_product_interaction(self, row: dict[str, Any]) -> None:
        """Insert (or ignore duplicate) a product-interaction row."""
        self.conn.execute(
            """
            INSERT OR IGNORE INTO product_interactions
                (event_id, user_id, session_id, event_type,
                 product_id, product_name, category, price, quantity, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                row["event_id"],
                row["user_id"],
                row["session_id"],
                row["event_type"],
                row["product_id"],
                row.get("product_name"),
                row.get("category"),
                row.get("price"),
                row.get("quantity"),
                row["timestamp"],
            ],
        )

    def insert_sales_transaction(self, row: dict[str, Any]) -> None:
        """Insert (or ignore duplicate) a sales-transaction row."""
        self.conn.execute(
            """
            INSERT OR IGNORE INTO sales_transactions
                (event_id, order_id, user_id, session_id,
                 product_id, product_name, category,
                 price, quantity, total_amount, payment_method, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                row["event_id"],
                row["order_id"],
                row["user_id"],
                row["session_id"],
                row["product_id"],
                row.get("product_name"),
                row.get("category"),
                row.get("price"),
                row.get("quantity"),
                row.get("total_amount"),
                row.get("payment_method"),
                row["timestamp"],
            ],
        )

    # ------------------------------------------------------------------
    # Analytics queries
    # ------------------------------------------------------------------

    def most_viewed_products(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return the most-viewed products."""
        rows = self.conn.execute(
            """
            SELECT product_id, product_name, category,
                   COUNT(*) AS view_count
            FROM   product_interactions
            WHERE  event_type = 'product_view'
            GROUP  BY product_id, product_name, category
            ORDER  BY view_count DESC
            LIMIT  ?
            """,
            [limit],
        ).fetchall()
        cols = ["product_id", "product_name", "category", "view_count"]
        return [dict(zip(cols, r)) for r in rows]

    def top_selling_products(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return the top-selling products by total units sold."""
        rows = self.conn.execute(
            """
            SELECT product_id, product_name, category,
                   SUM(quantity)     AS units_sold,
                   SUM(total_amount) AS total_revenue
            FROM   sales_transactions
            GROUP  BY product_id, product_name, category
            ORDER  BY units_sold DESC
            LIMIT  ?
            """,
            [limit],
        ).fetchall()
        cols = ["product_id", "product_name", "category", "units_sold", "total_revenue"]
        return [dict(zip(cols, r)) for r in rows]

    def conversion_rate(self) -> float:
        """
        Return the ratio of purchase sessions to total sessions.

        Conversion rate = unique sessions with a purchase / total unique sessions.
        """
        result = self.conn.execute(
            """
            WITH all_sessions AS (
                SELECT DISTINCT session_id FROM user_activity
                UNION
                SELECT DISTINCT session_id FROM product_interactions
                UNION
                SELECT DISTINCT session_id FROM sales_transactions
            ),
            purchase_sessions AS (
                SELECT DISTINCT session_id FROM sales_transactions
            )
            SELECT
                COUNT(DISTINCT ps.session_id) AS purchases,
                COUNT(DISTINCT s.session_id)  AS total
            FROM   all_sessions s
            LEFT JOIN purchase_sessions ps USING (session_id)
            """
        ).fetchone()
        purchases, total = result if result else (0, 0)
        return round(purchases / total, 4) if total else 0.0

    def revenue_by_category(self) -> list[dict[str, Any]]:
        """Return total revenue grouped by product category."""
        rows = self.conn.execute(
            """
            SELECT category,
                   SUM(total_amount)    AS total_revenue,
                   COUNT(*)             AS transaction_count
            FROM   sales_transactions
            GROUP  BY category
            ORDER  BY total_revenue DESC
            """
        ).fetchall()
        cols = ["category", "total_revenue", "transaction_count"]
        return [dict(zip(cols, r)) for r in rows]

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying DuckDB connection."""
        self.conn.close()

    def __enter__(self) -> "DataWarehouse":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
