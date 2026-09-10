class Entity:

    _next_id = 0

    def __init__(self, entity_type=None, creation_time=0.0):
        self.id = Entity._next_id
        Entity._next_id += 1

        self.entity_type = entity_type
        self.creation_time = creation_time
        self.queue_entry_time = None
        self.attributes = {}

    @classmethod
    def reset_ids(cls):
        cls._next_id = 0

    def __repr__(self):
        return f"Entity(id={self.id}, type={self.entity_type!r})"