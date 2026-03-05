"""
Traffic simulator for the e-commerce data platform.

Drives the EventGenerator and pushes events into a queue at a
configurable rate.
"""

import logging
import time
from typing import Any

from .event_generator import EventGenerator

logger = logging.getLogger(__name__)


class Simulator:
    """
    Simulates e-commerce user activity by continuously generating events.

    Usage::

        queue = LocalQueue()
        sim = Simulator(queue=queue, events_per_second=10)
        sim.run(total_events=1000)
    """

    def __init__(
        self,
        queue: Any,
        events_per_second: float = 10.0,
        num_users: int = 1000,
    ) -> None:
        """
        Initialise the simulator.

        Args:
            queue:              A queue-like object with a ``publish(topic, event)`` method.
            events_per_second:  Target throughput.
            num_users:          Size of the simulated user pool.
        """
        self.queue = queue
        self.events_per_second = max(events_per_second, 0.001)
        self.generator = EventGenerator(num_users=num_users)
        self._sleep_interval: float = 1.0 / self.events_per_second

    def run(self, total_events: int = 100, topic: str = "ecommerce-events") -> int:
        """
        Generate and publish *total_events* events.

        Args:
            total_events: How many events to emit.
            topic:        Message-queue topic name.

        Returns:
            Number of events actually published.
        """
        published = 0
        for _ in range(total_events):
            event = self.generator.generate_event()
            self.queue.publish(topic, event)
            published += 1
            logger.debug("Published %s event %s", event["event_type"], event["event_id"])
            time.sleep(self._sleep_interval)
        logger.info("Simulator finished: %d events published.", published)
        return published

    def run_burst(self, total_events: int = 100, topic: str = "ecommerce-events") -> int:
        """
        Publish *total_events* as fast as possible (no sleep).

        Useful for testing and seeding the warehouse.

        Returns:
            Number of events actually published.
        """
        published = 0
        for _ in range(total_events):
            event = self.generator.generate_event()
            self.queue.publish(topic, event)
            published += 1
        logger.info("Burst mode finished: %d events published.", published)
        return published
