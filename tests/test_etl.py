"""Tests for the ETL pipeline."""

import pytest

from src.streaming.queue import LocalQueue
from src.warehouse.schema import DataWarehouse
from src.etl.pipeline import ETLPipeline
from src.simulator.event_generator import EventGenerator


@pytest.fixture
def setup():
    q = LocalQueue()
    wh = DataWarehouse(db_path=":memory:")
    pipeline = ETLPipeline(queue=q, warehouse=wh)
    yield q, wh, pipeline
    wh.close()


def _seed_queue(queue, n: int = 20, topic: str = "ecommerce-events"):
    gen = EventGenerator(num_users=10)
    for _ in range(n):
        event = gen.generate_event()
        queue.publish(topic, event)


class TestETLPipeline:
    def test_process_batch_returns_count(self, setup):
        q, wh, pipeline = setup
        _seed_queue(q, n=10)
        processed = pipeline.process_batch()
        assert processed >= 10

    def test_user_activity_populated(self, setup):
        q, wh, pipeline = setup
        _seed_queue(q, n=50)
        pipeline.process_batch()
        count = wh.conn.execute("SELECT COUNT(*) FROM user_activity").fetchone()[0]
        assert count > 0

    def test_product_interactions_populated(self, setup):
        q, wh, pipeline = setup
        _seed_queue(q, n=50)
        pipeline.process_batch()
        count = wh.conn.execute("SELECT COUNT(*) FROM product_interactions").fetchone()[0]
        assert count > 0

    def test_sales_transactions_populated(self, setup):
        """With enough events, at least one checkout_purchase should land."""
        q, wh, pipeline = setup
        gen = EventGenerator(num_users=5)
        for _ in range(100):
            event = gen.generate_event(event_type="checkout_purchase")
            q.publish("ecommerce-events", event)
        pipeline.process_batch()
        count = wh.conn.execute("SELECT COUNT(*) FROM sales_transactions").fetchone()[0]
        assert count == 100

    def test_error_count_stays_zero_for_valid_events(self, setup):
        q, wh, pipeline = setup
        _seed_queue(q, n=30)
        pipeline.process_batch()
        assert pipeline.error_count == 0

    def test_idempotent_reprocessing(self, setup):
        """Re-processing the same events should not duplicate rows."""
        q, wh, pipeline = setup
        gen = EventGenerator(num_users=5)
        event = gen.generate_event(event_type="user_login")
        q.publish("ecommerce-events", event)
        q.publish("ecommerce-events", event)  # duplicate
        pipeline.process_batch()
        count = wh.conn.execute("SELECT COUNT(*) FROM user_activity").fetchone()[0]
        assert count == 1
