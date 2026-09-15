import math
import random


class Distribution:
    """Base class for all Queuenamics probability distributions."""

    def __init__(self):
        # By default use Python's global random module.
        # Model simulations replace this with their seeded RNG.
        self.rng = random

    def set_rng(self, rng):
        """Set the random number generator used by this distribution."""
        if rng is None:
            raise ValueError("rng cannot be None.")

        self.rng = rng
        return self

    def sample(self):
        """Generate one random sample."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Continuous distributions
# ---------------------------------------------------------------------------


class Constant(Distribution):
    """Return the same value every time."""

    def __init__(self, value):
        super().__init__()
        self.value = value

    def sample(self):
        return self.value


class Exponential(Distribution):
    """Exponential distribution parameterized by rate."""

    def __init__(self, rate):
        super().__init__()

        if not isinstance(rate, (int, float)) or isinstance(rate, bool):
            raise TypeError("Rate must be a number.")

        if not math.isfinite(rate) or rate <= 0:
            raise ValueError("Rate must be greater than 0.")

        self.rate = rate

    def sample(self):
        return self.rng.expovariate(self.rate)


class Uniform(Distribution):
    """Continuous uniform distribution on [low, high]."""

    def __init__(self, low, high):
        super().__init__()

        if not self._is_number(low) or not self._is_number(high):
            raise TypeError("low and high must be numbers.")

        if not math.isfinite(low) or not math.isfinite(high):
            raise ValueError("low and high must be finite.")

        if low > high:
            raise ValueError(
                "low must be less than or equal to high."
            )

        self.low = low
        self.high = high

    def sample(self):
        return self.rng.uniform(self.low, self.high)

    @staticmethod
    def _is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)


class Normal(Distribution):
    """Normal (Gaussian) distribution."""

    def __init__(self, mean=0.0, std=1.0):
        super().__init__()

        self._validate_finite(mean, "Mean")

        if not self._is_number(std):
            raise TypeError("Standard deviation must be a number.")

        if not math.isfinite(std) or std <= 0:
            raise ValueError(
                "Standard deviation must be greater than 0."
            )

        self.mean = mean
        self.std = std

    def sample(self):
        return self.rng.normalvariate(self.mean, self.std)

    @staticmethod
    def _is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @staticmethod
    def _validate_finite(value, name):
        if not Normal._is_number(value):
            raise TypeError(f"{name} must be a number.")

        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite.")


class LogNormal(Distribution):
    """Log-normal distribution.

    mean and sigma refer to the parameters of the underlying normal
    distribution, not the arithmetic mean and standard deviation of
    the log-normal distribution.
    """

    def __init__(self, mean=0.0, sigma=1.0):
        super().__init__()

        if not self._is_number(mean):
            raise TypeError("Mean must be a number.")

        if not math.isfinite(mean):
            raise ValueError("Mean must be finite.")

        if not self._is_number(sigma):
            raise TypeError("Sigma must be a number.")

        if not math.isfinite(sigma) or sigma <= 0:
            raise ValueError("Sigma must be greater than 0.")

        self.mean = mean
        self.sigma = sigma

    def sample(self):
        return self.rng.lognormvariate(self.mean, self.sigma)

    @staticmethod
    def _is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)


class Triangular(Distribution):
    """Triangular distribution."""

    def __init__(self, low, high, mode=None):
        super().__init__()

        values = {
            "low": low,
            "high": high,
        }

        for name, value in values.items():
            if not self._is_number(value):
                raise TypeError(f"{name} must be a number.")

            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite.")

        if low > high:
            raise ValueError(
                "low must be less than or equal to high."
            )

        if mode is None:
            mode = (low + high) / 2

        if not self._is_number(mode):
            raise TypeError("mode must be a number.")

        if not math.isfinite(mode):
            raise ValueError("mode must be finite.")

        if mode < low or mode > high:
            raise ValueError(
                "mode must be between low and high."
            )

        self.low = low
        self.high = high
        self.mode = mode

    def sample(self):
        return self.rng.triangular(
            self.low,
            self.high,
            self.mode,
        )

    @staticmethod
    def _is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)


class Gamma(Distribution):
    """Gamma distribution parameterized by shape and scale."""

    def __init__(self, shape, scale=1.0):
        super().__init__()

        self._validate_positive(shape, "Shape")
        self._validate_positive(scale, "Scale")

        self.shape = shape
        self.scale = scale

    def sample(self):
        return self.rng.gammavariate(
            self.shape,
            self.scale,
        )

    @staticmethod
    def _validate_positive(value, name):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"{name} must be a number.")

        if not math.isfinite(value) or value <= 0:
            raise ValueError(
                f"{name} must be greater than 0."
            )


class Weibull(Distribution):
    """Weibull distribution parameterized by shape and scale."""

    def __init__(self, shape, scale=1.0):
        super().__init__()

        self._validate_positive(shape, "Shape")
        self._validate_positive(scale, "Scale")

        self.shape = shape
        self.scale = scale

    def sample(self):
        return self.rng.weibullvariate(
            self.scale,
            self.shape,
        )

    @staticmethod
    def _validate_positive(value, name):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"{name} must be a number.")

        if not math.isfinite(value) or value <= 0:
            raise ValueError(
                f"{name} must be greater than 0."
            )


class Erlang(Distribution):
    """Erlang distribution.

    Erlang is a Gamma distribution where the shape parameter is
    restricted to a positive integer.
    """

    def __init__(self, shape, rate):
        super().__init__()

        if isinstance(shape, bool) or not isinstance(shape, int):
            raise TypeError("Shape must be an integer.")

        if shape <= 0:
            raise ValueError(
                "Shape must be greater than 0."
            )

        if not isinstance(rate, (int, float)) or isinstance(rate, bool):
            raise TypeError("Rate must be a number.")

        if not math.isfinite(rate) or rate <= 0:
            raise ValueError(
                "Rate must be greater than 0."
            )

        self.shape = shape
        self.rate = rate

    def sample(self):
        return self.rng.gammavariate(
            self.shape,
            1.0 / self.rate,
        )


class Beta(Distribution):
    """Beta distribution."""

    def __init__(self, alpha, beta):
        super().__init__()

        self._validate_positive(alpha, "Alpha")
        self._validate_positive(beta, "Beta")

        self.alpha = alpha
        self.beta = beta

    def sample(self):
        return self.rng.betavariate(
            self.alpha,
            self.beta,
        )

    @staticmethod
    def _validate_positive(value, name):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"{name} must be a number.")

        if not math.isfinite(value) or value <= 0:
            raise ValueError(
                f"{name} must be greater than 0."
            )


# ---------------------------------------------------------------------------
# Discrete distributions
# ---------------------------------------------------------------------------


class DiscreteUniform(Distribution):
    """Discrete uniform distribution over integers [low, high]."""

    def __init__(self, low, high):
        super().__init__()

        if isinstance(low, bool) or not isinstance(low, int):
            raise TypeError("low must be an integer.")

        if isinstance(high, bool) or not isinstance(high, int):
            raise TypeError("high must be an integer.")

        if low > high:
            raise ValueError(
                "low must be less than or equal to high."
            )

        self.low = low
        self.high = high

    def sample(self):
        return self.rng.randint(self.low, self.high)


class Bernoulli(Distribution):
    """Bernoulli distribution returning 0 or 1."""

    def __init__(self, p):
        super().__init__()

        self._validate_probability(p)

        self.p = p

    def sample(self):
        return 1 if self.rng.random() < self.p else 0

    @staticmethod
    def _validate_probability(p):
        if not isinstance(p, (int, float)) or isinstance(p, bool):
            raise TypeError("p must be a number.")

        if not math.isfinite(p) or p < 0 or p > 1:
            raise ValueError(
                "p must be between 0 and 1."
            )


class Binomial(Distribution):
    """Binomial distribution.

    Returns the number of successes in n independent Bernoulli trials.
    """

    def __init__(self, n, p):
        super().__init__()

        if isinstance(n, bool) or not isinstance(n, int):
            raise TypeError("n must be an integer.")

        if n < 0:
            raise ValueError(
                "n must be greater than or equal to 0."
            )

        Bernoulli._validate_probability(p)

        self.n = n
        self.p = p

    def sample(self):
        if self.n == 0 or self.p == 0:
            return 0

        if self.p == 1:
            return self.n

        successes = 0

        for _ in range(self.n):
            if self.rng.random() < self.p:
                successes += 1

        return successes


class Geometric(Distribution):
    """Geometric distribution.

    Returns the number of trials required to obtain the first success.
    """

    def __init__(self, p):
        super().__init__()

        Bernoulli._validate_probability(p)

        if p == 0:
            raise ValueError(
                "p must be greater than 0 for a geometric distribution."
            )

        self.p = p

    def sample(self):
        if self.p == 1:
            return 1

        # Inverse CDF:
        #
        # P(X = k) = (1-p)^(k-1) p
        #
        # log1p/log gives better numerical behaviour for small p.
        u = self.rng.random()

        return math.floor(
            math.log1p(-u) / math.log1p(-self.p)
        ) + 1


class NegativeBinomial(Distribution):
    """Negative binomial distribution.

    Returns the number of failures before n successes.
    """

    def __init__(self, n, p):
        super().__init__()

        if isinstance(n, bool) or not isinstance(n, int):
            raise TypeError("n must be an integer.")

        if n <= 0:
            raise ValueError(
                "n must be greater than 0."
            )

        Bernoulli._validate_probability(p)

        if p == 0:
            raise ValueError(
                "p must be greater than 0."
            )

        self.n = n
        self.p = p

    def sample(self):
        if self.p == 1:
            return 0

        failures = 0

        for _ in range(self.n):
            # Number of failures before the next success.
            failures += Geometric(self.p).sample() - 1

        return failures


class Poisson(Distribution):
    """Poisson distribution parameterized by its mean/rate."""

    def __init__(self, rate):
        super().__init__()

        if not isinstance(rate, (int, float)) or isinstance(rate, bool):
            raise TypeError("Rate must be a number.")

        if not math.isfinite(rate) or rate < 0:
            raise ValueError(
                "Rate must be greater than or equal to 0."
            )

        self.rate = rate

    def sample(self):
        if self.rate == 0:
            return 0

        # Knuth's algorithm.
        #
        # This is exact, simple and works with any RNG implementing
        # random(). It is particularly suitable for the relatively
        # small event counts normally encountered in simulation models.
        limit = math.exp(-self.rate)

        count = 0
        probability = 1.0

        while probability > limit:
            count += 1
            probability *= self.rng.random()

        return count - 1


class Hypergeometric(Distribution):
    """Hypergeometric distribution.

    Population:
        Total population size.

    Successes:
        Number of successful items in the population.

    Draws:
        Number of items drawn without replacement.

    Returns the number of successes among the draws.
    """

    def __init__(self, population, successes, draws):
        super().__init__()

        self._validate_nonnegative_integer(
            population,
            "population",
        )

        self._validate_nonnegative_integer(
            successes,
            "successes",
        )

        self._validate_nonnegative_integer(
            draws,
            "draws",
        )

        if successes > population:
            raise ValueError(
                "successes cannot be greater than population."
            )

        if draws > population:
            raise ValueError(
                "draws cannot be greater than population."
            )

        self.population = population
        self.successes = successes
        self.draws = draws

    def sample(self):
        if self.draws == 0 or self.successes == 0:
            return 0

        if self.successes == self.population:
            return self.draws

        successes = self.successes
        failures = self.population - self.successes
        remaining = self.draws
        result = 0

        # Sequential sampling without replacement.
        for _ in range(self.draws):
            if remaining <= 0:
                break

            probability_success = successes / (successes + failures)

            if self.rng.random() < probability_success:
                result += 1
                successes -= 1
            else:
                failures -= 1

            remaining -= 1

        return result

    @staticmethod
    def _validate_nonnegative_integer(value, name):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer.")

        if value < 0:
            raise ValueError(
                f"{name} must be greater than or equal to 0."
            )


# ---------------------------------------------------------------------------
# Data / categorical distributions
# ---------------------------------------------------------------------------


class Empirical(Distribution):
    """Empirical distribution based on observed data.

    Samples one observation uniformly from the supplied observations.
    Sampling is with replacement.
    """

    def __init__(self, values):
        super().__init__()

        if values is None:
            raise ValueError("values cannot be None.")

        self.values = list(values)

        if not self.values:
            raise ValueError(
                "values must contain at least one observation."
            )

    def sample(self):
        return self.rng.choice(self.values)


class Choice(Distribution):
    """Choose uniformly from a collection of values."""

    def __init__(self, values):
        super().__init__()

        if values is None:
            raise ValueError("values cannot be None.")

        self.values = list(values)

        if not self.values:
            raise ValueError(
                "values must contain at least one choice."
            )

    def sample(self):
        return self.rng.choice(self.values)


class WeightedChoice(Distribution):
    """Choose from values using relative weights.

    Example:
        WeightedChoice(
            ["low", "medium", "high"],
            [0.6, 0.3, 0.1],
        )
    """

    def __init__(self, values, weights):
        super().__init__()

        if values is None:
            raise ValueError("values cannot be None.")

        if weights is None:
            raise ValueError("weights cannot be None.")

        self.values = list(values)
        self.weights = list(weights)

        if not self.values:
            raise ValueError(
                "values must contain at least one choice."
            )

        if len(self.values) != len(self.weights):
            raise ValueError(
                "values and weights must have the same length."
            )

        for weight in self.weights:
            if (
                not isinstance(weight, (int, float))
                or isinstance(weight, bool)
            ):
                raise TypeError(
                    "All weights must be numbers."
                )

            if not math.isfinite(weight):
                raise ValueError(
                    "All weights must be finite."
                )

            if weight < 0:
                raise ValueError(
                    "Weights cannot be negative."
                )

        if sum(self.weights) <= 0:
            raise ValueError(
                "At least one weight must be greater than 0."
            )

    def sample(self):
        return self.rng.choices(
            self.values,
            weights=self.weights,
            k=1,
        )[0]