"""
Experiment and parameter-sweep utilities for Queuenamics.

This module provides:
- Experiment: run independent model replications.
- ExperimentResults: structured analysis of experiment outputs.
- ParameterSweep: run an experiment for every parameter combination.
- ParameterSweepResults: structured comparison of sweep configurations.

The public API remains compatible with the original Experiment and
ParameterSweep classes while adding unified replication statistics.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from statistics import mean

from queuenamics.stats import ReplicationStatistic


class ExperimentResults:
    """Structured results from an :class:`Experiment`.

    Parameters
    ----------
    models:
        Models produced by the experiment.
    reports:
        Optional report dictionaries corresponding to ``models``.

    Notes
    -----
    Models are retained for backward compatibility. For large experiments,
    callers can discard ``models`` after extracting the required metrics.
    """

    def __init__(self, models=None, reports=None):
        self.models = list(models or [])
        self.reports = list(reports or [])

        if not self.reports and self.models:
            self.reports = [
                model.stats.report()
                for model in self.models
            ]

    @property
    def count(self):
        """Return the number of replications."""
        return len(self.reports)

    @property
    def metrics(self):
        """Return available report metric names.

        Nested dictionaries are exposed as dotted paths.
        """
        values = {}

        for report in self.reports:
            self._collect_metrics(report, values)

        return sorted(values)

    @staticmethod
    def _collect_metrics(value, result, prefix=""):
        if isinstance(value, dict):
            for key, child in value.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                ExperimentResults._collect_metrics(
                    child, result, path
                )
            return

        if isinstance(value, bool):
            return

        if isinstance(value, (int, float)):
            result.setdefault(prefix, [])

    def _metric_values(self, metric):
        if not isinstance(metric, str) or not metric:
            raise ValueError("metric must be a non-empty string")

        values = []

        for report in self.reports:
            found, value = self._get_path(report, metric)
            if found and isinstance(value, (int, float)) and not isinstance(value, bool):
                values.append(float(value))

        if not values:
            raise KeyError(
                f"Unknown or non-numeric experiment metric: {metric!r}"
            )

        return values

    @staticmethod
    def _get_path(data, path):
        current = data

        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return False, None
            current = current[part]

        return True, current

    def values(self, extractor_or_metric):
        """Return values across replications.

        ``extractor_or_metric`` may be either:
        - a callable receiving a model, or
        - a dotted metric name from ``metrics``.
        """
        if not self.reports:
            raise RuntimeError("Experiment has not been run")

        if callable(extractor_or_metric):
            if not self.models:
                raise RuntimeError(
                    "Models were not retained; use a metric name instead"
                )
            return [
                extractor_or_metric(model)
                for model in self.models
            ]

        return self._metric_values(extractor_or_metric)

    def statistic(self, extractor_or_metric):
        """Return a :class:`ReplicationStatistic` for a metric or extractor."""
        return ReplicationStatistic(
            self.values(extractor_or_metric)
        )

    def mean(self, extractor_or_metric):
        """Return the mean across replications."""
        return self.statistic(extractor_or_metric).mean

    def standard_deviation(self, extractor_or_metric):
        """Return the sample standard deviation across replications."""
        return self.statistic(extractor_or_metric).standard_deviation

    def standard_error(self, extractor_or_metric):
        """Return the standard error of the mean."""
        return self.statistic(extractor_or_metric).standard_error

    def confidence_interval(
        self,
        extractor_or_metric,
        confidence=0.95,
    ):
        """Return a Student-t confidence interval across replications.

        At least two replications are required to estimate uncertainty.
        """
        if self.count < 2:
            raise RuntimeError(
                "At least two replications are required "
                "to calculate a confidence interval"
            )
        return self.statistic(
            extractor_or_metric
        ).confidence_interval(confidence)

    def summary(self, extractor_or_metric=None, confidence=0.95):
        """Return statistical summaries.

        If no metric is supplied, return summaries for all report metrics.
        """
        if extractor_or_metric is not None:
            return self.statistic(
                extractor_or_metric
            ).summary(confidence=confidence)

        return {
            metric: self.statistic(metric).summary(
                confidence=confidence
            )
            for metric in self.metrics
        }

    def compare(self, metric, other, confidence=0.95):
        """Compare this result with another result.

        Returns the difference ``other - self`` together with confidence
        intervals for both means.

        This is a descriptive comparison, not a hypothesis test.
        """
        if not isinstance(other, ExperimentResults):
            raise TypeError("other must be an ExperimentResults instance")

        first = self.statistic(metric)
        second = other.statistic(metric)

        first_ci = first.confidence_interval(confidence)
        second_ci = second.confidence_interval(confidence)

        return {
            "metric": metric,
            "confidence_level": confidence,
            "mean": {
                "self": first.mean,
                "other": second.mean,
                "difference": second.mean - first.mean,
            },
            "standard_deviation": {
                "self": first.standard_deviation,
                "other": second.standard_deviation,
            },
            "confidence_interval": {
                "self": list(first_ci),
                "other": list(second_ci),
            },
        }

    def to_dict(self, confidence=0.95):
        """Return all metric summaries as a dictionary."""
        return {
            "replications": self.count,
            "metrics": self.summary(confidence=confidence),
        }

    def export(self, filename, format=None, confidence=0.95):
        """Export experiment summaries to JSON or CSV.

        Parameters
        ----------
        filename:
            Destination filename.
        format:
            ``"json"`` or ``"csv"``. If omitted, inferred from the suffix.
        confidence:
            Confidence level for reported intervals.
        """
        path = Path(filename)
        fmt = (format or path.suffix.lstrip(".")).lower()

        if fmt == "json":
            path.write_text(
                json.dumps(self.to_dict(confidence), indent=2),
                encoding="utf-8",
            )
            return

        if fmt == "csv":
            import csv

            rows = []
            for metric, summary in self.summary(
                confidence=confidence
            ).items():
                lower, upper = summary["confidence_interval"]
                rows.append({
                    "metric": metric,
                    "count": summary["count"],
                    "mean": summary["mean"],
                    "standard_deviation": summary["standard_deviation"],
                    "standard_error": summary["standard_error"],
                    "confidence_level": summary["confidence_level"],
                    "margin_of_error": summary["margin_of_error"],
                    "confidence_interval_lower": lower,
                    "confidence_interval_upper": upper,
                })

            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "metric",
                        "count",
                        "mean",
                        "standard_deviation",
                        "standard_error",
                        "confidence_level",
                        "margin_of_error",
                        "confidence_interval_lower",
                        "confidence_interval_upper",
                    ],
                )
                writer.writeheader()
                writer.writerows(rows)
            return

        raise ValueError(
            f"Unsupported format: {fmt!r}. Use 'json' or 'csv'."
        )

    def __getitem__(self, key):
        """Return a model by integer index or a statistic by metric name."""
        if isinstance(key, int):
            return self.models[key]
        if isinstance(key, str):
            return self.statistic(key)
        raise TypeError("ExperimentResults indices must be integers or metric names")

    def __iter__(self):
        """Iterate over retained models for backward compatibility."""
        return iter(self.models)

    def __len__(self):
        return len(self.models)


class Experiment:
    """Run independent replications of a Queuenamics model.

    Parameters
    ----------
    model_factory:
        Callable receiving the replication index and returning a Model.
    replications:
        Number of independent replications.
    time:
        Simulation duration for each replication.
    warmup:
        Warm-up period excluded from measurement statistics.
    """

    def __init__(self, model_factory, replications, time, warmup=0):
        if replications <= 0:
            raise ValueError("replications must be greater than 0")
        if time <= 0:
            raise ValueError("time must be greater than 0")
        if warmup < 0:
            raise ValueError("warmup must be non-negative")
        if warmup >= time:
            raise ValueError("warmup must be smaller than time")

        if not callable(model_factory):
            raise TypeError("model_factory must be callable")

        self.model_factory = model_factory
        self.replications = replications
        self.time = time
        self.warmup = warmup

        # Backward-compatible raw model storage.
        self.results = []

        # Structured analysis result.
        self.experiment_results = None

    def run(self):
        """Run all replications and return :class:`ExperimentResults`."""
        self.results = []
        reports = []

        for replication in range(self.replications):
            model = self.model_factory(replication)
            model.run(
                time=self.time,
                warmup=self.warmup,
            )

            self.results.append(model)
            reports.append(model.stats.report())

        self.experiment_results = ExperimentResults(
            models=self.results,
            reports=reports,
        )

        return self.experiment_results

    @property
    def analysis(self):
        """Alias for :attr:`experiment_results`."""
        if self.experiment_results is None:
            raise RuntimeError("Experiment has not been run")
        return self.experiment_results

    def values(self, extractor):
        """Return extracted values from every replication.

        Preserved for backward compatibility.
        """
        if not self.results:
            raise RuntimeError("Experiment has not been run")

        return [
            extractor(model)
            for model in self.results
        ]

    def mean(self, extractor):
        """Return the mean of an extracted value."""
        return self.analysis.mean(extractor)

    def standard_deviation(self, extractor):
        """Return the sample standard deviation of an extracted value."""
        return self.analysis.standard_deviation(extractor)

    def confidence_interval(self, extractor, confidence=0.95):
        """Return a Student-t confidence interval.

        This replaces the old hard-coded normal 1.96 approximation and
        uses the same replication-statistics implementation as Model.
        """
        return self.analysis.confidence_interval(
            extractor,
            confidence=confidence,
        )

class ParameterSweepResults:
    """Structured results from a :class:`ParameterSweep`.

    Supports both ordinary parameters and structural atom-count
    parameters.
    """

    def __init__(self, results=None):
        self.results = list(results or [])

    @property
    def count(self):
        """Return the number of parameter configurations."""
        return len(self.results)

    @property
    def parameter_names(self):
        """Return ordinary parameter names in stable order."""
        if not self.results:
            return []

        return list(self.results[0]["parameters"])

    @property
    def atom_names(self):
        """Return atom types whose counts were swept."""
        if not self.results:
            return []

        return list(
            self.results[0].get("atom_counts", {})
        )

    def combinations(self):
        """Return all parameter configurations.

        Atom counts are included under the ``"atoms"`` key.
        """
        combinations = []

        for result in self.results:
            configuration = dict(
                result["parameters"]
            )

            if result.get("atom_counts"):
                configuration["atoms"] = dict(
                    result["atom_counts"]
                )

            combinations.append(configuration)

        return combinations

    def experiments(self):
        """Return the :class:`ExperimentResults` objects."""
        return [
            result["results"]
            for result in self.results
        ]

    def values(self, extractor_or_metric):
        """Return one mean value per configuration."""
        return [
            experiment.mean(extractor_or_metric)
            for experiment in self.experiments()
        ]

    def table(self, extractor_or_metric):
        """Return sweep results as a list of dictionaries.

        Atom counts are represented as columns named
        ``atoms.<atom_name>``.
        """
        rows = []

        for result in self.results:
            experiment = result["results"]

            row = dict(result["parameters"])

            for atom_name, count in result.get(
                "atom_counts",
                {},
            ).items():
                row[f"atoms.{atom_name}"] = count

            row.update(
                experiment.summary(
                    extractor_or_metric
                )
            )

            rows.append(row)

        return rows

    def best(
        self,
        extractor_or_metric,
        maximize=False,
    ):
        """Return the best configuration.

        Parameters
        ----------
        extractor_or_metric:
            Callable or dotted report metric.

        maximize:
            If ``True``, maximize the metric.
            If ``False``, minimize the metric.
        """
        if not self.results:
            raise RuntimeError(
                "Parameter sweep has not been run"
            )

        rows = self.table(
            extractor_or_metric
        )

        if maximize:
            return max(
                rows,
                key=lambda row: row["mean"],
            )

        return min(
            rows,
            key=lambda row: row["mean"],
        )

    def filter(self, **parameters):
        """Return a new result containing matching configurations.

        Ordinary parameters are matched directly.

        Atom counts can be matched using:

            atoms.Cashier=3

        Example
        -------
        ``results.filter(service_rate=6)``

        ``results.filter(**{"atoms.Cashier": 3})``
        """
        filtered = []

        for result in self.results:
            matches = True

            for name, value in parameters.items():

                if name.startswith("atoms."):
                    atom_name = name.split(
                        ".", 1
                    )[1]

                    actual = result.get(
                        "atom_counts",
                        {},
                    ).get(atom_name)

                else:
                    actual = result[
                        "parameters"
                    ].get(name)

                if actual != value:
                    matches = False
                    break

            if matches:
                filtered.append(result)

        return ParameterSweepResults(
            filtered
        )

    def compare(
        self,
        extractor_or_metric,
        first,
        second,
        confidence=0.95,
    ):
        """Compare two parameter configurations.

        ``first`` and ``second`` may be:

        - integer result indices
        - ordinary parameter dictionaries
        - complete configuration dictionaries containing
          ``"atoms"``

        """
        first_result = self._resolve(first)
        second_result = self._resolve(second)

        comparison = first_result[
            "results"
        ].compare(
            extractor_or_metric,
            second_result["results"],
            confidence=confidence,
        )

        comparison["parameters"] = {
            "first": self._configuration(
                first_result
            ),
            "second": self._configuration(
                second_result
            ),
        }

        return comparison

    @staticmethod
    def _configuration(result):
        """Return the complete configuration."""
        configuration = dict(
            result["parameters"]
        )

        if result.get("atom_counts"):
            configuration["atoms"] = dict(
                result["atom_counts"]
            )

        return configuration

    def _resolve(self, value):
        """Resolve an index or configuration."""
        if isinstance(value, int):
            try:
                return self.results[value]
            except IndexError as exc:
                raise IndexError(
                    f"Unknown parameter-sweep "
                    f"result index: {value}"
                ) from exc

        if isinstance(value, dict):

            # Allow both:
            #
            # {"service_rate": 6}
            #
            # and:
            #
            # {
            #     "service_rate": 6,
            #     "atoms": {"Cashier": 3}
            # }

            for result in self.results:
                if (
                    self._configuration(result)
                    == value
                ):
                    return result

            raise KeyError(
                f"Unknown parameter configuration: "
                f"{value!r}"
            )

        raise TypeError(
            "Configuration must be an integer "
            "index or parameter dictionary"
        )

    def export(
        self,
        filename,
        extractor_or_metric,
        format=None,
    ):
        """Export sweep results to CSV or JSON."""
        path = Path(filename)

        fmt = (
            format
            or path.suffix.lstrip(".")
        ).lower()

        rows = self.table(
            extractor_or_metric
        )

        if fmt == "json":
            path.write_text(
                json.dumps(
                    rows,
                    indent=2,
                ),
                encoding="utf-8",
            )
            return

        if fmt == "csv":
            import csv

            fieldnames = []

            for row in rows:
                for key in row:
                    if key not in fieldnames:
                        fieldnames.append(key)

            with path.open(
                "w",
                newline="",
                encoding="utf-8",
            ) as handle:

                writer = csv.DictWriter(
                    handle,
                    fieldnames=fieldnames,
                )

                writer.writeheader()
                writer.writerows(rows)

            return

        raise ValueError(
            f"Unsupported format: {fmt!r}. "
            "Use 'json' or 'csv'."
        )

    def __getitem__(self, index):
        return self.results[index]

    def __len__(self):
        return self.count

    def __iter__(self):
        return iter(self.results)


class ParameterSweep:
    """Run experiments for every parameter combination.

    Parameters
    ----------
    model_factory:
        Callable with signature::

            model_factory(parameters, replication)

        The ``parameters`` dictionary contains ordinary parameters
        normally, plus an ``"atoms"`` dictionary containing swept
        atom counts.

    parameters:
        Dictionary mapping ordinary parameter names to iterables
        of values.

        Example::

            parameters={
                "arrival_rate": [4, 5, 6],
                "service_rate": [5, 6, 7],
            }

    atom_counts:
        Optional dictionary mapping atom types/names to iterables
        of non-negative integer counts.

        Example::

            atom_counts={
                "Cashier": range(1, 7),
                "Machine": [1, 2, 3],
            }

        The values are passed to ``model_factory`` as::

            parameters["atoms"]["Cashier"]

        and::

            parameters["atoms"]["Machine"]

    replications:
        Number of replications per configuration.

    time:
        Simulation duration for each replication.

    warmup:
        Warm-up period excluded from measurement statistics.

    Notes
    -----
    ``ParameterSweep`` does not construct atoms automatically.

    The sweep determines *which model structures should be tested*;
    ``model_factory`` determines how those structures are constructed.

    This allows the feature to work with every Queuenamics atom,
    including custom atoms.
    """

    def __init__(
        self,
        model_factory,
        parameters=None,
        replications=1,
        time=1,
        warmup=0,
        atom_counts=None,
    ):
        if not callable(model_factory):
            raise TypeError(
                "model_factory must be callable"
            )

        if replications <= 0:
            raise ValueError(
                "replications must be greater than 0"
            )

        if time <= 0:
            raise ValueError(
                "time must be greater than 0"
            )

        if warmup < 0:
            raise ValueError(
                "warmup must be non-negative"
            )

        if warmup >= time:
            raise ValueError(
                "warmup must be smaller than time"
            )

        if parameters is None:
            parameters = {}

        if atom_counts is None:
            atom_counts = {}

        if not isinstance(parameters, dict):
            raise TypeError(
                "parameters must be a dictionary"
            )

        if not isinstance(atom_counts, dict):
            raise TypeError(
                "atom_counts must be a dictionary"
            )

        if not parameters and not atom_counts:
            raise ValueError(
                "At least one parameter or atom count "
                "must be provided"
            )

        self.model_factory = model_factory

        self.parameters = (
            self._validate_parameter_values(
                parameters
            )
        )

        self.atom_counts = (
            self._validate_atom_counts(
                atom_counts
            )
        )

        self.replications = replications
        self.time = time
        self.warmup = warmup

        self.results = None
        self.sweep_results = None

    @staticmethod
    def _validate_parameter_values(
        parameters
    ):
        """Validate ordinary sweep parameters."""
        validated = {}

        for name, values in parameters.items():

            if (
                not isinstance(name, str)
                or not name
            ):
                raise ValueError(
                    "parameter names must be "
                    "non-empty strings"
                )

            try:
                values = list(values)
            except TypeError as exc:
                raise TypeError(
                    f"Values for parameter "
                    f"{name!r} must be iterable"
                ) from exc

            if not values:
                raise ValueError(
                    f"Values for parameter "
                    f"{name!r} must not be empty"
                )

            validated[name] = values

        return validated

    @staticmethod
    def _validate_atom_counts(
        atom_counts
    ):
        """Validate structural atom-count parameters."""
        validated = {}

        for atom_name, counts in atom_counts.items():

            if (
                not isinstance(atom_name, str)
                or not atom_name
            ):
                raise ValueError(
                    "atom names must be "
                    "non-empty strings"
                )

            try:
                counts = list(counts)
            except TypeError as exc:
                raise TypeError(
                    f"Values for atom count "
                    f"{atom_name!r} must be iterable"
                ) from exc

            if not counts:
                raise ValueError(
                    f"Values for atom count "
                    f"{atom_name!r} must not be empty"
                )

            for count in counts:
                if (
                    isinstance(count, bool)
                    or not isinstance(count, int)
                    or count < 0
                ):
                    raise ValueError(
                        f"Atom counts for "
                        f"{atom_name!r} must contain "
                        "non-negative integers"
                    )

            validated[atom_name] = counts

        return validated

    def _configurations(self):
        """Generate every ordinary/structural configuration."""
        parameter_names = list(
            self.parameters
        )

        parameter_values = [
            list(values)
            for values in self.parameters.values()
        ]

        atom_names = list(
            self.atom_counts
        )

        atom_values = [
            list(values)
            for values in self.atom_counts.values()
        ]

        if parameter_values:
            parameter_combinations = itertools.product(
                *parameter_values
            )
        else:
            parameter_combinations = [()]

        if atom_values:
            atom_combinations = itertools.product(
                *atom_values
            )
        else:
            atom_combinations = [()]

        for parameter_tuple in parameter_combinations:

            ordinary_parameters = dict(
                zip(
                    parameter_names,
                    parameter_tuple,
                )
            )

            for atom_tuple in atom_combinations:

                counts = dict(
                    zip(
                        atom_names,
                        atom_tuple,
                    )
                )

                yield (
                    ordinary_parameters,
                    counts,
                )

    def run(self):
        """Run all parameter and atom-count combinations.

        Every combination receives the configured number of
        independent replications.
        """
        results = []

        for (
            ordinary_parameters,
            atom_counts,
        ) in self._configurations():

            # Create a fresh parameter dictionary for this
            # configuration.
            parameter_set = dict(
                ordinary_parameters
            )

            # Structural parameters are isolated under
            # the "atoms" namespace.
            parameter_set["atoms"] = dict(
                atom_counts
            )

            experiment = Experiment(
                model_factory=(
                    lambda replication,
                    params=parameter_set:
                    self.model_factory(
                        params,
                        replication,
                    )
                ),
                replications=self.replications,
                time=self.time,
                warmup=self.warmup,
            )

            experiment_results = (
                experiment.run()
            )

            results.append({
                "parameters": dict(
                    ordinary_parameters
                ),

                "atom_counts": dict(
                    atom_counts
                ),

                "results": experiment_results,

                # Backward-compatible access
                # to the actual models.
                "models": (
                    experiment_results.models
                ),
            })

        self.sweep_results = (
            ParameterSweepResults(results)
        )

        self.results = self.sweep_results

        return self.sweep_results

    @property
    def analysis(self):
        """Alias for :attr:`sweep_results`."""
        if self.sweep_results is None:
            raise RuntimeError(
                "Parameter sweep has not been run"
            )

        return self.sweep_results
