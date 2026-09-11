import random

from queuenamics.simulation import Simulation
from queuenamics.atoms import Source
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
            return

        self.destination.receive(entity)

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

        Returns
        -------
        None
            For a normal single simulation.

        ReplicationResults
            When replications > 1.
        """
        if time < 0:
            raise ValueError(
                "Simulation time cannot be negative."
            )
        if warmup < 0:
            raise ValueError("Warm-up time must be non-negative.")

        if (
            not isinstance(replications, int)
            or isinstance(replications, bool)
        ):
            raise TypeError(
                "replications must be an integer."
            )

        if replications <= 0:
            raise ValueError(
                "replications must be greater than 0."
            )

        # Preserve the original single-run behavior.
        if replications == 1:
            self.replication_results = None

            self._run_single(
                time=time,
                validate=validate,
                progress=progress,
                reset=False,
                warmup=warmup,
            )

            return None

        # Validate once before starting the experiment.
        if validate:
            validation = self.validate()

            if not validation["valid"]:
                raise RuntimeError(
                    "Model validation failed:\n"
                    + "\n".join(
                        validation["errors"]
                    )
                )

        reports = []

        for replication in range(replications):
            seed = self._replication_seed(
                replication
            )

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

    def validate(self):
        errors = []
        warnings = []

        for atom in self.atoms:
            if atom.model is not self:
                errors.append(
                    f"Atom {atom.name!r} is not assigned "
                    f"to this model."
                )

            if isinstance(atom, Source):
                if not atom.outputs:
                    warnings.append(
                        f"Source {atom.name!r} has no outputs."
                    )

            if atom.__class__.__name__ == "Sink":
                if not atom.inputs:
                    warnings.append(
                        f"Sink {atom.name!r} has no inputs."
                    )

            if atom.__class__.__name__ == "Queue":
                if (
                    atom.capacity is not None
                    and atom.capacity <= 0
                ):
                    errors.append(
                        f"Queue {atom.name!r} has invalid capacity."
                    )

            if atom.__class__.__name__ == "Server":
                if atom.service is None:
                    errors.append(
                        f"Server {atom.name!r} has no service "
                        f"distribution."
                    )

        for connection in self.connections:
            if connection.source not in self.atoms:
                errors.append(
                    f"Connection source "
                    f"{connection.source.name!r} "
                    f"is not registered in the model."
                )

            if connection.destination not in self.atoms:
                errors.append(
                    f"Connection destination "
                    f"{connection.destination.name!r} "
                    f"is not registered in the model."
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }