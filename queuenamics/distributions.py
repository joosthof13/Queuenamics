import random


class Distribution:

    def __init__(self):
        self.rng = random

    def set_rng(self, rng):
        self.rng = rng

    def sample(self):
        raise NotImplementedError


class Constant(Distribution):

    def __init__(self, value):
        super().__init__()
        self.value = value

    def sample(self):
        return self.value


class Exponential(Distribution):

    def __init__(self, rate):
        super().__init__()

        if rate <= 0:
            raise ValueError("Rate must be greater than 0.")

        self.rate = rate

    def sample(self):
        return self.rng.expovariate(self.rate)


class Uniform(Distribution):

    def __init__(self, low, high):
        super().__init__()

        if low > high:
            raise ValueError(
                "low must be less than or equal to high."
            )

        self.low = low
        self.high = high

    def sample(self):
        return self.rng.uniform(
            self.low,
            self.high
        )


class Poisson(Distribution):

    def __init__(self, rate):
        super().__init__()

        if rate < 0:
            raise ValueError(
                "Rate must be greater than or equal to 0."
            )

        self.rate = rate

    def sample(self):
        if self.rate == 0:
            return 0

        limit = 2.718281828459045 ** (-self.rate)

        count = 0
        probability = 1.0

        while probability > limit:
            count += 1
            probability *= self.rng.random()

        return count - 1