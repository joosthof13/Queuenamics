class Router:
    def __init__(self):
        self.rng = None

    def set_rng(self, rng):
        self.rng = rng

    def select(self, connections):
        raise NotImplementedError


class FirstAvailable(Router):
    def select(self, connections, entity=None):
        for connection in connections:
            destination = connection.destination

            if (
                hasattr(destination, "available")
                and destination.available()
            ):
                return connection

        return None


class RandomAvailable(Router):
    def select(self, connections, entity=None):
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
    
class EntityTypeRouter(Router):
    """Route entities based on their entity_type."""

    def __init__(self, routes, default=None):
        super().__init__()
        self.routes = dict(routes)
        self.default = default

    def select(self, connections, entity=None):
        if not connections:
            return None

        if entity is None:
            raise ValueError(
                "EntityTypeRouter requires an entity."
            )

        index = self.routes.get(
            entity.entity_type,
            self.default,
        )

        if index is None:
            return None

        if not 0 <= index < len(connections):
            raise IndexError(
                f"EntityTypeRouter selected connection index "
                f"{index}, but only {len(connections)} connections exist."
            )

        return connections[index]


class AttributeRouter(Router):
    """Route entities based on an entity attribute."""

    def __init__(self, attribute, routes, default=None):
        super().__init__()
        self.attribute = attribute
        self.routes = dict(routes)
        self.default = default

    def select(self, connections, entity=None):
        if not connections:
            return None

        if entity is None:
            raise ValueError(
                "AttributeRouter requires an entity."
            )

        value = entity.attributes.get(self.attribute)

        index = self.routes.get(
            value,
            self.default,
        )

        if index is None:
            return None

        if not 0 <= index < len(connections):
            raise IndexError(
                f"AttributeRouter selected connection index "
                f"{index}, but only {len(connections)} connections exist."
            )

        return connections[index]


class ConditionalRouter(Router):
    """Route entities using user-defined conditions."""

    def __init__(self, conditions, default=None):
        super().__init__()
        self.conditions = list(conditions)
        self.default = default

    def select(self, connections, entity=None):
        if not connections:
            return None

        if entity is None:
            raise ValueError(
                "ConditionalRouter requires an entity."
            )

        for condition, index in self.conditions:
            if condition(entity):
                if not 0 <= index < len(connections):
                    raise IndexError(
                        f"ConditionalRouter selected connection index "
                        f"{index}, but only {len(connections)} "
                        f"connections exist."
                    )
                return connections[index]

        if self.default is None:
            return None

        if not 0 <= self.default < len(connections):
            raise IndexError(
                f"ConditionalRouter selected connection index "
                f"{self.default}, but only {len(connections)} "
                f"connections exist."
            )

        return connections[self.default]