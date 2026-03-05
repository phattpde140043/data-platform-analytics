"""Tests for the streaming layer (queue + producer)."""

import threading
import time

from src.streaming.queue import LocalQueue
from src.streaming.producer import EventProducer
from src.simulator.event_generator import EVENT_TYPES


class TestLocalQueue:
    def test_publish_and_consume(self):
        q = LocalQueue()
        q.publish("test-topic", {"event_id": "1", "event_type": "user_login"})
        msg = q.consume("test-topic", timeout=1.0)
        assert msg is not None
        assert msg["event_id"] == "1"

    def test_consume_returns_none_when_empty(self):
        q = LocalQueue()
        msg = q.consume("empty-topic", timeout=0.01)
        assert msg is None

    def test_consume_all_drains_queue(self):
        q = LocalQueue()
        for i in range(5):
            q.publish("topic", {"event_id": str(i)})
        messages = q.consume_all("topic")
        assert len(messages) == 5
        assert q.size("topic") == 0

    def test_size(self):
        q = LocalQueue()
        assert q.size("t") == 0
        q.publish("t", {"x": 1})
        q.publish("t", {"x": 2})
        assert q.size("t") == 2

    def test_multiple_topics(self):
        q = LocalQueue()
        q.publish("a", {"n": 1})
        q.publish("b", {"n": 2})
        assert q.size("a") == 1
        assert q.size("b") == 1
        assert set(q.topics()) == {"a", "b"}

    def test_topics_returns_known_topics(self):
        q = LocalQueue()
        q.publish("alpha", {})
        q.publish("beta", {})
        topics = q.topics()
        assert "alpha" in topics
        assert "beta" in topics


class TestEventProducer:
    def test_producer_publishes_events(self):
        q = LocalQueue()
        producer = EventProducer(queue=q, events_per_second=200, num_users=10)
        producer.start()
        time.sleep(0.2)
        producer.stop(timeout=2.0)
        assert q.size("ecommerce-events") > 0

    def test_producer_stop(self):
        q = LocalQueue()
        producer = EventProducer(queue=q, events_per_second=200, num_users=10)
        producer.start()
        assert producer.is_running()
        producer.stop(timeout=2.0)
        assert not producer.is_running()

    def test_published_count_increments(self):
        q = LocalQueue()
        producer = EventProducer(queue=q, events_per_second=500, num_users=5)
        producer.start()
        time.sleep(0.1)
        producer.stop(timeout=2.0)
        assert producer.published_count > 0

    def test_events_are_valid(self):
        q = LocalQueue()
        producer = EventProducer(queue=q, events_per_second=500, num_users=5)
        producer.start()
        time.sleep(0.1)
        producer.stop(timeout=2.0)
        events = q.consume_all("ecommerce-events")
        for event in events:
            assert event["event_type"] in EVENT_TYPES
