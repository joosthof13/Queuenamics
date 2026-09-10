import random


class Router:

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

        return random.choice(available)