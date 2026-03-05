"""
Event generator for e-commerce traffic simulation.

Generates realistic user activity events with configurable distributions.
"""

import random
import uuid
from datetime import datetime, timezone
from typing import Any

PRODUCT_CATALOG: list[dict[str, Any]] = [
    {"product_id": "P001", "name": "Wireless Headphones", "category": "Electronics", "price": 79.99},
    {"product_id": "P002", "name": "Running Shoes", "category": "Footwear", "price": 129.99},
    {"product_id": "P003", "name": "Coffee Maker", "category": "Kitchen", "price": 49.99},
    {"product_id": "P004", "name": "Yoga Mat", "category": "Sports", "price": 34.99},
    {"product_id": "P005", "name": "Smart Watch", "category": "Electronics", "price": 199.99},
    {"product_id": "P006", "name": "Backpack", "category": "Bags", "price": 59.99},
    {"product_id": "P007", "name": "Sunglasses", "category": "Accessories", "price": 89.99},
    {"product_id": "P008", "name": "Blender", "category": "Kitchen", "price": 69.99},
    {"product_id": "P009", "name": "Sneakers", "category": "Footwear", "price": 89.99},
    {"product_id": "P010", "name": "Laptop Stand", "category": "Electronics", "price": 44.99},
]

SEARCH_QUERIES: list[str] = [
    "wireless headphones", "running shoes", "coffee maker", "yoga mat",
    "smart watch", "backpack", "sunglasses", "blender", "sneakers",
    "laptop stand", "bluetooth speaker", "water bottle", "phone case",
]

EVENT_TYPES: list[str] = [
    "user_login",
    "product_view",
    "product_search",
    "add_to_cart",
    "checkout_purchase",
]

EVENT_WEIGHTS: list[float] = [0.10, 0.40, 0.25, 0.15, 0.10]


class EventGenerator:
    """Generates synthetic e-commerce user activity events."""

    def __init__(self, num_users: int = 1000) -> None:
        """
        Initialise the event generator.

        Args:
            num_users: Size of the simulated user pool.
        """
        self.num_users = num_users
        self._user_pool: list[str] = [f"U{str(i).zfill(6)}" for i in range(1, num_users + 1)]

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def random_user_id(self) -> str:
        """Return a random user identifier from the pool."""
        return random.choice(self._user_pool)

    def random_product(self) -> dict[str, Any]:
        """Return a random product from the catalogue."""
        return random.choice(PRODUCT_CATALOG)

    def random_event_type(self) -> str:
        """Return a weighted-random event type."""
        return random.choices(EVENT_TYPES, weights=EVENT_WEIGHTS, k=1)[0]

    # ------------------------------------------------------------------
    # Event factories
    # ------------------------------------------------------------------

    def _base_event(self, event_type: str, user_id: str, session_id: str) -> dict[str, Any]:
        return {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

    def generate_user_login(self, user_id: str | None = None, session_id: str | None = None) -> dict[str, Any]:
        """Generate a *user_login* event."""
        user_id = user_id or self.random_user_id()
        session_id = session_id or str(uuid.uuid4())
        event = self._base_event("user_login", user_id, session_id)
        event["device"] = random.choice(["mobile", "desktop", "tablet"])
        return event

    def generate_product_view(self, user_id: str | None = None, session_id: str | None = None) -> dict[str, Any]:
        """Generate a *product_view* event."""
        user_id = user_id or self.random_user_id()
        session_id = session_id or str(uuid.uuid4())
        product = self.random_product()
        event = self._base_event("product_view", user_id, session_id)
        event.update({
            "product_id": product["product_id"],
            "product_name": product["name"],
            "category": product["category"],
            "price": product["price"],
        })
        return event

    def generate_product_search(self, user_id: str | None = None, session_id: str | None = None) -> dict[str, Any]:
        """Generate a *product_search* event."""
        user_id = user_id or self.random_user_id()
        session_id = session_id or str(uuid.uuid4())
        event = self._base_event("product_search", user_id, session_id)
        event["query"] = random.choice(SEARCH_QUERIES)
        event["results_count"] = random.randint(0, 50)
        return event

    def generate_add_to_cart(self, user_id: str | None = None, session_id: str | None = None) -> dict[str, Any]:
        """Generate an *add_to_cart* event."""
        user_id = user_id or self.random_user_id()
        session_id = session_id or str(uuid.uuid4())
        product = self.random_product()
        event = self._base_event("add_to_cart", user_id, session_id)
        event.update({
            "product_id": product["product_id"],
            "product_name": product["name"],
            "category": product["category"],
            "price": product["price"],
            "quantity": random.randint(1, 5),
        })
        return event

    def generate_checkout_purchase(
        self, user_id: str | None = None, session_id: str | None = None
    ) -> dict[str, Any]:
        """Generate a *checkout_purchase* event."""
        user_id = user_id or self.random_user_id()
        session_id = session_id or str(uuid.uuid4())
        product = self.random_product()
        quantity = random.randint(1, 3)
        event = self._base_event("checkout_purchase", user_id, session_id)
        event.update({
            "product_id": product["product_id"],
            "product_name": product["name"],
            "category": product["category"],
            "price": product["price"],
            "quantity": quantity,
            "total_amount": round(product["price"] * quantity, 2),
            "order_id": str(uuid.uuid4()),
            "payment_method": random.choice(["credit_card", "paypal", "debit_card"]),
        })
        return event

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def generate_event(
        self,
        event_type: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate a single event.

        Args:
            event_type: Explicit event type; if *None* one is chosen at random.
            user_id:    User identifier; defaults to a random pool member.
            session_id: Session identifier; defaults to a new UUID.

        Returns:
            A dict representing the event payload.
        """
        event_type = event_type or self.random_event_type()
        factories = {
            "user_login": self.generate_user_login,
            "product_view": self.generate_product_view,
            "product_search": self.generate_product_search,
            "add_to_cart": self.generate_add_to_cart,
            "checkout_purchase": self.generate_checkout_purchase,
        }
        factory = factories.get(event_type)
        if factory is None:
            raise ValueError(f"Unknown event type: {event_type!r}")
        return factory(user_id=user_id, session_id=session_id)
