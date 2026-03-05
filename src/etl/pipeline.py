"""
ETL pipeline: consumes raw events from the queue and loads them into
the data warehouse.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ETLPipeline:
    """
    Extract-Transform-Load pipeline.

    Reads raw events from a :class:`LocalQueue`, applies lightweight
    transformations, and writes to the three analytics tables in the
    :class:`DataWarehouse`.

    Usage::

        pipeline = ETLPipeline(queue=queue, warehouse=dw)
        pipeline.process_batch()          # drain the queue once
    """

    def __init__(self, queue: Any, warehouse: Any, topic: str = "ecommerce-events") -> None:
        self.queue = queue
        self.warehouse = warehouse
        self.topic = topic
        self._processed = 0
        self._errors = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_batch(self, max_events: int = 500) -> int:
        """
        Consume up to *max_events* from the queue and write to the warehouse.

        Returns:
            Number of events successfully processed.
        """
        events = self.queue.consume_all(self.topic)
        if max_events:
            events = events[:max_events]
        for event in events:
            self._process_event(event)
        return self._processed

    def run_continuous(self, poll_interval: float = 1.0, stop_event: Any = None) -> None:
        """
        Continuously consume from the queue until *stop_event* is set.

        Args:
            poll_interval: Seconds to sleep between polls when the queue is empty.
            stop_event:    A :class:`threading.Event`; loop exits when set.
        """
        import time

        logger.info("ETLPipeline running in continuous mode.")
        while stop_event is None or not stop_event.is_set():
            message = self.queue.consume(self.topic, timeout=poll_interval)
            if message:
                self._process_event(message)

    @property
    def processed_count(self) -> int:
        return self._processed

    @property
    def error_count(self) -> int:
        return self._errors

    # ------------------------------------------------------------------
    # Transform + Load
    # ------------------------------------------------------------------

    def _process_event(self, event: dict[str, Any]) -> None:
        try:
            event_type = event.get("event_type", "")
            if event_type == "user_login":
                self._load_user_activity(event)
            elif event_type == "product_view":
                self._load_product_interaction(event)
                self._load_user_activity(event)
            elif event_type == "product_search":
                self._load_user_activity(event)
            elif event_type == "add_to_cart":
                self._load_product_interaction(event)
                self._load_user_activity(event)
            elif event_type == "checkout_purchase":
                self._load_sales_transaction(event)
                self._load_product_interaction(event)
                self._load_user_activity(event)
            else:
                logger.warning("Unknown event type: %s", event_type)
            self._processed += 1
        except Exception:  # noqa: BLE001
            logger.exception("Error processing event %s", event.get("event_id"))
            self._errors += 1

    def _load_user_activity(self, event: dict[str, Any]) -> None:
        self.warehouse.insert_user_activity(event)

    def _load_product_interaction(self, event: dict[str, Any]) -> None:
        self.warehouse.insert_product_interaction(event)

    def _load_sales_transaction(self, event: dict[str, Any]) -> None:
        self.warehouse.insert_sales_transaction(event)
