"""Tests for the traffic simulator module."""

import pytest

from src.simulator.event_generator import EventGenerator, EVENT_TYPES
from src.simulator.simulator import Simulator
from src.streaming.queue import LocalQueue


class TestEventGenerator:
    def setup_method(self):
        self.gen = EventGenerator(num_users=100)

    def test_user_pool_size(self):
        assert len(self.gen._user_pool) == 100

    def test_generate_user_login(self):
        event = self.gen.generate_user_login()
        assert event["event_type"] == "user_login"
        assert "user_id" in event
        assert "session_id" in event
        assert "timestamp" in event
        assert "device" in event
        assert event["device"] in ("mobile", "desktop", "tablet")

    def test_generate_product_view(self):
        event = self.gen.generate_product_view()
        assert event["event_type"] == "product_view"
        assert "product_id" in event
        assert "category" in event
        assert "price" in event
        assert isinstance(event["price"], float)

    def test_generate_product_search(self):
        event = self.gen.generate_product_search()
        assert event["event_type"] == "product_search"
        assert "query" in event
        assert isinstance(event["results_count"], int)
        assert event["results_count"] >= 0

    def test_generate_add_to_cart(self):
        event = self.gen.generate_add_to_cart()
        assert event["event_type"] == "add_to_cart"
        assert "product_id" in event
        assert isinstance(event["quantity"], int)
        assert event["quantity"] >= 1

    def test_generate_checkout_purchase(self):
        event = self.gen.generate_checkout_purchase()
        assert event["event_type"] == "checkout_purchase"
        assert "order_id" in event
        assert "total_amount" in event
        assert event["total_amount"] > 0
        assert "payment_method" in event

    def test_generate_event_random(self):
        """generate_event() without arguments must produce a valid event."""
        event = self.gen.generate_event()
        assert event["event_type"] in EVENT_TYPES
        assert "event_id" in event

    def test_generate_event_explicit_type(self):
        for event_type in EVENT_TYPES:
            event = self.gen.generate_event(event_type=event_type)
            assert event["event_type"] == event_type

    def test_generate_event_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown event type"):
            self.gen.generate_event(event_type="unknown_event")

    def test_explicit_user_id_is_preserved(self):
        event = self.gen.generate_event(user_id="U999999")
        assert event["user_id"] == "U999999"

    def test_explicit_session_id_is_preserved(self):
        session = "test-session-id"
        event = self.gen.generate_event(session_id=session)
        assert event["session_id"] == session


class TestSimulator:
    def test_run_burst(self):
        q = LocalQueue()
        sim = Simulator(queue=q, events_per_second=1000, num_users=10)
        published = sim.run_burst(total_events=50)
        assert published == 50
        assert q.size("ecommerce-events") == 50

    def test_published_events_are_valid(self):
        q = LocalQueue()
        sim = Simulator(queue=q, num_users=10)
        sim.run_burst(total_events=20)
        events = q.consume_all("ecommerce-events")
        assert len(events) == 20
        for e in events:
            assert e["event_type"] in EVENT_TYPES
