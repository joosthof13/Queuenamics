from queuenamics.entities import Entity
from queuenamics.disciplines import FIFO, Discipline
from queuenamics.input_strategies import AnyInputChannel
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
            accepted = connection.send(entity)

            if accepted is False:
                return False

        return True

    def reset(self):
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name!r})"

class Source(Atom):

    def __init__(
        self,
        name,
        arrival,
        max_arrivals=None,
        entity_type=None,
        attributes=None,
        time_till_first_product=None,
    ):
        super().__init__(name)

        self.arrival = arrival
        self.max_arrivals = max_arrivals
        self.entity_type = entity_type
        self.attributes = dict(attributes) if attributes is not None else {}
        self.time_till_first_product = time_till_first_product

        self.active = False
        self.entities_created = 0
        self.pending_entity = None

    def start(self):
        if (
            self.max_arrivals is not None
            and self.entities_created >= self.max_arrivals
        ):
            return

        self.active = True

        if self.time_till_first_product is None:
            # Use the arrival distribution for the first product
            self._schedule_next()
        else:
            # Schedule the first product at the explicitly specified time
            self.model.simulation.schedule(
                time=(
                    self.model.simulation.time
                    + self.time_till_first_product
                ),
                action=self.generate,
            )

    def stop(self):
        self.active = False

    def generate(self):
        if not self.active:
            return

        # A pending entity is already waiting for Queue admission.
        if self.pending_entity is not None:
            return

        # Stop if the maximum has been reached.
        if (
            self.max_arrivals is not None
            and self.entities_created >= self.max_arrivals
        ):
            self.active = False
            return

        entity = Entity(
            entity_type=self.entity_type,
            creation_time=self.model.simulation.time,
        )

        entity.attributes = dict(self.attributes)

        self.entities_created += 1

        # A Queue controls admission of its input channels.
        if len(self.outputs) == 1:
            destination = self.outputs[0].destination

            if isinstance(destination, Queue):
                self.pending_entity = entity
                destination._notify_blocked_inputs()
                return

        # Preserve normal push behaviour for other destinations.
        accepted = self.send(entity)

        if not accepted:
            self.pending_entity = entity
            return

        # Entity was successfully sent.
        self.pending_entity = None

        # Schedule the next arrival.
        if (
            self.max_arrivals is None
            or self.entities_created < self.max_arrivals
        ):
            self._schedule_next()
        else:
            self.active = False

    def _schedule_next(self):
        if not self.active:
            return

        if (
            self.max_arrivals is not None
            and self.entities_created >= self.max_arrivals
        ):
            self.active = False
            return

        delay = self.arrival.sample()

        self.model.simulation.schedule(
            time=self.model.simulation.time + delay,
            action=self.generate,
        )

    def reset(self):
        self.active = False
        self.entities_created = 0
        self.pending_entity = None

    def reset_statistics(self):
        self.entities_created = 0

class Sink(Atom):
    def __init__(self, name):
        super().__init__(name)

        self.entities_received = 0
        self.entities = []

        self.stats = Statistics()

    def receive(self, entity):
        self.entities_received += 1
        self.entities.append(entity)

        current_time = (
            self.model.simulation.time
            if self.model is not None
            else 0.0
        )

        flow_time = entity.flow_time(current_time)
        waiting_time = entity.total_waiting_time
        service_time = entity.total_processing_time
        other_time = entity.other_time(current_time)

        self.stats.flow_time.record(
            flow_time,
            entity=entity,
        )

        self.stats.waiting_time.record(
            waiting_time,
            entity=entity,
        )

        self.stats.service_time.record(
            service_time,
            entity=entity,
        )

        self.stats.other_time.record(
            other_time,
            entity=entity,
        )

    @property
    def throughput(self):
        if self.model is None:
            return 0.0

        simulation_time = self.model.simulation.time

        if simulation_time <= 0:
            return 0.0

        return (
            self.entities_received
            / simulation_time
        )

    def completed_by(self, group="entity_type"):
        """Return completed-entity counts grouped by type/attribute."""
        return self.stats.flow_time.grouped_count(group)

    def throughput_by(self, group="entity_type"):
        """Return throughput grouped by type/attribute."""

        if (
            self.model is None
            or self.model.simulation.time <= 0
        ):
            return {
                key: 0.0
                for key in self.completed_by(group)
            }

        simulation_time = self.model.simulation.time

        return {
            key: count / simulation_time
            for key, count in self.completed_by(group).items()
        }

    def reset_statistics(self):
        self.entities_received = 0
        self.entities.clear()
        self.stats.reset()

    def reset(self):
        self.entities_received = 0
        self.entities.clear()
        self.stats.reset()


class Queue(Atom):

    VALID_OVERFLOW = {"error", "drop", "route", "block"}

    def __init__(
        self,
        name,
        capacity=None,
        discipline=None,
        router=None,
        overflow="error",
        input_strategy = None
    ):
        super().__init__(name)

        self.capacity = capacity
        self.discipline = discipline or FIFO()
        self.router = router or FirstAvailable()
        self.input_strategy = (
            input_strategy
            if input_strategy is not None
            else AnyInputChannel()
        )
        self.overflow = overflow

        if overflow not in self.VALID_OVERFLOW:
            raise ValueError(
                f"Invalid overflow policy {overflow!r}. "
                f"Choose from: {sorted(self.VALID_OVERFLOW)}"
            )

        self.entities = []
        self.overflow_outputs = []
        self.stats = Statistics()

    def _accept_from_input(self, connection):
        source = connection.source

        if not hasattr(source, "pending_entity"):
            return False

        if source.pending_entity is None:
            return False

        # Do not admit anything if the Queue itself cannot accept it.
        if self.is_full():
            return False

        entity = source.pending_entity

        # Clear the pending entity BEFORE receiving it.
        # This prevents recursive notifications from admitting
        # the same entity multiple times.
        source.pending_entity = None

        accepted = self.receive(entity)

        if not accepted:
            # Restore the entity if the Queue rejected it.
            source.pending_entity = entity
            return False

        # The source can now schedule its next arrival.
        if (
            source.active
            and (
                source.max_arrivals is None
                or source.entities_created < source.max_arrivals
            )
        ):
            source._schedule_next()

        elif (
            source.max_arrivals is not None
            and source.entities_created >= source.max_arrivals
        ):
            source.active = False

        return True

    def receive(self, entity):
        if self.is_full():
            if self.overflow == "error":
                raise RuntimeError(
                    f"Queue {self.name!r} is full"
                )

            elif self.overflow == "drop":
                return True

            elif self.overflow == "route":
                if not self.overflow_outputs:
                    raise RuntimeError(
                        f"Queue {self.name!r} is full and "
                        "has no overflow connection"
                    )

                connection = self.overflow_outputs[0]
                connection.send(entity)
                return True

            elif self.overflow == "block":
                return False

        if self.model is not None:
            entity.queue_entry_time = (
                self.model.simulation.time
            )
        else:
            entity.queue_entry_time = 0.0

        self.entities.append(entity)

        current_time = (
            self.model.simulation.time
            if self.model is not None
            else 0.0
        )

        self.stats.queue_length.update(
            self.length(),
            current_time,
        )

        self._try_send()

        return True

    def add(self, entity):
        self.receive(entity)

    def _record_waiting(self, entity, current_time):
        if entity.queue_entry_time is None:
            return

        waiting_time = (
            current_time
            - entity.queue_entry_time
        )

        self.stats.waiting_time.record(
            waiting_time,
            entity=entity,
        )

        # Accumulate this waiting period on the entity exactly once.
        entity.add_waiting_time(waiting_time)

    def remove(self):
        if self.is_empty():
            return None

        entity = self.discipline.select(
            self.entities
        )

        self.entities.remove(entity)

        current_time = (
            self.model.simulation.time
            if self.model is not None
            else 0.0
        )

        self._record_waiting(
            entity,
            current_time,
        )

        entity.queue_entry_time = None

        self.stats.queue_length.update(
            self.length(),
            current_time,
        )

        return entity

    def _try_send(self):
        if self.is_empty():
            return

        entity = self.discipline.select(
            self.entities
        )

        if entity is None:
            return

        connection = self.router.select(
            self.outputs,
            entity=entity,
        )

        if connection is None:
            return

        destination = connection.destination

        if (
            hasattr(destination, "available")
            and not destination.available()
        ):
            return

        self.entities.remove(entity)

        current_time = (
            self.model.simulation.time
            if self.model is not None
            else 0.0
        )

        self._record_waiting(
            entity,
            current_time,
        )

        self.stats.queue_length.update(
            self.length(),
            current_time,
        )

        connection.send(entity)
        self._notify_blocked_inputs()

    def _notify_blocked_inputs(self):
        connection = self.input_strategy.select(self.inputs)

        if connection is None:
            return

        self._accept_from_input(connection)

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

    @property
    def time_empty(self):
        if self.model is None:
            return 0.0

        return self.stats.queue_length.time_zero(
            self.model.simulation.time
        )

    @property
    def time_nonempty(self):
        if self.model is None:
            return 0.0

        return self.stats.queue_length.time_nonzero(
            self.model.simulation.time
        )

    @property
    def occupancy(self):
        if self.model is None:
            return 0.0

        return self.stats.queue_length.occupancy(
            self.model.simulation.time
        )

    def reset_statistics(self):
        current_time = (
            self.model.simulation.time
            if self.model is not None
            else 0.0
        )

        self.stats.waiting_time.reset()
        self.stats.service_time.reset()
        self.stats.other_time.reset()
        self.stats.flow_time.reset()

        self.stats.queue_length.reset(
            time=current_time,
            current=self.length(),
        )

    def reset(self):
        self.entities.clear()
        self.stats.reset()
        self.input_strategy.reset()


class Server(Atom):

    def __init__(
        self,
        name,
        service,
        resource=None,
        setup=None,
    ):
        super().__init__(name)

        self.service = service
        self.resource = resource
        self.setup = setup

        self.current_entity = None
        self.busy = False
        self.processed = 0

        self.busy_time = 0.0
        self.setup_time = 0.0

        self.service_start_time = None
        self.setup_start_time = None
        self.busy_start_time = None

        self.stats = Statistics()

        # Server occupancy:
        # 0 = idle
        # 1 = busy
        self.stats.server_occupancy.reset(
            time=0.0,
            current=0.0,
        )

    def receive(self, entity):

        if self.busy:
            return False

        # Acquire resource before starting setup.
        if self.resource is not None:
            if not self.resource.acquire(entity):
                return False

        current_time = self.model.simulation.time
        self.busy_start_time = current_time

        # Record queue waiting time.
        if entity.queue_entry_time is not None:

            waiting_time = (
                current_time
                - entity.queue_entry_time
            )

            self.stats.waiting_time.record(
                waiting_time,
                entity=entity,
            )

            entity.queue_entry_time = None

        self.current_entity = entity
        self.busy = True

        self.stats.server_occupancy.update(
            1.0,
            current_time,
        )

        # Setup phase
        if self.setup is not None:

            self.setup_start_time = current_time

            setup_duration = self.setup.sample()

            self.model.simulation.schedule(
                time=current_time + setup_duration,
                action=self._complete_setup,
            )

        else:

            # No setup: start service immediately.
            self._start_service(current_time)

        return True

    def _complete_setup(self):

        if self.current_entity is None:
            return

        current_time = self.model.simulation.time

        setup_duration = (
            current_time
            - self.setup_start_time
        )

        if self.setup_start_time is None:
            raise RuntimeError("Server busy start time is missing.")

        self.stats.setup_time.record(
            setup_duration,
            entity=self.current_entity,
        )

        self.setup_time += setup_duration

        self.setup_start_time = None

        self._start_service(current_time)

    def _start_service(self, current_time):

        self.service_start_time = current_time

        delay = self.service.sample()

        self.model.simulation.schedule(
            time=current_time + delay,
            action=self.complete,
        )

    def complete(self):

        if self.current_entity is None:
            return

        entity = self.current_entity
        current_time = self.model.simulation.time

        service_time = (
            current_time
            - self.service_start_time
        )

        self.stats.service_time.record(
            service_time,
            entity=entity,
        )

        # Setup time is deliberately NOT included
        # in the entity's service_time.
        entity.add_service_time(
            service_time
        )

        # Total time the server was occupied,
        # including setup + service.
        busy_duration = (
            current_time
            - self.busy_start_time
        )

        self.busy_time += busy_duration

        if self.busy_start_time is None:
            raise RuntimeError("Server busy start time is missing.")

        if self.resource is not None:
            self.resource.release(entity)

        self.current_entity = None
        self.busy = False
        self.processed += 1

        self.busy_start_time = None
        self.service_start_time = None
        self.setup_start_time = None

        self.stats.server_occupancy.update(
            0.0,
            current_time,
        )

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

        if self.busy:
            return False

        if self.resource is not None:
            return self.resource.available()

        return True

    @property
    def utilization(self):

        if self.model is None:
            return 0.0

        simulation_time = self.model.simulation.time

        if simulation_time <= 0:
            return 0.0

        return self.busy_time / simulation_time

    @property
    def busy_time_exact(self):

        if self.model is None:
            return 0.0

        return self.stats.server_occupancy.time_nonzero(
            self.model.simulation.time
        )

    @property
    def idle_time(self):

        if self.model is None:
            return 0.0

        simulation_time = self.model.simulation.time

        return max(
            0.0,
            simulation_time - self.busy_time_exact,
        )

    @property
    def busy_periods(self):

        if self.model is None:
            return []

        return self.stats.server_occupancy.periods_nonzero(
            self.model.simulation.time
        )

    @property
    def idle_periods(self):

        if self.model is None:
            return []

        return self.stats.server_occupancy.period_durations(
            lambda value: value == 0,
            self.model.simulation.time,
        )

    @property
    def number_of_busy_periods(self):
        return len(self.busy_periods)

    @property
    def average_busy_period(self):

        periods = self.busy_periods

        if not periods:
            return 0.0

        return sum(periods) / len(periods)

    @property
    def maximum_busy_period(self):

        periods = self.busy_periods

        if not periods:
            return 0.0

        return max(periods)

    @property
    def number_of_idle_periods(self):
        return len(self.idle_periods)

    @property
    def average_idle_period(self):

        periods = self.idle_periods

        if not periods:
            return 0.0

        return sum(periods) / len(periods)

    @property
    def maximum_idle_period(self):

        periods = self.idle_periods

        if not periods:
            return 0.0

        return max(periods)

    @property
    def average_service_time(self):
        return self.stats.service_time.mean

    @property
    def average_setup_time(self):
        return self.stats.setup_time.mean

    def reset_statistics(self):

        current_time = (
            self.model.simulation.time
            if self.model is not None
            else 0.0
        )

        self.stats.waiting_time.reset()
        self.stats.service_time.reset()
        self.stats.setup_time.reset()
        self.stats.flow_time.reset()

        self.busy_time = 0.0
        self.setup_time = 0.0
        self.processed = 0

        if self.busy:

            self.busy_start_time = current_time

            if self.setup_start_time is not None:
                self.setup_start_time = current_time

            if self.service_start_time is not None:
                self.service_start_time = current_time

            current_occupancy = 1.0

        else:

            self.busy_start_time = None
            self.service_start_time = None
            self.setup_start_time = None

            current_occupancy = 0.0

        self.stats.server_occupancy.reset(
            time=current_time,
            current=current_occupancy,
        )

    def reset(self):

        self.current_entity = None
        self.busy = False
        self.processed = 0

        self.service_start_time = None
        self.setup_start_time = None
        self.busy_start_time = None

        self.busy_time = 0.0
        self.setup_time = 0.0

        self.stats.reset()


class Resource(Atom):
    """
    A finite-capacity shared resource.

    Examples include machines, employees, rooms, vehicles,
    tools, or other capacity-constrained assets.
    """

    def __init__(self, name, capacity=1):
        super().__init__(name)

        if (
            isinstance(capacity, bool)
            or not isinstance(capacity, int)
        ):
            raise TypeError(
                "Resource capacity must be an integer."
            )

        if capacity <= 0:
            raise ValueError(
                "Resource capacity must be greater than 0."
            )

        self.capacity = capacity
        self.busy_count = 0

        self.stats = Statistics()

        # Number of occupied resource units over time.
        self.stats.server_occupancy.reset(
            time=0.0,
            current=0.0,
        )

        # Seize atoms waiting for this resource.
        self.waiting_seizes = []

    def acquire(self, entity=None):
        """
        Acquire one unit of the resource.

        Returns True when successful and False when the
        resource is currently full.
        """

        if not self.available():
            return False

        current_time = self._time()

        self.busy_count += 1

        self.stats.server_occupancy.update(
            self.busy_count,
            current_time,
        )

        if entity is not None:
            entity.acquire_resource(self)

        return True

    def release(self, entity=None):
        """Release one unit of the resource.

        If an entity is supplied, it must currently hold one unit of this
        resource. Releasing a resource that the entity does not hold raises
        RuntimeError.
        """
        if entity is not None and not entity.has_resource(self):
            raise RuntimeError(
                f"Entity {entity.id} does not hold resource {self.name!r}."
            )

        if self.busy_count <= 0:
            raise RuntimeError(
                f"Resource {self.name!r} has no busy units."
            )

        if entity is not None:
            entity.release_resource(self)

        self.busy_count -= 1
        current_time = self._time()

        self.stats.server_occupancy.update(
            self.busy_count,
            current_time,
        )

        self._notify_waiting()

    def available(self):
        """Return True when at least one unit is available."""
        return self.busy_count < self.capacity

    @property
    def available_capacity(self):
        """Number of currently available resource units."""
        return self.capacity - self.busy_count

    @property
    def utilization(self):
        """
        Fraction of total resource capacity utilized.

        For capacity=3, two occupied units correspond to
        a utilization of 2/3.
        """

        if self.model is None:
            return self.busy_count / self.capacity

        simulation_time = self.model.simulation.time

        if simulation_time <= 0:
            return 0.0

        return (
            self.stats.server_occupancy.mean(
                simulation_time
            )
            / self.capacity
        )

    @property
    def busy_time(self):
        """
        Total time during which at least one resource unit
        was occupied.
        """

        if self.model is None:
            return 0.0

        return self.stats.server_occupancy.time_nonzero(
            self.model.simulation.time
        )

    @property
    def idle_time(self):
        """Total time during which all resource units were idle."""

        if self.model is None:
            return 0.0

        return max(
            0.0,
            self.model.simulation.time - self.busy_time,
        )

    @property
    def average_busy(self):
        if self.model is None:
            return float(self.busy_count)
        return self.stats.server_occupancy.mean(
            self.model.simulation.time
        )

    @property
    def peak_busy(self):
        return self.stats.server_occupancy.maximum

    def receive(self, entity):
        """
        Allow Resource to be used directly as an atom.

        Normally Seize/Release should be preferred when modelling
        explicit resource acquisition and release.
        """

        if not self.acquire(entity):
            raise RuntimeError(
                f"Resource {self.name!r} is full."
            )

        self.send(entity)

    def _time(self):
        if self.model is None:
            return 0.0

        return self.model.simulation.time

    def _register_waiting(self, seize):
        if seize not in self.waiting_seizes:
            self.waiting_seizes.append(seize)

    def _unregister_waiting(self, seize):
        if seize in self.waiting_seizes:
            self.waiting_seizes.remove(seize)

    def _notify_waiting(self):
        """
        Notify waiting Seize atoms that capacity is available.
        """

        for seize in list(self.waiting_seizes):

            if not self.available():
                break

            seize._try_allocate()

    def reset_statistics(self):
        """
        Reset measurements while preserving current resource state.

        This is important for warm-up periods.
        """

        current_time = self._time()

        self.stats.server_occupancy.reset(
            time=current_time,
            current=self.busy_count,
        )

    def reset(self):
        self.busy_count = 0
        self.waiting_seizes.clear()

        self.stats.reset()

class Seize(Atom):
    """
    Acquire a Resource before continuing.

    If the resource is unavailable, entities wait inside
    the Seize atom until capacity becomes available.

    Entities are allocated in FIFO order.
    """

    def __init__(self, name, resource, discipline=None):
        super().__init__(name)

        if not isinstance(resource, Resource):
            raise TypeError(
                "resource must be a Resource instance."
            )

        if discipline is None:
            discipline = FIFO()

        if not isinstance(discipline, Discipline):
            raise TypeError(
                "discipline must be a Discipline instance."
            )

        self.resource = resource
        self.discipline = discipline
        self.entities = []

        self.stats = Statistics()
        self.stats.queue_length.reset(
            time=0.0,
            current=0.0,
        )

    def receive(self, entity):
        """
        Add an entity to the Seize queue and attempt allocation.

        Seize itself never blocks incoming entities. If the Resource
        is unavailable, the entity remains in the Seize queue.
        """
        current_time = self._time()

        # Record when the entity entered the resource wait.
        entity.seize_entry_time = current_time

        self.entities.append(entity)

        self.stats.queue_length.update(
            len(self.entities),
            current_time,
        )

        self._try_allocate()

    def _try_allocate(self):
        """
        Allocate available resource capacity to waiting entities.

        Entities are served in FIFO order. Allocation continues while
        both waiting entities and resource capacity are available.
        """

        while self.entities and self.resource.available():

            current_time = self._time()

            # Check whether the immediate destination can accept
            # the entity before acquiring the resource.
            if self.outputs:
                destination = self.outputs[0].destination

                if (
                    hasattr(destination, "available")
                    and not destination.available()
                ):
                    self.resource._register_waiting(self)
                    return

            entity = self.discipline.select(self.entities)
            self.entities.remove(entity)

            self.stats.queue_length.update(
                len(self.entities),
                current_time,
            )

            # Calculate time spent waiting in Seize.
            entry_time = getattr(
                entity,
                "seize_entry_time",
                None,
            )

            if entry_time is not None:
                waiting_time = current_time - entry_time

                self.stats.waiting_time.record(
                    waiting_time,
                    entity=entity,
                )

                entity.add_waiting_time(
                    waiting_time
                )

            entity.seize_entry_time = None

            # Acquire one unit of the resource.
            acquired = self.resource.acquire(entity)

            if not acquired:
                # Normally impossible because available() was true,
                # but keep this safe if Resource behaviour changes.
                self.entities.insert(0, entity)

                self.stats.queue_length.update(
                    len(self.entities),
                    current_time,
                )

                self.resource._register_waiting(self)
                return

            # The entity now owns one resource unit.
            self.resource._unregister_waiting(self)

            # Continue through the model.
            self.send(entity)

        # No more entities can currently be allocated.
        if self.entities:
            self.resource._register_waiting(self)
        else:
            self.resource._unregister_waiting(self)

    def available(self):
        """
        Seize itself can always accept an entity.

        If the resource is unavailable, the entity waits here.
        """
        return True

    def _time(self):
        if self.model is None:
            return 0.0

        return self.model.simulation.time

    @property
    def queue_length(self):
        return len(self.entities)

    @property
    def average_waiting_time(self):
        return self.stats.waiting_time.mean

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
    def p95_waiting_time(self):
        return self.stats.waiting_time.percentile(95)
    
    @property
    def maximum_waiting_time(self):
        return self.stats.waiting_time.maximum

    def reset_statistics(self):
        current_time = self._time()

        self.stats.waiting_time.reset()

        self.stats.queue_length.reset(
            time=current_time,
            current=len(self.entities),
        )

    def reset(self):
        self.entities.clear()

        self.resource._unregister_waiting(
            self
        )

        self.stats.reset()

class Release(Atom):
    """
    Release one unit of a Resource and continue the entity flow.
    """

    def __init__(self, name, resource):
        super().__init__(name)

        if not isinstance(resource, Resource):
            raise TypeError(
                "resource must be a Resource instance."
            )

        self.resource = resource
        self.released = 0

    def receive(self, entity):
        self.resource.release(entity)

        self.released += 1

        self.send(entity)

    def reset_statistics(self):
        self.released = 0

    def reset(self):
        self.released = 0