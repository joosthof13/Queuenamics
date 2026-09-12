from math import sqrt
from statistics import NormalDist


class Statistic:
    """
    A scalar statistic with optional entity-aware grouping.

    Notes
    -----
    ``variance`` and ``standard_deviation`` refer to population statistics
    and therefore use N as the denominator.

    For sample statistics, use ``sample_variance`` and
    ``sample_standard_deviation``, which use N - 1.

    Empty statistics return ``0.0`` for numerical summary properties.
    """

    def __init__(self):
        self.count = 0
        self.total = 0.0
        self._groups = {}
        self.values = []

    def record(self, value, entity=None):
        """Record one observation.

        Parameters
        ----------
        value : float
            The observed value.
        entity : Entity, optional
            Entity associated with the observation. If supplied, the
            observation is automatically included in entity-type and
            entity-attribute groups.
        """
        self.count += 1
        self.total += value
        self.values.append(value)

        if entity is not None:
            self._record_group(
                "entity_type",
                entity.entity_type,
                value,
            )

            for attribute, attribute_value in entity.attributes.items():
                self._record_group(
                    attribute,
                    attribute_value,
                    value,
                )

    def _record_group(self, group, key, value):
        """Record an observation in an internal group."""
        data = self._groups.setdefault(group, {})

        bucket = data.setdefault(
            key,
            {
                "count": 0,
                "total": 0.0,
                "values": [],
            },
        )

        bucket["count"] += 1
        bucket["total"] += value
        bucket["values"].append(value)

    @property
    def mean(self):
        """Return the arithmetic mean."""
        if self.count == 0:
            return 0.0

        return self.total / self.count

    @property
    def minimum(self):
        """Return the minimum observation."""
        if not self.values:
            return 0.0

        return min(self.values)

    @property
    def maximum(self):
        """Return the maximum observation."""
        if not self.values:
            return 0.0

        return max(self.values)

    @property
    def median(self):
        """Return the 50th percentile (median)."""
        return self.percentile(50)

    @property
    def q1(self):
        """Return the first quartile (25th percentile)."""
        return self.percentile(25)

    @property
    def q2(self):
        """Return the second quartile (50th percentile)."""
        return self.percentile(50)

    @property
    def q3(self):
        """Return the third quartile (75th percentile)."""
        return self.percentile(75)

    @property
    def iqr(self):
        """Return the interquartile range (Q3 - Q1)."""
        return self.q3 - self.q1

    @property
    def population_variance(self):
        """
        Return the population variance.

        The denominator is N.
        """
        if self.count == 0:
            return 0.0

        mean = self.mean

        return sum(
            (value - mean) ** 2
            for value in self.values
        ) / self.count

    @property
    def sample_variance(self):
        """
        Return the sample variance.

        The denominator is N - 1. Returns 0.0 when fewer than two
        observations are available.
        """
        if self.count < 2:
            return 0.0

        mean = self.mean

        return sum(
            (value - mean) ** 2
            for value in self.values
        ) / (self.count - 1)

    @property
    def variance(self):
        """
        Return the population variance.

        This property is retained for backwards compatibility.
        """
        return self.population_variance

    @property
    def population_standard_deviation(self):
        """Return the population standard deviation."""
        return sqrt(self.population_variance)

    @property
    def sample_standard_deviation(self):
        """Return the sample standard deviation."""
        return sqrt(self.sample_variance)

    @property
    def standard_deviation(self):
        """
        Return the population standard deviation.

        This property is retained for backwards compatibility.
        """
        return self.population_standard_deviation

    def percentile(self, percentage):
        """
        Return a percentile using linear interpolation.

        Parameters
        ----------
        percentage : float
            Percentile between 0 and 100 inclusive.

        Returns
        -------
        float
            The requested percentile.

        Raises
        ------
        ValueError
            If ``percentage`` is outside the range 0 to 100.
        """
        if not 0 <= percentage <= 100:
            raise ValueError(
                "percentile must be between 0 and 100"
            )

        if not self.values:
            return 0.0

        values = sorted(self.values)

        if len(values) == 1:
            return values[0]

        position = (
            percentage / 100
        ) * (len(values) - 1)

        lower_index = int(position)
        upper_index = lower_index + 1

        if upper_index >= len(values):
            return values[lower_index]

        fraction = position - lower_index

        return (
            values[lower_index]
            + fraction
            * (
                values[upper_index]
                - values[lower_index]
            )
        )

    def group_by(self, group):
        """
        Return statistics grouped by entity type or entity attribute.

        The returned dictionary preserves the existing Queuenamics API.
        Each group contains the same major descriptive statistics as
        ``Statistic``.
        """
        groups = self._groups.get(group, {})

        result = {}

        for key, data in groups.items():
            values = data["values"]
            count = data["count"]
            total = data["total"]

            if count == 0:
                mean = 0.0
                minimum = 0.0
                maximum = 0.0
                population_variance = 0.0
                sample_variance = 0.0
            else:
                mean = total / count
                minimum = min(values)
                maximum = max(values)

                population_variance = sum(
                    (value - mean) ** 2
                    for value in values
                ) / count

                if count < 2:
                    sample_variance = 0.0
                else:
                    sample_variance = sum(
                        (value - mean) ** 2
                        for value in values
                    ) / (count - 1)

            population_standard_deviation = sqrt(
                population_variance
            )

            sample_standard_deviation = sqrt(
                sample_variance
            )

            def percentile(percentage):
                if not 0 <= percentage <= 100:
                    raise ValueError(
                        "percentile must be between 0 and 100"
                    )

                if not values:
                    return 0.0

                sorted_values = sorted(values)

                if len(sorted_values) == 1:
                    return sorted_values[0]

                position = (
                    percentage / 100
                ) * (len(sorted_values) - 1)

                lower_index = int(position)
                upper_index = lower_index + 1

                if upper_index >= len(sorted_values):
                    return sorted_values[lower_index]

                fraction = position - lower_index

                return (
                    sorted_values[lower_index]
                    + fraction
                    * (
                        sorted_values[upper_index]
                        - sorted_values[lower_index]
                    )
                )

            q1 = percentile(25)
            median = percentile(50)
            q3 = percentile(75)

            result[key] = {
                "count": count,
                "total": total,
                "mean": mean,
                "minimum": minimum,
                "maximum": maximum,
                "median": median,
                "q1": q1,
                "q2": median,
                "q3": q3,
                "iqr": q3 - q1,
                "variance": population_variance,
                "population_variance": population_variance,
                "sample_variance": sample_variance,
                "standard_deviation":
                    population_standard_deviation,
                "population_standard_deviation":
                    population_standard_deviation,
                "sample_standard_deviation":
                    sample_standard_deviation,
                "percentile_25": q1,
                "percentile_50": median,
                "percentile_75": q3,
                "percentile_90": percentile(90),
                "percentile_95": percentile(95),
                "percentile_99": percentile(99),
            }

        return result

    def grouped_count(self, group):
        """Return observation counts grouped by entity type or attribute."""
        return {
            key: data["count"]
            for key, data in self._groups.get(group, {}).items()
        }

    def reset(self):
        """Remove all observations and grouped statistics."""
        self.count = 0
        self.total = 0.0
        self._groups.clear()
        self.values.clear()


class TimeWeightedStatistic:
    """
    A statistic whose value changes at discrete simulation events.

    The statistic stores state-change history and calculates quantities
    exactly from the area under the state curve. No periodic sampling
    is required.
    """

    def __init__(self):
        self.area = 0.0
        self.last_time = 0.0
        self.current = 0.0
        self.maximum = 0.0
        self.start_time = 0.0
        self.history = [(0.0, 0.0)]

    def update(self, value, time):
        """
        Update the statistic at a simulation time.

        Raises
        ------
        ValueError
            If ``time`` is earlier than the previous update time.
        """
        if time < self.last_time:
            raise ValueError(
                "TimeWeightedStatistic cannot move backwards in time."
            )

        elapsed = time - self.last_time

        self.area += self.current * elapsed
        self.last_time = time
        self.current = value

        if value > self.maximum:
            self.maximum = value

        self.history.append((time, value))

    def mean(self, until):
        """
        Return the exact time-weighted mean up to ``until``.
        """
        elapsed = until - self.start_time

        if elapsed <= 0:
            return 0.0

        area = (
            self.area
            + self.current
            * (until - self.last_time)
        )

        return area / elapsed

    def total_time_where(self, predicate, until):
        """
        Return the amount of time for which ``predicate(value)`` is true.
        """
        elapsed = until - self.start_time

        if elapsed <= 0:
            return 0.0

        total = 0.0
        history = self.history

        for index, (time, value) in enumerate(history):
            if time >= until:
                break

            if index + 1 < len(history):
                end_time = history[index + 1][0]
            else:
                end_time = until

            end_time = min(end_time, until)

            if end_time <= time:
                continue

            if predicate(value):
                total += end_time - time

        return total

    def time_at(self, value, until):
        """Return time spent exactly at a particular value."""
        return self.total_time_where(
            lambda current: current == value,
            until,
        )

    def time_zero(self, until):
        """Return time spent at zero."""
        return self.time_at(0, until)

    def time_nonzero(self, until):
        """Return time spent at a nonzero value."""
        return self.total_time_where(
            lambda current: current != 0,
            until,
        )

    def occupancy(self, until):
        """
        Return the fraction of time for which the statistic was nonzero.
        """
        elapsed = until - self.start_time

        if elapsed <= 0:
            return 0.0

        return self.time_nonzero(until) / elapsed

    def period_durations(self, predicate, until):
        """
        Return durations of contiguous periods where ``predicate(value)``
        is true.

        An ongoing final period is included up to ``until``.
        """
        periods = []
        period_start = None

        for index, (time, value) in enumerate(self.history):
            if time >= until:
                break

            matches = predicate(value)

            if matches and period_start is None:
                period_start = time

            elif not matches and period_start is not None:
                duration = time - period_start

                if duration > 0:
                    periods.append(duration)

                period_start = None

        if period_start is not None:
            duration = until - period_start

            if duration > 0:
                periods.append(duration)

        return periods

    def periods_nonzero(self, until):
        """Return durations of all contiguous nonzero periods."""
        return self.period_durations(
            lambda value: value != 0,
            until,
        )

    def reset(self, time=0.0, current=0.0):
        """Reset the statistic at a specified simulation time and value."""
        self.area = 0.0
        self.last_time = time
        self.current = current
        self.maximum = current
        self.start_time = time
        self.history = [(time, current)]


class Statistics:
    """
    Collection of standard simulation statistics.

    Includes entity-based statistics such as waiting and service time,
    as well as time-weighted queue and server statistics.
    """

    def __init__(self):
        self.waiting_time = Statistic()
        self.service_time = Statistic()
        self.other_time = Statistic()
        self.flow_time = Statistic()

        self.queue_length = TimeWeightedStatistic()
        self.server_occupancy = TimeWeightedStatistic()

    def reset(self):
        """Reset all contained statistics."""
        self.waiting_time.reset()
        self.service_time.reset()
        self.other_time.reset()
        self.flow_time.reset()

        self.queue_length.reset()
        self.server_occupancy.reset()


class ReplicationStatistic:
    """
    Statistics calculated across independent simulation replications.

    The standard deviation is a sample standard deviation using N - 1.

    Confidence intervals use Student's t distribution. The confidence
    interval level can be selected with ``confidence_interval()``.
    """

    _T_90 = {
        1: 6.314,
        2: 2.920,
        3: 2.353,
        4: 2.132,
        5: 2.015,
        6: 1.943,
        7: 1.895,
        8: 1.860,
        9: 1.833,
        10: 1.812,
        11: 1.796,
        12: 1.782,
        13: 1.771,
        14: 1.761,
        15: 1.753,
        16: 1.746,
        17: 1.740,
        18: 1.734,
        19: 1.729,
        20: 1.725,
        21: 1.721,
        22: 1.717,
        23: 1.714,
        24: 1.711,
        25: 1.708,
        26: 1.706,
        27: 1.703,
        28: 1.701,
        29: 1.699,
        30: 1.697,
    }

    _T_95 = {
        1: 12.706,
        2: 4.303,
        3: 3.182,
        4: 2.776,
        5: 2.571,
        6: 2.447,
        7: 2.365,
        8: 2.306,
        9: 2.262,
        10: 2.228,
        11: 2.201,
        12: 2.179,
        13: 2.160,
        14: 2.145,
        15: 2.131,
        16: 2.120,
        17: 2.110,
        18: 2.101,
        19: 2.093,
        20: 2.086,
        21: 2.080,
        22: 2.074,
        23: 2.069,
        24: 2.064,
        25: 2.060,
        26: 2.056,
        27: 2.052,
        28: 2.048,
        29: 2.045,
        30: 2.042,
    }

    _T_99 = {
        1: 63.657,
        2: 9.925,
        3: 5.841,
        4: 4.604,
        5: 4.032,
        6: 3.707,
        7: 3.499,
        8: 3.355,
        9: 3.250,
        10: 3.169,
        11: 3.106,
        12: 3.055,
        13: 3.012,
        14: 2.977,
        15: 2.947,
        16: 2.921,
        17: 2.898,
        18: 2.878,
        19: 2.861,
        20: 2.845,
        21: 2.831,
        22: 2.819,
        23: 2.807,
        24: 2.797,
        25: 2.787,
        26: 2.779,
        27: 2.771,
        28: 2.763,
        29: 2.756,
        30: 2.750,
    }

    def __init__(self, values):
        self.values = list(values)

    @property
    def count(self):
        """Return the number of replications."""
        return len(self.values)

    @property
    def mean(self):
        """Return the mean across replications."""
        if not self.values:
            return 0.0

        return sum(self.values) / self.count

    @property
    def sample_variance(self):
        """Return the sample variance across replications."""
        if self.count < 2:
            return 0.0

        mean = self.mean

        return sum(
            (value - mean) ** 2
            for value in self.values
        ) / (self.count - 1)

    @property
    def standard_deviation(self):
        """Return the sample standard deviation."""
        return sqrt(self.sample_variance)

    @property
    def standard_error(self):
        """Return the standard error of the mean."""
        if self.count < 2:
            return 0.0

        return self.standard_deviation / sqrt(self.count)

    def t_critical(self, confidence=0.95):
        """
        Return the Student-t critical value.

        Parameters
        ----------
        confidence : float
            Confidence level between 0 and 1.

        Notes
        -----
        Exact tabulated Student-t values are used for 90%, 95%, and
        99% confidence levels up to 30 degrees of freedom.

        For other confidence levels, or more than 30 degrees of
        freedom, a normal approximation is used.
        """
        if not 0 < confidence < 1:
            raise ValueError(
                "confidence must be between 0 and 1"
            )

        if self.count < 2:
            return float("inf")

        degrees_of_freedom = self.count - 1

        tables = {
            0.90: self._T_90,
            0.95: self._T_95,
            0.99: self._T_99,
        }

        table = tables.get(confidence)

        if table is not None and degrees_of_freedom in table:
            return table[degrees_of_freedom]

        # Normal approximation for larger samples or
        # non-tabulated confidence levels.
        probability = 0.5 + confidence / 2

        return NormalDist().inv_cdf(probability)

    @property
    def t_critical_95(self):
        """Return the 95% Student-t critical value."""
        return self.t_critical(0.95)

    def margin_of_error(self, confidence=0.95):
        """Return the margin of error at the requested confidence level."""
        return (
            self.t_critical(confidence)
            * self.standard_error
        )

    @property
    def margin_of_error_95(self):
        """Return the 95% margin of error."""
        return self.margin_of_error(0.95)

    def confidence_interval(self, confidence=0.95):
        """
        Return a confidence interval for the mean.

        Parameters
        ----------
        confidence : float
            Confidence level between 0 and 1.

        Returns
        -------
        tuple
            ``(lower, upper)`` confidence interval.
        """
        margin = self.margin_of_error(confidence)

        return (
            self.mean - margin,
            self.mean + margin,
        )

    @property
    def confidence_interval_95(self):
        """Return the 95% confidence interval."""
        return self.confidence_interval(0.95)

    def summary(self, confidence=0.95):
        """
        Return a dictionary containing the main replication statistics.
        """
        lower, upper = self.confidence_interval(confidence)

        return {
            "count": self.count,
            "mean": self.mean,
            "standard_deviation":
                self.standard_deviation,
            "standard_error":
                self.standard_error,
            "confidence_level": confidence,
            "margin_of_error":
                self.margin_of_error(confidence),
            "confidence_interval":
                [lower, upper],
        }


class ReplicationResults:
    """
    Collection of results from independent model replications.

    Metrics are flattened using dotted paths, for example:

        "queues.Waiting.average_waiting_time"
        "servers.Machine.utilization"
        "sinks.Completed.throughput"
    """

    def __init__(self, reports):
        self.reports = list(reports)
        self.count = len(self.reports)
        self._metrics = {}

        for report in self.reports:
            self._collect_metrics(report)

    def _collect_metrics(self, value, prefix=""):
        if isinstance(value, dict):
            for key, child in value.items():
                path = (
                    f"{prefix}.{key}"
                    if prefix
                    else str(key)
                )

                self._collect_metrics(
                    child,
                    path,
                )

            return

        if isinstance(value, bool):
            return

        if isinstance(value, (int, float)):
            self._metrics.setdefault(
                prefix,
                [],
            ).append(float(value))

    @property
    def metrics(self):
        """Return all available metric names."""
        return sorted(self._metrics)

    def values(self, metric):
        """Return all replication values for a metric."""
        if metric not in self._metrics:
            raise KeyError(
                f"Unknown replication metric: {metric!r}"
            )

        return list(self._metrics[metric])

    def statistic(self, metric):
        """Return a ReplicationStatistic for a metric."""
        return ReplicationStatistic(
            self.values(metric)
        )

    def mean(self, metric):
        """Return the mean of a metric across replications."""
        return self.statistic(metric).mean

    def confidence_interval(self, metric, confidence=0.95):
        """
        Return a confidence interval for a metric.

        Parameters
        ----------
        metric : str
            Metric name.
        confidence : float
            Confidence level between 0 and 1.
        """
        return (
            self.statistic(metric)
            .confidence_interval(confidence)
        )

    def summary(self, metric=None, confidence=0.95):
        """
        Return summary statistics.

        If ``metric`` is supplied, return its summary. Otherwise,
        return summaries for all metrics.
        """
        if metric is not None:
            return self.statistic(metric).summary(
                confidence=confidence
            )

        return {
            name: self.statistic(name).summary(
                confidence=confidence
            )
            for name in self.metrics
        }

    def __getitem__(self, metric):
        return self.statistic(metric)

    def __len__(self):
        return self.count