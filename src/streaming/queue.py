"""
Local in-process queue abstraction.

Provides the same interface that a real Kafka client would expose so the
rest of the pipeline can swap implementations without code changes.
"""

import logging
import queue
from typing import Any

logger = logging.getLogger(__name__)


class LocalQueue:
    """
    Thread-safe, in-process message queue.

    Mimics the *publish / subscribe* contract used by Kafka consumers and
    producers so that the rest of the pipeline is decoupled from the
    underlying transport.
    """

    def __init__(self, maxsize: int = 0) -> None:
        """
        Args:
            maxsize: Maximum number of messages to buffer (0 = unlimited).
        """
        self._queues: dict[str, queue.Queue] = {}
        self._maxsize = maxsize

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_create(self, topic: str) -> "queue.Queue[dict[str, Any]]":
        if topic not in self._queues:
            self._queues[topic] = queue.Queue(maxsize=self._maxsize)
        return self._queues[topic]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def publish(self, topic: str, message: dict[str, Any]) -> None:
        """
        Publish a message to *topic*.

        Args:
            topic:   Topic / channel name.
            message: Arbitrary JSON-serialisable dict.
        """
        q = self._get_or_create(topic)
        q.put_nowait(message)
        logger.debug("Published to '%s': %s", topic, message.get("event_id"))

    def consume(self, topic: str, timeout: float = 0.1) -> dict[str, Any] | None:
        """
        Consume the next message from *topic*.

        Args:
            topic:   Topic / channel name.
            timeout: How long (seconds) to wait for a message.

        Returns:
            The next message dict, or *None* if the queue is empty.
        """
        q = self._get_or_create(topic)
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            return None

    def consume_all(self, topic: str) -> list[dict[str, Any]]:
        """
        Drain all currently available messages from *topic*.

        Returns:
            List of message dicts (may be empty).
        """
        q = self._get_or_create(topic)
        messages: list[dict[str, Any]] = []
        while True:
            try:
                messages.append(q.get_nowait())
            except queue.Empty:
                break
        return messages

    def size(self, topic: str) -> int:
        """Return the number of messages currently buffered for *topic*."""
        if topic not in self._queues:
            return 0
        return self._queues[topic].qsize()

    def topics(self) -> list[str]:
        """Return all known topic names."""
        return list(self._queues.keys())
