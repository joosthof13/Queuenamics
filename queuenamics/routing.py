class Router:
    def __init__(self):
        self.rng = None

    def set_rng(self, rng):
        self.rng = rng

    def select(self, connections):
        raise NotImplementedError


class FirstAvailable(Router):
    def select(self, connections):
        for connection in connections:
            destination = connection.destination

            if (
                hasattr(destination, "available")
                and destination.available()
            ):
                return connection

        return None


class RandomAvailable(Router):
    def select(self, connections):
        available = [
            connection
            for connection in connections
            if (
                hasattr(connection.destination, "available")
                and connection.destination.available()
            )
        ]

        if not available:
            return None

        if self.rng is None:
            raise RuntimeError(
                "RandomAvailable router is not assigned to a model."
            )

        return self.rng.choice(available)