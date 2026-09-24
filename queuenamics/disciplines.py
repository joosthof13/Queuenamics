class Discipline:
    def __init__(self):
        self.rng = None

    def set_rng(self, rng):
        self.rng = rng

    def select(self, entities):
        raise NotImplementedError


class FIFO(Discipline):
    def select(self, entities):
        return entities[0] if entities else None


class LIFO(Discipline):
    def select(self, entities):
        return entities[-1] if entities else None


class Random(Discipline):
    def select(self, entities):
        if not entities:
            return None

        if self.rng is None:
            raise RuntimeError(
                "Random discipline is not assigned to a model."
            )

        return self.rng.choice(entities)


class Priority(Discipline):
    def __init__(self, attribute="priority", highest_first=True):
        super().__init__()
        self.attribute = attribute
        self.highest_first = highest_first

    def select(self, entities):
        if not entities:
            return None

        if self.highest_first:
            return max(
                entities,
                key=lambda entity: entity.attributes.get(
                    self.attribute, 0
                ),
            )

        return min(
            entities,
            key=lambda entity: entity.attributes.get(
                self.attribute, 0
            ),
        )


class ShortestProcessingTime(Discipline):
    def __init__(self, attribute="service_time"):
        super().__init__()
        self.attribute = attribute

    def select(self, entities):
        if not entities:
            return None

        return min(
            entities,
            key=lambda entity: entity.attributes.get(
                self.attribute, float("inf")
            ),
        )
    
class LongestProcessingTime(Discipline):

    def __init__(self, attribute="service_time"):
        super().__init__()
        self.attribute = attribute

    def select(self, entities):
        if not entities:
            return None

        return max(
            entities,
            key=lambda entity: entity.attributes.get(
                self.attribute, 0
            ),
        )