import random


class Discipline:

    def select(self, entities):
        raise NotImplementedError


class FIFO(Discipline):

    def select(self, entities):
        if not entities:
            return None

        return entities[0]


class LIFO(Discipline):

    def select(self, entities):
        if not entities:
            return None

        return entities[-1]


class Random(Discipline):

    def select(self, entities):
        if not entities:
            return None

        return random.choice(entities)


class Priority(Discipline):

    def __init__(self, attribute="priority", highest_first=True):
        self.attribute = attribute
        self.highest_first = highest_first

    def select(self, entities):
        if not entities:
            return None

        if self.highest_first:
            return max(
                entities,
                key=lambda entity:
                    entity.attributes.get(self.attribute, 0)
            )

        return min(
            entities,
            key=lambda entity:
                entity.attributes.get(self.attribute, 0)
        )


class ShortestProcessingTime(Discipline):

    def __init__(self, attribute="service_time"):
        self.attribute = attribute

    def select(self, entities):
        if not entities:
            return None

        return min(
            entities,
            key=lambda entity:
                entity.attributes.get(self.attribute, float("inf"))
        )