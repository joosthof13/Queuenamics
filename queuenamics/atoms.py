from queuenamics.entities import Entity
from queuenamics.disciplines import FIFO
from queuenamics.stats import Statistics
from queuenamics.routing import FirstAvailable

class Atom:

    def __init__(self, name):
        self.name = name
        self.inputs = []
        self.outputs = []
        self.model = None
        self.stats = None

    def receive(self, entity):
        raise NotImplementedError

    def send(self, entity):
        for connection in self.outputs:
            connection.send(entity)

    def reset(self):
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name!r})"


class Source(Atom):
    def __init__(self, name, arrival, entity_type=None, attributes=None):
        super().__init__(name)
        self.arrival = arrival
        self.entity_type = entity_type
        self.attributes = dict(attributes) if attributes is not None else {}
        self.active = False
        self.entities_created = 0

    def start(self):
        self.active = True
        self._schedule_next()

    def stop(self):
        self.active = False

    def generate(self):
        if not self.active:
            return

        entity = Entity(
            entity_type=self.entity_type,
            creation_time=self.model.simulation.time
        )
        entity.attributes = dict(self.attributes)

        self.entities_created += 1
        self.send(entity)
        self._schedule_next()

    def _schedule_next(self):
        if not self.active:
            return

        delay = self.arrival.sample()

        self.model.simulation.schedule(
            time=self.model.simulation.time + delay,
            action=self.generate
        )

    def reset(self):
        self.active = False
        self.entities_created = 0

    def reset_statistics(self):
        self.entities_created = 0

class Sink(Atom):

    def __init__(self, name):
        super().__init__(name)

        self.entities_received = 0
        self.entities = []

    def receive(self, entity):
        self.entities_received += 1
        self.entities.append(entity)

    @property
    def throughput(self):
        if self.model is None:
            return 0.0

        simulation_time = self.model.simulation.time

        if simulation_time <= 0:
            return 0.0

        return self.entities_received / simulation_time

    def reset_statistics(self):
        self.entities_received = 0
        self.entities.clear()

    def reset(self):
        self.entities_received = 0
        self.entities.clear()

class Queue(Atom):

    def __init__(
        self,
        name,
        capacity=None,
        discipline=None,
        router=None
    ):
        super().__init__(name)

        self.capacity = capacity
        self.discipline = discipline or FIFO()
        self.router = router or FirstAvailable()
        self.entities = []
        self.stats = Statistics()

    def receive(self, entity):
        if self.is_full():
            raise RuntimeError(
                f"Queue {self.name!r} is full"
            )

        if self.model is not None:
            entity.queue_entry_time = self.model.simulation.time
        else:
            entity.queue_entry_time = 0.0

        self.entities.append(entity)

        current_time = (
            self.model.simulation.time
            if self.model is not None
            else 0.0
        )

        # Record the state immediately after entering.
        self.stats.queue_length.update(
            self.length(),
            current_time
        )

        # Only send after the new queue state has been recorded.
        self._try_send()

    def add(self, entity):
        self.receive(entity)

    def remove(self):

        if self.is_empty():
            return None

        entity = self.discipline.select(self.entities)

        self.entities.remove(entity)

        current_time = (
            self.model.simulation.time
            if self.model is not None
            else 0.0
        )

        if entity.queue_entry_time is not None:

            waiting_time = (
                current_time
                - entity.queue_entry_time
            )

            # Queue-level waiting-time statistic.
            self.stats.waiting_time.record(
                waiting_time
            )

            # Keep the server-level statistic populated
            # for backwards compatibility.
            if self.outputs:

                connection = self.outputs[0]

                server = connection.destination

                if hasattr(server, "stats"):
                    server.stats.waiting_time.record(
                        waiting_time
                    )

            entity.queue_entry_time = None

        self.stats.queue_length.update(
            self.length(),
            current_time
        )

        return entity

    def _try_send(self):
        if self.is_empty():
            return

        connection = self.router.select(self.outputs)

        if connection is None:
            return

        entity = self.remove()

        connection.send(entity)

    def length(self):
        return len(self.entities)

    def is_empty(self):
        return len(self.entities) == 0

    def is_full(self):
        if self.capacity is None:
            return False

        return len(self.entities) >= self.capacity
    
    @property
    def average_length(self):
        if self.model is None:
            return 0.0

        return self.stats.queue_length.mean(
            self.model.simulation.time
        )


    @property
    def maximum_length(self):
        return self.stats.queue_length.maximum


    @property
    def average_waiting_time(self):
        return self.stats.waiting_time.mean
    
    def reset_statistics(self):
        current_time = (
            self.model.simulation.time
            if self.model is not None
            else 0.0
        )

        self.stats.waiting_time.reset()
        self.stats.service_time.reset()

        self.stats.queue_length.reset(
            time=current_time,
            current=self.length()
        )

    def reset(self):
        self.entities.clear()
        self.stats.reset()

class Server(Atom):

    def __init__(self, name, service, resource=None):
        super().__init__(name)

        self.service = service
        self.resource = resource

        self.current_entity = None
        self.busy = False
        self.processed = 0
        self.busy_time = 0.0
        self.service_start_time = None
        self.stats = Statistics()

    def receive(self, entity):
        if self.busy:
            raise RuntimeError(
                f"Server {self.name!r} is busy"
            )

        if self.resource is not None:
            if not self.resource.acquire():
                return False

        self.current_entity = entity
        self.busy = True

        self.service_start_time = (
            self.model.simulation.time
        )

        delay = self.service.sample()

        self.model.simulation.schedule(
            time=self.model.simulation.time + delay,
            action=self.complete
        )

        return True

    def complete(self):
        if self.current_entity is None:
            return

        entity = self.current_entity

        service_time = (
            self.model.simulation.time
            - self.service_start_time
        )

        self.stats.service_time.record(
            service_time
        )
        self.busy_time += service_time

        if self.resource is not None:
            self.resource.release()

        self.current_entity = None
        self.busy = False
        self.processed += 1

        self.send(entity)

        self._pull_from_queue()

    def _pull_from_queue(self):
        for connection in self.inputs:
            queue = connection.source

            if hasattr(queue, "_try_send"):
                queue._try_send()

                if self.busy:
                    return

    def available(self):
        return not self.busy
    
    @property
    def utilization(self):
        if self.model is None:
            return 0.0

        simulation_time = self.model.simulation.time

        if simulation_time <= 0:
            return 0.0

        busy_time = self.busy_time

        if self.busy and self.service_start_time is not None:
            busy_time += (
                simulation_time
                - self.service_start_time
            )

        return busy_time / simulation_time


    @property
    def average_service_time(self):
        return self.stats.service_time.mean
    
    def reset_statistics(self):
        self.stats.waiting_time.reset()
        self.stats.service_time.reset()

        self.busy_time = 0.0
        self.processed = 0

    def reset(self):
        self.current_entity = None
        self.busy = False
        self.processed = 0
        self.service_start_time = None
        self.busy_time = 0.0
        self.stats.reset()

class Resource(Atom):

    def __init__(self, name, capacity=1):
        super().__init__(name)

        if capacity <= 0:
            raise ValueError(
                "Resource capacity must be greater than 0."
            )

        self.capacity = capacity
        self.busy_count = 0

    def acquire(self):
        if not self.available():
            return False

        self.busy_count += 1
        return True

    def release(self):
        if self.busy_count <= 0:
            raise RuntimeError(
                f"Resource {self.name!r} has no busy units."
            )

        self.busy_count -= 1

    def available(self):
        return self.busy_count < self.capacity

    @property
    def available_capacity(self):
        return self.capacity - self.busy_count

    @property
    def utilization(self):
        if self.capacity <= 0:
            return 0.0

        return self.busy_count / self.capacity

    def receive(self, entity):
        if not self.acquire():
            raise RuntimeError(
                f"Resource {self.name!r} is full."
            )

        self.send(entity)

    def reset(self):
        self.busy_count = 0