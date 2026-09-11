from queuenamics.simulation import Simulation
from queuenamics.atoms import Source
from queuenamics.report import StatisticsReport
import random

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

        self.rng = random.Random(seed)

        self.stats = StatisticsReport(self)

    def connect(self, source, destination):
        self._register_atom(source)
        self._register_atom(destination)

        connection = Connection(
            source,
            destination
        )

        source.outputs.append(connection)
        destination.inputs.append(connection)

        self.connections.append(connection)

        return connection

    def _register_atom(self, atom):
        if atom not in self.atoms:
            self.atoms.append(atom)

        atom.model = self

        if hasattr(atom, "arrival") and hasattr(atom.arrival, "set_rng"):
            atom.arrival.set_rng(self.rng)

        if hasattr(atom, "service") and hasattr(atom.service, "set_rng"):
            atom.service.set_rng(self.rng)

        if hasattr(atom, "discipline") and hasattr(atom.discipline, "set_rng"):
            atom.discipline.set_rng(self.rng)

        if hasattr(atom, "router") and hasattr(atom.router, "set_rng"):
            atom.router.set_rng(self.rng)

    def run(self, time, validate=True, progress=True):

        if validate:
            validation = self.validate()

            if not validation["valid"]:
                raise RuntimeError(
                    "Model validation failed:\n"
                    + "\n".join(
                        validation["errors"]
                    )
                )

        for atom in self.atoms:
            if isinstance(atom, Source) and not atom.active:
                atom.start()

        self.simulation.run(
            until=time,
            progress=progress
        )

    def reset_statistics(self):
        for atom in self.atoms:
            if hasattr(atom, "reset_statistics"):
                atom.reset_statistics()

    def reset(self):
        self.simulation.reset()

        for atom in self.atoms:
            atom.reset()

    def validate(self):

        errors = []
        warnings = []

        for atom in self.atoms:

            if atom.model is not self:
                errors.append(
                    f"Atom {atom.name!r} is not assigned to this model."
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
                if atom.capacity is not None and atom.capacity <= 0:
                    errors.append(
                        f"Queue {atom.name!r} has invalid capacity."
                    )

            if atom.__class__.__name__ == "Server":
                if atom.service is None:
                    errors.append(
                        f"Server {atom.name!r} has no service distribution."
                    )

        for connection in self.connections:

            if connection.source not in self.atoms:
                errors.append(
                    f"Connection source {connection.source.name!r} "
                    f"is not registered in the model."
                )

            if connection.destination not in self.atoms:
                errors.append(
                    f"Connection destination {connection.destination.name!r} "
                    f"is not registered in the model."
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }