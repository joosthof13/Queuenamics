class Statistic:

    def __init__(self):
        self.count = 0
        self.total = 0.0

    def record(self, value):
        self.count += 1
        self.total += value

    @property
    def mean(self):
        if self.count == 0:
            return 0.0

        return self.total / self.count

    def reset(self):
        self.count = 0
        self.total = 0.0


class TimeWeightedStatistic:

    def __init__(self):
        self.area = 0.0
        self.last_time = 0.0
        self.current = 0.0
        self.maximum = 0.0
        self.start_time = 0.0
        self.history = [(0.0, 0.0)]

    def update(self, value, time):
        elapsed = time - self.last_time

        self.area += self.current * elapsed
        self.last_time = time
        self.current = value

        if value > self.maximum:
            self.maximum = value

        self.history.append(
            (time, value)
        )

    def mean(self, until):
        elapsed = until - self.start_time

        if elapsed <= 0:
            return 0.0

        area = self.area + self.current * (
            until - self.last_time
        )

        return area / elapsed

    def reset(self, time=0.0, current=0.0):
        self.area = 0.0
        self.last_time = time
        self.current = current
        self.maximum = current
        self.start_time = time
        self.history = [(time, current)]


class Statistics:

    def __init__(self):
        self.waiting_time = Statistic()
        self.service_time = Statistic()
        self.queue_length = TimeWeightedStatistic()

    def reset(self):
        self.waiting_time.reset()
        self.service_time.reset()
        self.queue_length.reset()