class Entity:
    _next_id = 0

    def __init__(self, entity_type=None, creation_time=0.0):
        self.id = Entity._next_id
        Entity._next_id += 1

        self.entity_type = entity_type
        self.creation_time = creation_time

        # Used while the entity is currently waiting in a queue.
        self.queue_entry_time = None

        # Accumulated over the entity's entire journey.
        #
        # An entity may visit multiple queues and servers, so these
        # represent totals rather than the time spent at one location.
        self.waiting_time = 0.0
        self.service_time = 0.0

        self.attributes = {}
        self.resources = {}

    @property
    def total_processing_time(self):
        """Alias for accumulated service time."""
        return self.service_time

    @property
    def total_waiting_time(self):
        """Alias for accumulated queue waiting time."""
        return self.waiting_time

    def add_waiting_time(self, duration):
        if duration < 0:
            raise ValueError(
                "Waiting time cannot be negative."
            )

        self.waiting_time += duration

    def add_service_time(self, duration):
        if duration < 0:
            raise ValueError(
                "Service time cannot be negative."
            )

        self.service_time += duration

    def flow_time(self, current_time):
        """Return total time since entity creation."""
        return max(
            0.0,
            current_time - self.creation_time,
        )

    def other_time(self, current_time):
        """
        Return time not accounted for by waiting or service.

        Flow time is decomposed as:

            flow = waiting + service + other
        """
        flow = self.flow_time(current_time)

        other = (
            flow
            - self.waiting_time
            - self.service_time
        )

        # Protect against tiny floating-point errors.
        if -1e-12 < other < 0:
            return 0.0

        return max(0.0, other)
    
def acquire_resource(self, resource):
    """Record that the entity acquired one resource unit."""

    self.resources[resource] = (
        self.resources.get(resource, 0) + 1
    )


def release_resource(self, resource):
    """Record that the entity released one resource unit."""

    count = self.resources.get(
        resource,
        0,
    )

    if count <= 0:
        raise RuntimeError(
            f"Entity {self.id} does not hold "
            f"resource {resource.name!r}."
        )

    if count == 1:
        del self.resources[resource]
    else:
        self.resources[resource] = count - 1

    def reset_timing(self):
        """Reset accumulated timing information."""
        self.queue_entry_time = None
        self.waiting_time = 0.0
        self.service_time = 0.0

    @classmethod
    def reset_ids(cls):
        cls._next_id = 0

    def __repr__(self):
        return (
            f"Entity("
            f"id={self.id}, "
            f"type={self.entity_type!r})"
        )