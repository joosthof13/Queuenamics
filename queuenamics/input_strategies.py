class InputStrategy:

    @staticmethod
    def available(connection):
        source = connection.source
        return (
            hasattr(source, "pending_entity")
            and source.pending_entity is not None
        )

    def select(self, connections):
        raise NotImplementedError

    def reset(self):
        pass


class AnyInputChannel(InputStrategy):

    def select(self, connections):
        for connection in connections:
            if self.available(connection):
                return connection
        return None


class RoundRobin(InputStrategy):

    def __init__(self):
        self.index = 0

    def select(self, connections):
        if not connections:
            return None

        connection = connections[self.index % len(connections)]
        self.index = (self.index + 1) % len(connections)

        return connection

    def reset(self):
        self.index = 0


class RoundRobinWithCheck(InputStrategy):

    def __init__(self):
        self.index = 0

    def select(self, connections):
        if not connections:
            return None

        n = len(connections)

        for offset in range(n):
            index = (self.index + offset) % n
            connection = connections[index]

            if self.available(connection):
                self.index = (index + 1) % n
                return connection

        return None

    def reset(self):
        self.index = 0