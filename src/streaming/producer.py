"""
Event producer for the streaming layer.

Continuously polls the simulator and publishes events into the queue.
The producer is designed to be run in a background thread or process.
"""

import logging
import threading
import time
from typing import Any

from src.simulator.event_generator import EventGenerator

logger = logging.getLogger(__name__)


class EventProducer:
    """
    Drives the EventGenerator and publishes events to a LocalQueue.

    The producer runs in its own daemon thread so the host process can
    continue doing other work (e.g. running the ETL pipeline).

    Usage::

        queue = LocalQueue()
        producer = EventProducer(queue=queue, events_per_second=20)
        producer.start()
        # ... do other work ...
        producer.stop()
    """

    def __init__(
        self,
        queue: Any,
        events_per_second: float = 10.0,
        num_users: int = 1000,
        topic: str = "ecommerce-events",
    ) -> None:
        self.queue = queue
        self.events_per_second = max(events_per_second, 0.001)
        self.topic = topic
        self._generator = EventGenerator(num_users=num_users)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._published = 0

    # ------------------------------------------------------------------
    # Thread control
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the producer in a background daemon thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Producer is already running.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._produce_loop, daemon=True)
        self._thread.start()
        logger.info("EventProducer started (%.1f eps, topic=%s).", self.events_per_second, self.topic)

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the producer to stop and wait for it to finish."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        logger.info("EventProducer stopped after publishing %d events.", self._published)

    def is_running(self) -> bool:
        """Return *True* if the producer thread is alive."""
        return bool(self._thread and self._thread.is_alive())

    @property
    def published_count(self) -> int:
        """Total events published since the producer started."""
        return self._published

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    def _produce_loop(self) -> None:
        interval = 1.0 / self.events_per_second
        while not self._stop_event.is_set():
            event = self._generator.generate_event()
            self.queue.publish(self.topic, event)
            self._published += 1
            time.sleep(interval)
