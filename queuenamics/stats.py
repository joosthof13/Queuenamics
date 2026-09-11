from math import sqrt
from statistics import NormalDist


class Statistic:
    """A scalar statistic with optional entity-aware grouping."""

    def __init__(self):
        self.count = 0
        self.total = 0.0
        self._groups = {}
        self.values = []

    def record(self, value, entity=None):
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
        data = self._groups.setdefault(
            group,
            {},
        )

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
        if self.count == 0:
            return 0.0

        return self.total / self.count

    @property
    def minimum(self):
        if not self.values:
            return 0.0

        return min(self.values)

    @property
    def maximum(self):
        if not self.values:
            return 0.0

        return max(self.values)

    @property
    def variance(self):
        if self.count == 0:
            return 0.0

        mean = self.mean

        return sum(
            (value - mean) ** 2
            for value in self.values
        ) / self.count

    @property
    def standard_deviation(self):
        return self.variance ** 0.5

    def percentile(self, percentage):
        if not self.values:
            return 0.0

        if not 0 <= percentage <= 100:
            raise ValueError(
                "percentile must be between 0 and 100"
            )

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
        """Return full statistics grouped by entity type/attribute."""

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
                variance = 0.0
                standard_deviation = 0.0
            else:
                mean = total / count
                minimum = min(values)
                maximum = max(values)

                variance = sum(
                    (value - mean) ** 2
                    for value in values
                ) / count

                standard_deviation = variance ** 0.5

            def percentile(percentage):
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

            result[key] = {
                "count": count,
                "total": total,
                "mean": mean,
                "minimum": minimum,
                "maximum": maximum,
                "variance": variance,
                "standard_deviation":
                    standard_deviation,
                "percentile_50":
                    percentile(50),
                "percentile_90":
                    percentile(90),
                "percentile_95":
                    percentile(95),
                "percentile_99":
                    percentile(99),
            }

        return result

    def grouped_count(self, group):
        """Return counts grouped by entity type/attribute."""

        return {
            key: data["count"]
            for key, data in self._groups.get(group, {}).items()
        }

    def reset(self):
        self.count = 0
        self.total = 0.0
        self._groups.clear()
        self.values.clear()


class TimeWeightedStatistic:
    """
    A statistic whose value changes at discrete simulation events.

    The statistic stores the complete state-change history, allowing
    exact calculation of time-weighted quantities without periodic
    sampling.
    """

    def __init__(self):
        self.area = 0.0
        self.last_time = 0.0
        self.current = 0.0
        self.maximum = 0.0
        self.start_time = 0.0
        self.history = [(0.0, 0.0)]

    def update(self, value, time):
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
        Return the amount of time for which predicate(value) is true.
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
        return self.time_at(0, until)

    def time_nonzero(self, until):
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
        Return durations of contiguous periods where predicate(value)
        is true.

        The final period is included up to `until`, which means an
        ongoing busy/idle period is correctly represented.
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
        return self.period_durations(
            lambda value: value != 0,
            until,
        )

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
        self.other_time = Statistic()
        self.flow_time = Statistic()

        self.queue_length = TimeWeightedStatistic()
        self.server_occupancy = TimeWeightedStatistic()

    def reset(self):
        self.waiting_time.reset()
        self.service_time.reset()
        self.other_time.reset()
        self.flow_time.reset()

        self.queue_length.reset()
        self.server_occupancy.reset()


class ReplicationStatistic:
    """
    Statistics calculated across independent simulation replications.

    The standard deviation is the sample standard deviation and the
    confidence interval uses Student's t distribution for 95% CIs.
    """

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

    def __init__(self, values):
        self.values = list(values)

    @property
    def count(self):
        return len(self.values)

    @property
    def mean(self):
        if not self.values:
            return 0.0

        return sum(self.values) / self.count

    @property
    def standard_deviation(self):
        if self.count < 2:
            return 0.0

        mean = self.mean

        variance = sum(
            (value - mean) ** 2
            for value in self.values
        ) / (self.count - 1)

        return sqrt(variance)

    @property
    def standard_error(self):
        if self.count < 2:
            return 0.0

        return self.standard_deviation / sqrt(self.count)

    @property
    def t_critical_95(self):
        if self.count < 2:
            return float("inf")

        degrees_of_freedom = self.count - 1

        if degrees_of_freedom in self._T_95:
            return self._T_95[degrees_of_freedom]

        return 1.96

    @property
    def margin_of_error_95(self):
        return (
            self.t_critical_95
            * self.standard_error
        )

    @property
    def confidence_interval_95(self):
        margin = self.margin_of_error_95

        return (
            self.mean - margin,
            self.mean + margin,
        )

    def summary(self):
        lower, upper = self.confidence_interval_95

        return {
            "count": self.count,
            "mean": self.mean,
            "standard_deviation":
                self.standard_deviation,
            "standard_error":
                self.standard_error,
            "confidence_level": 0.95,
            "margin_of_error":
                self.margin_of_error_95,
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
            self._collect_metrics(
                report
            )

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
        return sorted(self._metrics)

    def values(self, metric):
        if metric not in self._metrics:
            raise KeyError(
                f"Unknown replication metric: {metric!r}"
            )

        return list(self._metrics[metric])

    def statistic(self, metric):
        return ReplicationStatistic(
            self.values(metric)
        )

    def mean(self, metric):
        return self.statistic(metric).mean

    def confidence_interval(self, metric):
        return (
            self.statistic(metric)
            .confidence_interval_95
        )

    def summary(self, metric=None):
        if metric is not None:
            return self.statistic(metric).summary()

        return {
            name: self.statistic(name).summary()
            for name in self.metrics
        }

    def __getitem__(self, metric):
        return self.statistic(metric)

    def __len__(self):
        return self.count