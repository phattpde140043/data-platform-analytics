"""
GraphQL API exposing e-commerce analytics metrics.

Built with Strawberry (schema-first, type-safe GraphQL for Python).
Run with:  uvicorn src.api.graphql_api:app --reload
"""

from __future__ import annotations

import logging
import os
from typing import Annotated

import strawberry
from strawberry.fastapi import GraphQLRouter
from fastapi import FastAPI

from src.warehouse.schema import DataWarehouse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared warehouse singleton (configurable via env var)
# ---------------------------------------------------------------------------

_warehouse: DataWarehouse | None = None


def get_warehouse() -> DataWarehouse:
    global _warehouse  # noqa: PLW0603
    if _warehouse is None:
        db_path = os.environ.get("WAREHOUSE_DB_PATH", "warehouse.duckdb")
        _warehouse = DataWarehouse(db_path=db_path)
        logger.info("Opened warehouse at '%s'.", db_path)
    return _warehouse


# ---------------------------------------------------------------------------
# Strawberry types
# ---------------------------------------------------------------------------


@strawberry.type
class ProductView:
    product_id: str
    product_name: str
    category: str
    view_count: int


@strawberry.type
class ProductSales:
    product_id: str
    product_name: str
    category: str
    units_sold: int
    total_revenue: float


@strawberry.type
class ConversionRate:
    rate: float


@strawberry.type
class CategoryRevenue:
    category: str
    total_revenue: float
    transaction_count: int


# ---------------------------------------------------------------------------
# Query resolver
# ---------------------------------------------------------------------------


@strawberry.type
class Query:
    @strawberry.field(description="Return the most viewed products.")
    def most_viewed_products(self, limit: int = 10) -> list[ProductView]:
        wh = get_warehouse()
        return [ProductView(**row) for row in wh.most_viewed_products(limit=limit)]

    @strawberry.field(description="Return the top selling products by units sold.")
    def top_selling_products(self, limit: int = 10) -> list[ProductSales]:
        wh = get_warehouse()
        return [ProductSales(**row) for row in wh.top_selling_products(limit=limit)]

    @strawberry.field(description="Return the overall session conversion rate.")
    def conversion_rate(self) -> ConversionRate:
        wh = get_warehouse()
        return ConversionRate(rate=wh.conversion_rate())

    @strawberry.field(description="Return total revenue broken down by product category.")
    def revenue_by_category(self) -> list[CategoryRevenue]:
        wh = get_warehouse()
        return [CategoryRevenue(**row) for row in wh.revenue_by_category()]


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

schema = strawberry.Schema(query=Query)


def create_app(warehouse: DataWarehouse | None = None) -> FastAPI:
    """
    Factory that creates and returns the FastAPI application.

    Args:
        warehouse: Optional pre-configured :class:`DataWarehouse` instance.
                   Useful for testing (e.g. pass an in-memory warehouse).
    """
    global _warehouse  # noqa: PLW0603
    if warehouse is not None:
        _warehouse = warehouse

    app = FastAPI(title="E-Commerce Analytics API", version="1.0.0")
    graphql_app = GraphQLRouter(schema)
    app.include_router(graphql_app, prefix="/graphql")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
