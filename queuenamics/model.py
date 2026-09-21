import random
import math

from queuenamics.simulation import Simulation
from queuenamics.atoms import (
    Atom,
    Source,
    Sink,
    Queue,
    Server,
    Resource,
    Seize,
    Release,
)
from queuenamics.routing import (
    Router,
    FirstAvailable,
    RandomAvailable,
    EntityTypeRouter,
    AttributeRouter,
    ConditionalRouter,
)
from queuenamics.disciplines import Discipline
from queuenamics.distributions import Distribution
from queuenamics.entities import Entity
from queuenamics.report import StatisticsReport
from queuenamics.stats import ReplicationResults


class Connection:
    def __init__(self, source, destination):
        self.source = source
        self.destination = destination
        self.enabled = True

    def send(self, entity):
        if not self.enabled:
            return True

        result = self.destination.receive(entity)

        if result is False:
            return False

        return True

    def __repr__(self):
        return (
            f"Connection("
            f"{self.source.name!r} -> "
            f"{self.destination.name!r})"
        )


class Model:
    def __init__(self, seed=None):
        self.atoms = []
        self.connections = []
        self.resources = []

        self.simulation = Simulation()

        # Keep the original seed so that replications can derive
        # independent deterministic seeds from it.
        self.seed = seed
        self.rng = random.Random(seed)

        self.stats = StatisticsReport(self)

        # Filled after model.run(..., replications=n).
        self.replication_results = None
        self.warmup = 0.0
        self.observation_time = 0.0
        self.observation_start = 0.0

    def connect(self, source, destination):
        self._register_atom(source)
        self._register_atom(destination)

        connection = Connection(
            source,
            destination,
        )

        source.outputs.append(connection)
        destination.inputs.append(connection)

        self.connections.append(connection)

        return connection
    
    def connect_overflow(self, source, destination):
        if not hasattr(source, "overflow_outputs"):
            raise TypeError(
                f"Atom {source.name!r} does not support overflow connections."
            )

        self._register_atom(source)
        self._register_atom(destination)

        connection = Connection(source, destination)

        source.overflow_outputs.append(connection)
        destination.inputs.append(connection)
        self.connections.append(connection)

        return connection

    def _register_atom(self, atom):
        if atom not in self.atoms:
            self.atoms.append(atom)

        atom.model = self

        self._bind_rng(atom)

    def _bind_rng(self, atom):
        """
        Bind the model RNG to all stochastic components of an atom.

        This is separated from _register_atom so that replications can
        replace the RNG without rebuilding the model topology.
        """
        if (
            hasattr(atom, "arrival")
            and hasattr(atom.arrival, "set_rng")
        ):
            atom.arrival.set_rng(self.rng)

        if (
            hasattr(atom, "service")
            and hasattr(atom.service, "set_rng")
        ):
            atom.service.set_rng(self.rng)

        if (
            hasattr(atom, "discipline")
            and hasattr(atom.discipline, "set_rng")
        ):
            atom.discipline.set_rng(self.rng)

        if (
            hasattr(atom, "router")
            and hasattr(atom.router, "set_rng")
        ):
            atom.router.set_rng(self.rng)

    def _set_rng(self, rng):
        """Replace the model RNG and propagate it to all atoms."""
        self.rng = rng

        for atom in self.atoms:
            self._bind_rng(atom)

    def _prepare_run(self):
        """
        Prepare the model for a clean simulation run.

        This is primarily used by replication mode.
        """
        self.simulation.reset()

        for atom in self.atoms:
            atom.reset()

        Entity.reset_ids()

    def _start_sources(self):
        for atom in self.atoms:
            if isinstance(atom, Source) and not atom.active:
                atom.start()

    def add_resource(self, resource):
        if resource not in self.resources:
            self.resources.append(resource)
            resource.model = self

    def _run_single(
        self,
        time,
        validate=True,
        progress=True,
        reset=False,
        warmup=0,
    ):
        """
        Execute one simulation.

        The `time` argument is the observation period.
        If warmup > 0, the model first runs for the warm-up
        period, then statistics are reset without resetting
        the simulation state.
        """

        if validate:
            validation = self.validate()
            if not validation["valid"]:
                raise RuntimeError(
                    "Model validation failed:\n"
                    + "\n".join(validation["errors"])
                )

        if reset:
            self._prepare_run()

        self.warmup = warmup
        self.observation_time = time
        self.observation_start = warmup

        self._start_sources()

        # -------------------------
        # Warm-up period
        # -------------------------

        if warmup > 0:
            self.simulation.run(
                until=warmup,
                progress=progress,
            )

            # Reset measurement statistics only.
            # The simulation state itself is preserved.
            self.reset_statistics()

        # -------------------------
        # Observation period
        # -------------------------

        self.simulation.run(
            until=warmup + time,
            progress=progress,
        )

    def _replication_seed(self, replication_index):
        """
        Return the seed for a replication.

        With seed=42, replications use:

            42, 43, 44, ...

        This makes replication experiments reproducible while keeping
        each replication statistically independent.

        If no base seed was supplied, a fresh system-random seed is
        generated for each replication.
        """
        if self.seed is not None:
            return self.seed + replication_index

        return random.SystemRandom().randrange(
            0,
            2**63,
        )

    def run(
        self,
        time,
        validate=True,
        progress=True,
        replications=1,
        warmup=0,
    ):
        """
        Run the simulation.

        Parameters
        ----------
        time:
            Simulation end time.
        validate:
            Validate the model before running.
        progress:
            Display the simulation progress bar.
        replications:
            Number of independent replications.
        warmup:
            Warm-up period before collecting statistics.

        Returns
        -------
        None
            For a normal single simulation.

        ReplicationResults
            When replications > 1.
        """

        # Always validate run parameters.
        validation = self.validate(
            time=time,
            warmup=warmup,
            replications=replications,
        )

        if not validation["valid"]:
            if validate:
                raise RuntimeError(
                    "Model validation failed:\n"
                    + "\n".join(validation["errors"])
                )

            parameter_errors = [
                error
                for error in validation["errors"]
                if (
                    "Simulation time" in error
                    or "Warmup time" in error
                    or "Replications" in error
                )
            ]

            if parameter_errors:
                raise ValueError(
                    "Invalid run parameters:\n"
                    + "\n".join(parameter_errors)
                )

        # Preserve the original single-run behavior.
        if replications == 1:
            self.replication_results = None

            self._run_single(
                time=time,
                validate=False,
                progress=progress,
                reset=False,
                warmup=warmup,
            )

            return None

        # Validate the model once before starting the experiment.
        if validate:
            # The validation above already happened.
            pass

        reports = []

        for replication in range(replications):
            seed = self._replication_seed(replication)

            # Every replication gets its own independent RNG stream.
            self._set_rng(
                random.Random(seed)
            )

            # Completely reset the model state.
            self._prepare_run()

            # Run warm-up + observation period.
            self._run_single(
                time=time,
                validate=False,
                progress=progress,
                reset=False,
                warmup=warmup,
            )

            # Capture only observation-period statistics.
            reports.append(
                self.stats.report()
            )

        self.replication_results = ReplicationResults(
            reports
        )

        return self.replication_results

    def reset_statistics(self):
        for atom in self.atoms:
            if hasattr(atom, "reset_statistics"):
                atom.reset_statistics()

    def reset(self):
        self.simulation.reset()

        for atom in self.atoms:
            atom.reset()

        self.replication_results = None

    def validate(self, time=None, warmup=None, replications=None):
        """
        Validate the model structure and configuration.

        Returns
        -------
        dict
            A dictionary containing:

            - valid: True if no errors were found
            - errors: Blocking validation errors
            - warnings: Non-blocking potential problems
            - info: Informational messages
        """

        errors = []
        warnings = []
        info = []

        def error(message):
            errors.append(f"ERROR: {message}")

        def warning(message):
            warnings.append(f"WARNING: {message}")

        def information(message):
            info.append(f"INFO: {message}")

        # ---------------------------------------------------------
        # Model-level validation
        # ---------------------------------------------------------
        if not self.atoms:
            warning(
                "Model contains no atoms. "
                "Add at least a Source, processing atom, and Sink."
            )

        if not self.resources and any(
            isinstance(atom, (Server, Seize, Release))
            and getattr(atom, "resource", None) is not None
            for atom in self.atoms
        ):
            error(
                "One or more atoms reference resources, but the model "
                "contains no registered resources."
            )

        # ---------------------------------------------------------
        # Atom names
        # ---------------------------------------------------------
        names = {}

        for atom in self.atoms:
            if not isinstance(atom.name, str) or not atom.name.strip():
                error(
                    f"Atom {atom!r} has an invalid name. "
                    "Atom names must be non-empty strings."
                )
                continue

            if atom.name in names:
                error(
                    f"Duplicate atom name {atom.name!r}. "
                    "Every atom in a model must have a unique name."
                )
            else:
                names[atom.name] = atom

        # ---------------------------------------------------------
        # Atom registration / ownership
        # ---------------------------------------------------------
        for atom in self.atoms:
            if not isinstance(atom, Atom):
                error(
                    f"Object {atom!r} is registered as an atom but is not "
                    "an instance of Atom."
                )
                continue

            if atom.model is not self:
                error(
                    f"Atom {atom.name!r} is not assigned to this model. "
                    "Register it using model.connect(), or assign it to "
                    "this model through the normal model API."
                )

        # ---------------------------------------------------------
        # Connections
        # ---------------------------------------------------------
        for connection in self.connections:

            if not isinstance(
                connection,
                type(self.connections[0])
            ) if self.connections else False:
                error(
                    "Model contains an invalid connection object."
                )
                continue

            source = connection.source
            destination = connection.destination

            if source not in self.atoms:
                error(
                    f"Connection source "
                    f"{getattr(source, 'name', source)!r} "
                    "is not registered in the model."
                )

            if destination not in self.atoms:
                error(
                    f"Connection destination "
                    f"{getattr(destination, 'name', destination)!r} "
                    "is not registered in the model."
                )

            if source in self.atoms and connection not in source.outputs:

                # Overflow connections deliberately do not belong
                # to the normal outputs list.
                if connection not in getattr(
                    source,
                    "overflow_outputs",
                    [],
                ):
                    error(
                        f"Connection from {source.name!r} to "
                        f"{destination.name!r} is registered in the model "
                        "but is missing from the source's connection list."
                    )

            if (
                destination in self.atoms
                and connection not in destination.inputs
            ):
                error(
                    f"Connection from {source.name!r} to "
                    f"{destination.name!r} is registered in the model "
                    "but is missing from the destination's input list."
                )

            if source is destination:
                warning(
                    f"Atom {source.name!r} has a self-connection. "
                    "Cycles are allowed, but verify that this is intentional."
                )

        # ---------------------------------------------------------
        # Atom-specific validation
        # ---------------------------------------------------------
        for atom in self.atoms:

            # -----------------------------------------------------
            # Source
            # -----------------------------------------------------
            if isinstance(atom, Source):

                if atom.arrival is None:
                    error(
                        f"Source {atom.name!r} has no arrival distribution. "
                        "Assign a Distribution to Source.arrival."
                    )

                elif not isinstance(atom.arrival, Distribution):
                    error(
                        f"Source {atom.name!r} has an invalid arrival "
                        f"distribution: {type(atom.arrival).__name__}. "
                        "arrival must be a Distribution."
                    )

                if atom.time_till_first_product is not None:

                    if (
                        not isinstance(
                            atom.time_till_first_product,
                            (int, float),
                        )
                        or isinstance(
                            atom.time_till_first_product,
                            bool,
                        )
                    ):
                        error(
                            f"Source {atom.name!r} has an invalid "
                            "time_till_first_product. "
                            "It must be a non-negative number."
                        )

                    elif atom.time_till_first_product < 0:
                        error(
                            f"Source {atom.name!r} has a negative "
                            "time_till_first_product. "
                            "It must be >= 0."
                        )

                if atom.max_arrivals is not None:

                    if (
                        isinstance(atom.max_arrivals, bool)
                        or not isinstance(atom.max_arrivals, int)
                    ):
                        error(
                            f"Source {atom.name!r} has an invalid "
                            "max_arrivals value. "
                            "It must be a positive integer or None."
                        )

                    elif atom.max_arrivals <= 0:
                        error(
                            f"Source {atom.name!r} has max_arrivals <= 0. "
                            "Use None for unlimited arrivals or a positive "
                            "integer."
                        )

                if not atom.outputs:
                    warning(
                        f"Source {atom.name!r} has no output connections. "
                        "Generated entities cannot enter the model."
                    )

            # -----------------------------------------------------
            # Sink
            # -----------------------------------------------------
            elif isinstance(atom, Sink):

                if not atom.inputs:
                    warning(
                        f"Sink {atom.name!r} has no input connections. "
                        "No entities can reach this sink."
                    )

            # -----------------------------------------------------
            # Queue
            # -----------------------------------------------------
            elif isinstance(atom, Queue):

                if atom.capacity is not None:

                    if (
                        isinstance(atom.capacity, bool)
                        or not isinstance(atom.capacity, int)
                    ):
                        error(
                            f"Queue {atom.name!r} has an invalid capacity. "
                            "Capacity must be a positive integer or None."
                        )

                    elif atom.capacity <= 0:
                        error(
                            f"Queue {atom.name!r} has invalid capacity "
                            f"{atom.capacity}. "
                            "Capacity must be greater than 0."
                        )

                if atom.overflow not in Queue.VALID_OVERFLOW:
                    error(
                        f"Queue {atom.name!r} has invalid overflow policy "
                        f"{atom.overflow!r}. "
                        f"Choose from {sorted(Queue.VALID_OVERFLOW)}."
                    )

                if not isinstance(atom.discipline, Discipline):
                    error(
                        f"Queue {atom.name!r} has an invalid discipline. "
                        "discipline must be a Discipline instance."
                    )

                if not isinstance(atom.router, Router):
                    error(
                        f"Queue {atom.name!r} has an invalid router. "
                        "router must be a Router instance."
                    )

                if atom.overflow == "route":

                    if not atom.overflow_outputs:
                        error(
                            f"Queue {atom.name!r} uses "
                            "overflow='route' but has no overflow "
                            "connection. "
                            "Use model.connect_overflow(queue, destination)."
                        )

                    elif len(atom.overflow_outputs) > 1:
                        warning(
                            f"Queue {atom.name!r} has multiple overflow "
                            "connections, but the current implementation "
                            "uses only the first one."
                        )

                if not atom.outputs:
                    warning(
                        f"Queue {atom.name!r} has no output connections. "
                        "Entities may accumulate in this queue."
                    )

                # Validate normal router connection references.
                for connection in atom.outputs:

                    if connection.source is not atom:
                        error(
                            f"Queue {atom.name!r} has an output connection "
                            "whose source is not the queue itself."
                        )

            # -----------------------------------------------------
            # Server
            # -----------------------------------------------------
            elif isinstance(atom, Server):

                if atom.service is None:
                    error(
                        f"Server {atom.name!r} has no service distribution. "
                        "Assign a Distribution to Server.service."
                    )

                elif not isinstance(atom.service, Distribution):
                    error(
                        f"Server {atom.name!r} has an invalid service "
                        f"distribution: {type(atom.service).__name__}. "
                        "service must be a Distribution."
                    )

                if getattr(atom, "setup", None) is not None:

                    if not isinstance(atom.setup, Distribution):
                        error(
                            f"Server {atom.name!r} has an invalid setup "
                            "distribution. setup must be a Distribution "
                            "or None."
                        )

                if getattr(atom, "resource", None) is not None:

                    resource = atom.resource

                    if not isinstance(resource, Resource):
                        error(
                            f"Server {atom.name!r} references an invalid "
                            "resource. resource must be a Resource."
                        )

                    elif resource not in self.resources:
                        error(
                            f"Server {atom.name!r} references resource "
                            f"{resource.name!r}, but that resource is not "
                            "registered in the model. "
                            "Add it with model.add_resource()."
                        )

                if not atom.outputs:
                    warning(
                        f"Server {atom.name!r} has no output connections. "
                        "Completed entities cannot continue through the model."
                    )

            # -----------------------------------------------------
            # Resource-dependent atoms
            # -----------------------------------------------------
            elif isinstance(atom, Seize):

                resource = getattr(atom, "resource", None)

                if not isinstance(resource, Resource):
                    error(
                        f"Seize {atom.name!r} does not reference a valid "
                        "Resource."
                    )

                elif resource not in self.resources:
                    error(
                        f"Seize {atom.name!r} references resource "
                        f"{resource.name!r}, but it is not registered in "
                        "the model. Add it with model.add_resource()."
                    )

                if not atom.outputs:
                    warning(
                        f"Seize {atom.name!r} has no output connections."
                    )

            elif isinstance(atom, Release):

                resource = getattr(atom, "resource", None)

                if not isinstance(resource, Resource):
                    error(
                        f"Release {atom.name!r} does not reference a valid "
                        "Resource."
                    )

                elif resource not in self.resources:
                    error(
                        f"Release {atom.name!r} references resource "
                        f"{resource.name!r}, but it is not registered in "
                        "the model. Add it with model.add_resource()."
                    )

                if not atom.outputs:
                    warning(
                        f"Release {atom.name!r} has no output connections."
                    )

        # ---------------------------------------------------------
        # Resources
        # ---------------------------------------------------------
        for resource in self.resources:

            if not isinstance(resource, Resource):
                error(
                    f"Object {resource!r} is registered as a resource but "
                    "is not a Resource instance."
                )
                continue

            if resource.model is not self:
                error(
                    f"Resource {resource.name!r} is not assigned to this "
                    "model."
                )

            capacity = resource.capacity

            if (
                isinstance(capacity, bool)
                or not isinstance(capacity, int)
            ):
                error(
                    f"Resource {resource.name!r} has an invalid capacity. "
                    "Capacity must be a positive integer."
                )

            elif capacity <= 0:
                error(
                    f"Resource {resource.name!r} has invalid capacity "
                    f"{capacity}. Capacity must be greater than 0."
                )

        # ---------------------------------------------------------
        # Router-specific validation
        # ---------------------------------------------------------
        for atom in self.atoms:

            if not isinstance(atom, Queue):
                continue

            router = atom.router
            connections = atom.outputs

            if not isinstance(router, Router):
                continue

            if isinstance(
                router,
                (
                    EntityTypeRouter,
                    AttributeRouter,
                    ConditionalRouter,
                ),
            ):

                route_indices = []

                if isinstance(router, EntityTypeRouter):

                    route_indices.extend(
                        router.routes.values()
                    )

                    if router.default is not None:
                        route_indices.append(router.default)

                elif isinstance(router, AttributeRouter):

                    route_indices.extend(
                        router.routes.values()
                    )

                    if router.default is not None:
                        route_indices.append(router.default)

                elif isinstance(router, ConditionalRouter):

                    for _, index in router.conditions:
                        route_indices.append(index)

                    if router.default is not None:
                        route_indices.append(router.default)

                for index in route_indices:

                    if (
                        isinstance(index, bool)
                        or not isinstance(index, int)
                    ):
                        error(
                            f"Router on Queue {atom.name!r} contains "
                            f"invalid route index {index!r}. "
                            "Route indices must be integers."
                        )

                    elif index < 0 or index >= len(connections):
                        error(
                            f"Router on Queue {atom.name!r} references "
                            f"connection index {index}, but the queue has "
                            f"{len(connections)} output connection(s). "
                            "Add the required connection or correct the "
                            "route index."
                        )

            if isinstance(router, ConditionalRouter):

                for condition, index in router.conditions:

                    if not callable(condition):
                        error(
                            f"ConditionalRouter on Queue {atom.name!r} "
                            "contains a condition that is not callable."
                        )

        # ---------------------------------------------------------
        # Distribution validation
        # ---------------------------------------------------------
        for atom in self.atoms:

            distributions = []

            if isinstance(atom, Source):
                distributions.append(
                    ("arrival", getattr(atom, "arrival", None))
                )

            if isinstance(atom, Server):

                distributions.append(
                    ("service", getattr(atom, "service", None))
                )

                if getattr(atom, "setup", None) is not None:
                    distributions.append(
                        ("setup", atom.setup)
                    )

            for name, distribution in distributions:

                if distribution is None:
                    continue

                if not isinstance(distribution, Distribution):
                    # Already reported above.
                    continue

                if not callable(
                    getattr(distribution, "sample", None)
                ):
                    error(
                        f"{atom.__class__.__name__} {atom.name!r} has "
                        f"distribution {name!r} without a usable sample() "
                        "method."
                    )

                if getattr(distribution, "rng", None) is None:
                    error(
                        f"{atom.__class__.__name__} {atom.name!r}'s "
                        f"{name} distribution has no random number generator."
                    )

        # ---------------------------------------------------------
        # Connectivity information
        # ---------------------------------------------------------
        sources = [
            atom
            for atom in self.atoms
            if isinstance(atom, Source)
        ]

        sinks = [
            atom
            for atom in self.atoms
            if isinstance(atom, Sink)
        ]

        if not sources:
            warning(
                "Model contains no Source atoms. "
                "No entities will be generated."
            )

        if not sinks:
            warning(
                "Model contains no Sink atoms. "
                "Entities may never have a defined completion point."
            )

        # ---------------------------------------------------------
        # Reachability from Sources
        # ---------------------------------------------------------
        reachable = set()
        stack = list(sources)

        while stack:

            atom = stack.pop()

            if atom in reachable:
                continue

            reachable.add(atom)

            # Normal connections.
            for connection in atom.outputs:

                if not connection.enabled:
                    continue

                destination = connection.destination

                if destination not in reachable:
                    stack.append(destination)

            # Overflow connections.
            for connection in getattr(
                atom,
                "overflow_outputs",
                [],
            ):

                if not connection.enabled:
                    continue

                destination = connection.destination

                if destination not in reachable:
                    stack.append(destination)

        # Every non-Source atom must be reachable from a Source.
        for atom in self.atoms:

            if isinstance(atom, Source):
                continue

            if atom not in reachable:
                error(
                    f"{atom.__class__.__name__} {atom.name!r} "
                    "is not reachable from any Source."
                )

        # ---------------------------------------------------------
        # Source → Sink reachability
        # ---------------------------------------------------------
        for source in sources:

            reachable_from_source = set()
            stack = [source]

            while stack:

                atom = stack.pop()

                if atom in reachable_from_source:
                    continue

                reachable_from_source.add(atom)

                for connection in atom.outputs:

                    if not connection.enabled:
                        continue

                    destination = connection.destination

                    if destination not in reachable_from_source:
                        stack.append(destination)

                for connection in getattr(
                    atom,
                    "overflow_outputs",
                    [],
                ):

                    if not connection.enabled:
                        continue

                    destination = connection.destination

                    if destination not in reachable_from_source:
                        stack.append(destination)

            if not any(
                sink in reachable_from_source
                for sink in sinks
            ):
                error(
                    f"Source {source.name!r} cannot reach any Sink."
                )

        information(
            f"Model contains {len(self.atoms)} atom(s), "
            f"{len(self.connections)} connection(s), "
            f"{len(self.resources)} resource(s), "
            f"{len(sources)} source(s), and "
            f"{len(sinks)} sink(s)."
        )

        # ---------------------------------------------------------
        # Run parameters
        # ---------------------------------------------------------
        if time is not None:

            if (
                isinstance(time, bool)
                or not isinstance(time, (int, float))
            ):
                error(
                    "Simulation time must be a number."
                )

            elif not math.isfinite(time):
                error(
                    "Simulation time must be finite."
                )

            elif time < 0:
                error(
                    f"Simulation time cannot be negative: {time}."
                )

        if warmup is not None:

            if (
                isinstance(warmup, bool)
                or not isinstance(warmup, (int, float))
            ):
                error(
                    "Warmup time must be a number."
                )

            elif not math.isfinite(warmup):
                error(
                    "Warmup time must be finite."
                )

            elif warmup < 0:
                error(
                    f"Warmup time cannot be negative: {warmup}."
                )

        if replications is not None:

            if (
                isinstance(replications, bool)
                or not isinstance(replications, int)
            ):
                error(
                    "Replications must be a positive integer."
                )

            elif replications <= 0:
                error(
                    f"Replications must be greater than 0: "
                    f"{replications}."
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "info": info,
        }