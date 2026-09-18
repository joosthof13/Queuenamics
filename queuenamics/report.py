import csv
import json

from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich import box
from queuenamics.atoms import Resource


class StatisticsReport:

    def __init__(self, model):
        self.model = model
        self.console = Console()

    # --------------------------------------------------
    # Basic statistics
    # --------------------------------------------------

    def throughput(self, sink):
        observation_time = self.model.observation_time

        if observation_time <= 0:
            return 0.0

        return sink.entities_received / observation_time

    def _statistic_summary(self, statistic, extended=False):
        data = {
            "count": statistic.count,
            "total": statistic.total,
            "mean": statistic.mean,
        }

        if extended:
            data.update({
                "minimum": statistic.minimum,
                "maximum": statistic.maximum,
                "variance": statistic.variance,
                "standard_deviation":
                    statistic.standard_deviation,
                "percentile_50":
                    statistic.percentile(50),
                "percentile_90":
                    statistic.percentile(90),
                "percentile_95":
                    statistic.percentile(95),
                "percentile_99":
                    statistic.percentile(99),
            })

        return data

    def _entity_breakdown(
        self,
        statistic,
        group="entity_type",
    ):
        return statistic.group_by(group)

    def queue_occupancy(self, queue):
        simulation_time = self.model.simulation.time

        if simulation_time <= 0:
            return 0.0

        return queue.stats.queue_length.occupancy(
            simulation_time
        )

    # --------------------------------------------------
    # Replications
    # --------------------------------------------------

    def _has_replications(self):
        results = self.model.replication_results

        return (
            results is not None
            and results.count > 1
        )

    def _replication_statistic(self, key):
        results = self.model.replication_results

        if results is None:
            return None

        try:
            return results.statistic(key)
        except KeyError:
            return None

    def _replication_summary(self, key):
        statistic = self._replication_statistic(key)

        if statistic is None:
            return None

        ci = statistic.confidence_interval_95

        return {
            "mean": statistic.mean,
            "standard_deviation":
                statistic.standard_deviation,
            "standard_error":
                statistic.standard_error,
            "confidence_interval_95": {
                "lower": ci[0],
                "upper": ci[1],
            },
        }

    def _replication_report(self, report):
        """
        Convert registered numeric metrics into replication summaries.

        Each replicated metric becomes:

            mean
            standard_deviation
            standard_error
            confidence_interval_95

        Metrics that are not registered in ReplicationResults
        remain unchanged.
        """

        results = self.model.replication_results

        if results is None or results.count <= 1:
            return report

        def convert(value, key_parts):

            # ------------------------------------------
            # Dictionaries
            # ------------------------------------------

            if isinstance(value, dict):
                converted = {}

                for key, item in value.items():

                    child_key = (
                        f"{key_parts}.{key}"
                        if key_parts
                        else key
                    )

                    converted[key] = convert(
                        item,
                        child_key,
                    )

                return converted

            # ------------------------------------------
            # Booleans
            # ------------------------------------------

            if isinstance(value, bool):
                return value

            # ------------------------------------------
            # Numeric values
            # ------------------------------------------

            if isinstance(value, (int, float)):

                statistic = self._replication_statistic(
                    key_parts
                )

                if statistic is None:
                    return value

                ci = statistic.confidence_interval_95

                return {
                    "mean": statistic.mean,
                    "standard_deviation":
                        statistic.standard_deviation,
                    "standard_error":
                        statistic.standard_error,
                    "confidence_interval_95": {
                        "lower": ci[0],
                        "upper": ci[1],
                    },
                }

            return value

        converted = {}

        for category, category_data in report.items():

            # Experiment metadata is not a performance metric.
            if category in {
                "simulation_time",
                "warmup",
                "observation_time",
            }:
                converted[category] = category_data
                continue

            converted[category] = convert(
                category_data,
                category,
            )

        return converted

    # --------------------------------------------------
    # Formatting helpers
    # --------------------------------------------------

    def _is_replication_summary(self, value):
        return (
            isinstance(value, dict)
            and "mean" in value
            and "standard_deviation" in value
            and "standard_error" in value
            and "confidence_interval_95" in value
        )

    def _format_value(self, value):

        if isinstance(value, bool):
            return str(value)

        if isinstance(value, int):
            return f"{value:,}"

        if isinstance(value, float):

            if abs(value) < 0.01:
                return f"{value:,.5f}"

            if abs(value) < 1:
                return f"{value:,.4f}"

            return f"{value:,.3f}"

        return str(value)

    def _add_metric_columns(self, table):

        table.add_column(
            "Metric",
            style="bold",
        )

        if self._has_replications():

            table.add_column(
                "Mean",
                justify="right",
            )

            table.add_column(
                "Std. Dev.",
                justify="right",
            )

            table.add_column(
                "Std. Error",
                justify="right",
            )

            table.add_column(
                "95% CI",
                justify="right",
            )

        else:

            table.add_column(
                "Value",
                justify="right",
            )

    def _add_metric_row(
        self,
        table,
        label,
        value,
    ):

        if (
            self._has_replications()
            and self._is_replication_summary(value)
        ):

            ci = value["confidence_interval_95"]

            table.add_row(
                label,
                self._format_value(
                    value["mean"]
                ),
                self._format_value(
                    value["standard_deviation"]
                ),
                self._format_value(
                    value["standard_error"]
                ),
                (
                    f"{self._format_value(ci['lower'])}"
                    f" – "
                    f"{self._format_value(ci['upper'])}"
                ),
            )

        else:

            table.add_row(
                label,
                self._format_value(value),
            )

    # --------------------------------------------------
    # Standard Rich table
    # --------------------------------------------------

    def _new_table(self):
        return Table(
            show_header=True,
            header_style="bold",
            expand=True,
        )

    # --------------------------------------------------
    # Statistic table
    # --------------------------------------------------

    def _statistic_table(
        self,
        statistic,
        extended=False,
    ):

        table = self._new_table()

        self._add_metric_columns(table)

        self._add_metric_row(
            table,
            "Count",
            statistic["count"],
        )

        self._add_metric_row(
            table,
            "Total",
            statistic["total"],
        )

        self._add_metric_row(
            table,
            "Mean",
            statistic["mean"],
        )

        if extended:

            self._add_metric_row(
                table,
                "Minimum",
                statistic["minimum"],
            )

            self._add_metric_row(
                table,
                "Maximum",
                statistic["maximum"],
            )

            self._add_metric_row(
                table,
                "Variance",
                statistic["variance"],
            )

            self._add_metric_row(
                table,
                "Standard deviation",
                statistic["standard_deviation"],
            )

            self._add_metric_row(
                table,
                "P50",
                statistic["percentile_50"],
            )

            self._add_metric_row(
                table,
                "P90",
                statistic["percentile_90"],
            )

            self._add_metric_row(
                table,
                "P95",
                statistic["percentile_95"],
            )

            self._add_metric_row(
                table,
                "P99",
                statistic["percentile_99"],
            )

        return table

    # --------------------------------------------------
    # Entity breakdown table
    # --------------------------------------------------

    def _entity_breakdown_table(
        self,
        breakdown,
        extended=False,
    ):

        table = self._new_table()

        table.add_column(
            "Entity",
            style="bold",
        )

        table.add_column(
            "Count",
            justify="right",
        )

        table.add_column(
            "Total",
            justify="right",
        )

        table.add_column(
            "Mean",
            justify="right",
        )

        if extended:

            table.add_column(
                "Min",
                justify="right",
            )

            table.add_column(
                "Max",
                justify="right",
            )

            table.add_column(
                "Variance",
                justify="right",
            )

            table.add_column(
                "Std. Dev.",
                justify="right",
            )

            table.add_column(
                "P50",
                justify="right",
            )

            table.add_column(
                "P90",
                justify="right",
            )

            table.add_column(
                "P95",
                justify="right",
            )

            table.add_column(
                "P99",
                justify="right",
            )

        for entity_type, stats in breakdown.items():

            row = [
                str(entity_type),
                self._format_value(
                    stats["count"]
                ),
                self._format_value(
                    stats["total"]
                ),
                self._format_value(
                    stats["mean"]
                ),
            ]

            if extended:

                row.extend([
                    self._format_value(
                        stats["minimum"]
                    ),
                    self._format_value(
                        stats["maximum"]
                    ),
                    self._format_value(
                        stats["variance"]
                    ),
                    self._format_value(
                        stats["standard_deviation"]
                    ),
                    self._format_value(
                        stats["percentile_50"]
                    ),
                    self._format_value(
                        stats["percentile_90"]
                    ),
                    self._format_value(
                        stats["percentile_95"]
                    ),
                    self._format_value(
                        stats["percentile_99"]
                    ),
                ])

            table.add_row(*row)

        return table

    # --------------------------------------------------
    # Resource
    # --------------------------------------------------

    def _resource_panel(
        self,
        name,
        data,
    ):

        table = self._new_table()

        self._add_metric_columns(table)

        self._add_metric_row(
            table,
            "Capacity",
            data["capacity"],
        )

        self._add_metric_row(
            table,
            "Busy units",
            data["busy_count"],
        )

        self._add_metric_row(
            table,
            "Available units",
            data["available_capacity"],
        )

        self._add_metric_row(
            table,
            "Average busy",
            data["average_busy"],
        )

        self._add_metric_row(
            table,
            "Peak busy",
            data["peak_busy"],
        )

        self._add_metric_row(
            table,
            "Utilization",
            data["utilization"],
        )

        self._add_metric_row(
            table,
            "Busy time",
            data["busy_time"],
        )

        self._add_metric_row(
            table,
            "Idle time",
            data["idle_time"],
        )

        return Panel(
            table,
            title=f"RESOURCE: {name}",
        )

    # --------------------------------------------------
    # Source
    # --------------------------------------------------

    def _source_panel(
        self,
        name,
        data,
    ):

        table = self._new_table()

        self._add_metric_columns(table)

        self._add_metric_row(
            table,
            "Entities created",
            data["created"],
        )

        return Panel(
            table,
            title=f"SOURCE: {name}",
        )

    # --------------------------------------------------
    # Queue
    # --------------------------------------------------

    def _queue_panel(
        self,
        name,
        data,
        entity_breakdown,
        group,
        extended,
    ):

        parts = []

        # ----------------------------------------------
        # Overview
        # ----------------------------------------------

        overview = self._new_table()

        self._add_metric_columns(overview)

        self._add_metric_row(
            overview,
            "Average queue length",
            data["average_length"],
        )

        self._add_metric_row(
            overview,
            "Maximum queue length",
            data["maximum_length"],
        )

        self._add_metric_row(
            overview,
            "Time empty",
            data["time_empty"],
        )

        self._add_metric_row(
            overview,
            "Time nonempty",
            data["time_nonempty"],
        )

        self._add_metric_row(
            overview,
            "Occupancy",
            data["occupancy"],
        )

        self._add_metric_row(
            overview,
            "Average waiting time",
            data["average_waiting_time"],
        )

        parts.append(
            Panel(
                overview,
                title="Overview",
            )
        )

        # ----------------------------------------------
        # Nonempty periods
        # ----------------------------------------------

        periods = data["nonempty_periods"]

        period_table = self._new_table()

        self._add_metric_columns(period_table)

        self._add_metric_row(
            period_table,
            "Number of periods",
            periods["count"],
        )

        self._add_metric_row(
            period_table,
            "Average period",
            periods["average"],
        )

        self._add_metric_row(
            period_table,
            "Maximum period",
            periods["maximum"],
        )

        parts.append(
            Panel(
                period_table,
                title="Nonempty Periods",
            )
        )

        # ----------------------------------------------
        # Extended statistics
        # ----------------------------------------------

        if extended:

            parts.append(
                Panel(
                    self._statistic_table(
                        data["waiting_time_statistics"],
                        extended=True,
                    ),
                    title="Waiting Time Statistics",
                )
            )

        # ----------------------------------------------
        # Entity breakdown
        # ----------------------------------------------

        if entity_breakdown:

            parts.append(
                Panel(
                    self._entity_breakdown_table(
                        data["waiting_time_by_entity"],
                        extended=extended,
                    ),
                    title=(
                        f"Waiting Time by {group}"
                    ),
                )
            )

        return Panel(
            Group(*parts),
            title=f"QUEUE: {name}",
        )

    # --------------------------------------------------
    # Server
    # --------------------------------------------------

    def _server_panel(
        self,
        name,
        data,
        entity_breakdown,
        group,
        extended,
    ):

        parts = []

        # ----------------------------------------------
        # Overview
        # ----------------------------------------------

        overview = self._new_table()

        self._add_metric_columns(overview)

        self._add_metric_row(
            overview,
            "Entities processed",
            data["processed"],
        )

        self._add_metric_row(
            overview,
            "Utilization",
            data["utilization"],
        )

        self._add_metric_row(
            overview,
            "Busy time",
            data["busy_time"],
        )

        self._add_metric_row(
            overview,
            "Idle time",
            data["idle_time"],
        )

        self._add_metric_row(
            overview,
            "Average service time",
            data["average_service_time"],
        )

        self._add_metric_row(
            overview,
            "Average waiting time",
            data["average_waiting_time"],
        )

        parts.append(
            Panel(
                overview,
                title="Overview",
            )
        )

        # ----------------------------------------------
        # Busy / idle periods
        # ----------------------------------------------

        busy = data["busy_periods"]
        idle = data["idle_periods"]

        period_table = self._new_table()

        period_table.add_column(
            "State",
            style="bold",
        )

        if self._has_replications():

            period_table.add_column(
                "Periods",
                justify="right",
            )

            period_table.add_column(
                "Average",
                justify="right",
            )

            period_table.add_column(
                "Maximum",
                justify="right",
            )

        else:

            period_table.add_column(
                "Periods",
                justify="right",
            )

            period_table.add_column(
                "Average",
                justify="right",
            )

            period_table.add_column(
                "Maximum",
                justify="right",
            )

        period_table.add_row(
            "Busy",
            self._format_value(
                busy["count"]
            ),
            self._format_value(
                busy["average"]
            ),
            self._format_value(
                busy["maximum"]
            ),
        )

        period_table.add_row(
            "Idle",
            self._format_value(
                idle["count"]
            ),
            self._format_value(
                idle["average"]
            ),
            self._format_value(
                idle["maximum"]
            ),
        )

        parts.append(
            Panel(
                period_table,
                title="Busy / Idle Periods",
            )
        )

        # ----------------------------------------------
        # Extended statistics
        # ----------------------------------------------

        if extended:

            parts.append(
                Panel(
                    self._statistic_table(
                        data["service_time_statistics"],
                        extended=True,
                    ),
                    title="Service Time Statistics",
                )
            )

            parts.append(
                Panel(
                    self._statistic_table(
                        data["waiting_time_statistics"],
                        extended=True,
                    ),
                    title="Waiting Time Statistics",
                )
            )

        # ----------------------------------------------
        # Entity breakdown
        # ----------------------------------------------

        if entity_breakdown:

            parts.append(
                Panel(
                    self._entity_breakdown_table(
                        data["service_time_by_entity"],
                        extended=extended,
                    ),
                    title=(
                        f"Service Time by {group}"
                    ),
                )
            )

            parts.append(
                Panel(
                    self._entity_breakdown_table(
                        data["waiting_time_by_entity"],
                        extended=extended,
                    ),
                    title=(
                        f"Waiting Time by {group}"
                    ),
                )
            )

        return Panel(
            Group(*parts),
            title=f"SERVER: {name}",
        )

    # --------------------------------------------------
    # Sink
    # --------------------------------------------------

    def _sink_panel(
        self,
        name,
        data,
        entity_breakdown,
        group,
        extended,
    ):

        parts = []

        # ----------------------------------------------
        # Overview
        # ----------------------------------------------

        overview = self._new_table()

        self._add_metric_columns(overview)

        self._add_metric_row(
            overview,
            "Entities completed",
            data["completed"],
        )

        self._add_metric_row(
            overview,
            "Throughput",
            data["throughput"],
        )

        self._add_metric_row(
            overview,
            "Average flow time",
            data["average_flow_time"],
        )

        self._add_metric_row(
            overview,
            "Average waiting time",
            data["average_waiting_time"],
        )

        self._add_metric_row(
            overview,
            "Average service time",
            data["average_service_time"],
        )

        self._add_metric_row(
            overview,
            "Average other time",
            data["average_other_time"],
        )

        parts.append(
            Panel(
                overview,
                title="Overview",
            )
        )

        # ----------------------------------------------
        # Flow-time decomposition
        # ----------------------------------------------

        decomposition = self._new_table()

        decomposition.add_column(
            "Component",
            style="bold",
        )

        decomposition.add_column(
            "Average",
            justify="right",
        )

        decomposition.add_column(
            "% of flow time",
            justify="right",
        )

        flow_time = data["average_flow_time"]

        components = [
            (
                "Waiting time",
                data["average_waiting_time"],
            ),
            (
                "Service time",
                data["average_service_time"],
            ),
            (
                "Other time",
                data["average_other_time"],
            ),
        ]

        if self._has_replications():

            flow_mean = flow_time["mean"]

            for label, value in components:

                value_mean = value["mean"]

                percentage = (
                    value_mean / flow_mean * 100
                    if flow_mean > 0
                    else 0.0
                )

                decomposition.add_row(
                    label,
                    self._format_value(
                        value_mean
                    ),
                    f"{percentage:.2f}%",
                )

            decomposition.add_row(
                "Total flow time",
                self._format_value(
                    flow_mean
                ),
                (
                    "100.00%"
                    if flow_mean > 0
                    else "0.00%"
                ),
            )

        else:

            for label, value in components:

                percentage = (
                    value / flow_time * 100
                    if flow_time > 0
                    else 0.0
                )

                decomposition.add_row(
                    label,
                    self._format_value(value),
                    f"{percentage:.2f}%",
                )

            decomposition.add_row(
                "Total flow time",
                self._format_value(flow_time),
                (
                    "100.00%"
                    if flow_time > 0
                    else "0.00%"
                ),
            )

        parts.append(
            Panel(
                decomposition,
                title="Flow Time Decomposition",
            )
        )

        # ----------------------------------------------
        # Extended statistics
        # ----------------------------------------------

        if extended:

            parts.append(
                Panel(
                    self._statistic_table(
                        data["flow_time_statistics"],
                        extended=True,
                    ),
                    title="Flow Time Statistics",
                )
            )

            parts.append(
                Panel(
                    self._statistic_table(
                        data["waiting_time_statistics"],
                        extended=True,
                    ),
                    title="Waiting Time Statistics",
                )
            )

            parts.append(
                Panel(
                    self._statistic_table(
                        data["service_time_statistics"],
                        extended=True,
                    ),
                    title="Service Time Statistics",
                )
            )

            parts.append(
                Panel(
                    self._statistic_table(
                        data["other_time_statistics"],
                        extended=True,
                    ),
                    title="Other Time Statistics",
                )
            )

        # ----------------------------------------------
        # Entity breakdown
        # ----------------------------------------------

        if entity_breakdown:

            if "flow_time_by_entity" in data:

                parts.append(
                    Panel(
                        self._entity_breakdown_table(
                            data["flow_time_by_entity"],
                            extended=extended,
                        ),
                        title="Flow Time by Entity",
                    )
                )

            if "waiting_time_by_entity" in data:

                parts.append(
                    Panel(
                        self._entity_breakdown_table(
                            data["waiting_time_by_entity"],
                            extended=extended,
                        ),
                        title="Waiting Time by Entity",
                    )
                )

            if "service_time_by_entity" in data:

                parts.append(
                    Panel(
                        self._entity_breakdown_table(
                            data["service_time_by_entity"],
                            extended=extended,
                        ),
                        title="Service Time by Entity",
                    )
                )

            if "other_time_by_entity" in data:

                parts.append(
                    Panel(
                        self._entity_breakdown_table(
                            data["other_time_by_entity"],
                            extended=extended,
                        ),
                        title="Other Time by Entity",
                    )
                )

            if "completed_by_entity" in data:

                parts.append(
                    Panel(
                        self._entity_breakdown_table(
                            data["completed_by_entity"],
                            extended=False,
                        ),
                        title="Completed by Entity",
                    )
                )

            if "throughput_by_entity" in data:

                parts.append(
                    Panel(
                        self._entity_breakdown_table(
                            data["throughput_by_entity"],
                            extended=False,
                        ),
                        title="Throughput by Entity",
                    )
                )

        return Panel(
            Group(*parts),
            title=f"SINK: {name}",
        )

    # --------------------------------------------------
    # Report
    # --------------------------------------------------

    def report(
        self,
        entity_breakdown=False,
        group="entity_type",
        extended=False,
    ):

        simulation_time = self.model.simulation.time
        warmup = self.model.warmup
        observation_time = self.model.observation_time

        result = {
            "simulation_time": simulation_time,
            "warmup": warmup,
            "observation_time": observation_time,
            "sources": {},
            "queues": {},
            "servers": {},
            "resources": {},
            "sinks": {},
        }

        # --------------------------------------------------
        # Atoms
        # --------------------------------------------------

        for atom in self.model.atoms:

            # --------------------------------------------------
            # Source
            # --------------------------------------------------

            if atom.__class__.__name__ == "Source":

                result["sources"][atom.name] = {
                    "created": atom.entities_created,
                }

            # --------------------------------------------------
            # Queue
            # --------------------------------------------------

            elif atom.__class__.__name__ == "Queue":

                waiting_time = atom.stats.waiting_time
                queue_length = atom.stats.queue_length

                data = {
                    "average_length":
                        atom.average_length,

                    "maximum_length":
                        atom.maximum_length,

                    "time_empty":
                        queue_length.time_zero(
                            simulation_time
                        ),

                    "time_nonempty":
                        queue_length.time_nonzero(
                            simulation_time
                        ),

                    "occupancy":
                        queue_length.occupancy(
                            simulation_time
                        ),

                    "average_waiting_time":
                        atom.average_waiting_time,

                    "waiting_time_statistics":
                        self._statistic_summary(
                            waiting_time,
                            extended=extended,
                        ),
                }

                nonempty_periods = (
                    queue_length.periods_nonzero(
                        simulation_time
                    )
                )

                data["nonempty_periods"] = {
                    "count": len(nonempty_periods),

                    "average":
                        (
                            sum(nonempty_periods)
                            / len(nonempty_periods)
                            if nonempty_periods
                            else 0.0
                        ),

                    "maximum":
                        (
                            max(nonempty_periods)
                            if nonempty_periods
                            else 0.0
                        ),
                }

                if entity_breakdown:

                    data[
                        "waiting_time_by_entity"
                    ] = self._entity_breakdown(
                        waiting_time,
                        group,
                    )

                result["queues"][atom.name] = data

            # --------------------------------------------------
            # Server
            # --------------------------------------------------

            elif atom.__class__.__name__ == "Server":

                waiting_time = atom.stats.waiting_time
                service_time = atom.stats.service_time
                occupancy = atom.stats.server_occupancy

                busy_periods = (
                    occupancy.periods_nonzero(
                        simulation_time
                    )
                )

                idle_periods = (
                    occupancy.period_durations(
                        lambda value: value == 0,
                        simulation_time,
                    )
                )

                data = {
                    "processed":
                        atom.processed,

                    "utilization":
                        occupancy.occupancy(
                            simulation_time
                        ),

                    "busy_time":
                        occupancy.time_nonzero(
                            simulation_time
                        ),

                    "idle_time":
                        occupancy.time_zero(
                            simulation_time
                        ),

                    "busy_periods": {
                        "count": len(busy_periods),

                        "average":
                            (
                                sum(busy_periods)
                                / len(busy_periods)
                                if busy_periods
                                else 0.0
                            ),

                        "maximum":
                            (
                                max(busy_periods)
                                if busy_periods
                                else 0.0
                            ),
                    },

                    "idle_periods": {
                        "count": len(idle_periods),

                        "average":
                            (
                                sum(idle_periods)
                                / len(idle_periods)
                                if idle_periods
                                else 0.0
                            ),

                        "maximum":
                            (
                                max(idle_periods)
                                if idle_periods
                                else 0.0
                            ),
                    },

                    "average_service_time":
                        atom.average_service_time,

                    "average_waiting_time":
                        atom.stats.waiting_time.mean,

                    "service_time_statistics":
                        self._statistic_summary(
                            service_time,
                            extended=extended,
                        ),

                    "waiting_time_statistics":
                        self._statistic_summary(
                            waiting_time,
                            extended=extended,
                        ),
                }

                if entity_breakdown:

                    data[
                        "waiting_time_by_entity"
                    ] = self._entity_breakdown(
                        waiting_time,
                        group,
                    )

                    data[
                        "service_time_by_entity"
                    ] = self._entity_breakdown(
                        service_time,
                        group,
                    )

                result["servers"][atom.name] = data

            # --------------------------------------------------
            # Sink
            # --------------------------------------------------

            elif atom.__class__.__name__ == "Sink":

                flow_time = atom.stats.flow_time
                waiting_time = atom.stats.waiting_time
                service_time = atom.stats.service_time
                other_time = atom.stats.other_time

                data = {
                    "completed":
                        atom.entities_received,

                    "throughput":
                        self.throughput(atom),

                    "average_flow_time":
                        flow_time.mean,

                    "average_waiting_time":
                        waiting_time.mean,

                    "average_service_time":
                        service_time.mean,

                    "average_other_time":
                        other_time.mean,

                    "flow_time_statistics":
                        self._statistic_summary(
                            flow_time,
                            extended=extended,
                        ),

                    "waiting_time_statistics":
                        self._statistic_summary(
                            waiting_time,
                            extended=extended,
                        ),

                    "service_time_statistics":
                        self._statistic_summary(
                            service_time,
                            extended=extended,
                        ),

                    "other_time_statistics":
                        self._statistic_summary(
                            other_time,
                            extended=extended,
                        ),
                }

                if entity_breakdown:

                    data[
                        "flow_time_by_entity"
                    ] = self._entity_breakdown(
                        flow_time,
                        group,
                    )

                    data[
                        "waiting_time_by_entity"
                    ] = self._entity_breakdown(
                        waiting_time,
                        group,
                    )

                    data[
                        "service_time_by_entity"
                    ] = self._entity_breakdown(
                        service_time,
                        group,
                    )

                    data[
                        "other_time_by_entity"
                    ] = self._entity_breakdown(
                        other_time,
                        group,
                    )

                    data[
                        "completed_by_entity"
                    ] = flow_time.grouped_count(
                        group
                    )

                    data[
                        "throughput_by_entity"
                    ] = atom.throughput_by(
                        group
                    )

                result["sinks"][atom.name] = data

        # --------------------------------------------------
        # Resources
        # --------------------------------------------------

        for atom in self.model.atoms:

            if isinstance(atom, Resource):

                result["resources"][atom.name] = {
                    "capacity":
                        atom.capacity,

                    "busy_count":
                        atom.busy_count,

                    "available_capacity":
                        atom.available_capacity,

                    "average_busy":
                        atom.average_busy,

                    "peak_busy":
                        atom.peak_busy,

                    "utilization":
                        atom.utilization,

                    "busy_time":
                        atom.busy_time,

                    "idle_time":
                        atom.idle_time,
                }

        # --------------------------------------------------
        # Replication conversion
        # --------------------------------------------------

        if self._has_replications():
            return self._replication_report(result)

        return result

    # --------------------------------------------------
    # Export
    # --------------------------------------------------

    def export(
        self,
        filename,
        format=None,
        entity_breakdown=False,
        group="entity_type",
        extended=False,
    ):

        report = self.report(
            entity_breakdown=entity_breakdown,
            group=group,
            extended=extended,
        )

        if format is None:

            if "." in filename:

                format = (
                    filename
                    .rsplit(".", 1)[1]
                    .lower()
                )

            else:

                raise ValueError(
                    "Could not determine export format. "
                    "Specify format='json' or format='csv'."
                )

        # --------------------------------------------------
        # JSON
        # --------------------------------------------------

        if format == "json":

            with open(
                filename,
                "w",
                encoding="utf-8",
            ) as file:

                json.dump(
                    report,
                    file,
                    indent=4,
                )

        # --------------------------------------------------
        # CSV
        # --------------------------------------------------

        elif format == "csv":

            rows = []

            def add_rows(
                category,
                atom_name,
                value,
                prefix="",
            ):

                if isinstance(value, dict):

                    # Replication summary
                    if self._is_replication_summary(
                        value
                    ):

                        ci = value[
                            "confidence_interval_95"
                        ]

                        rows.extend([
                            {
                                "category": category,
                                "atom": atom_name,
                                "statistic":
                                    f"{prefix}mean",
                                "group": "",
                                "value":
                                    value["mean"],
                            },
                            {
                                "category": category,
                                "atom": atom_name,
                                "statistic":
                                    f"{prefix}"
                                    "standard_deviation",
                                "group": "",
                                "value":
                                    value[
                                        "standard_deviation"
                                    ],
                            },
                            {
                                "category": category,
                                "atom": atom_name,
                                "statistic":
                                    f"{prefix}"
                                    "standard_error",
                                "group": "",
                                "value":
                                    value[
                                        "standard_error"
                                    ],
                            },
                            {
                                "category": category,
                                "atom": atom_name,
                                "statistic":
                                    f"{prefix}"
                                    "confidence_interval_lower",
                                "group": "",
                                "value":
                                    ci["lower"],
                            },
                            {
                                "category": category,
                                "atom": atom_name,
                                "statistic":
                                    f"{prefix}"
                                    "confidence_interval_upper",
                                "group": "",
                                "value":
                                    ci["upper"],
                            },
                        ])

                        return

                    for key, item in value.items():

                        if isinstance(item, dict):

                            add_rows(
                                category,
                                atom_name,
                                item,
                                prefix=(
                                    f"{prefix}{key}_"
                                ),
                            )

                        else:

                            rows.append({
                                "category":
                                    category,

                                "atom":
                                    atom_name,

                                "statistic":
                                    f"{prefix}"
                                    f"{key}",

                                "group":
                                    "",

                                "value":
                                    item,
                            })

                else:

                    rows.append({
                        "category":
                            category,

                        "atom":
                            atom_name,

                        "statistic":
                            prefix.rstrip("_"),

                        "group":
                            "",

                        "value":
                            value,
                    })

            for category, atoms in report.items():

                if not isinstance(atoms, dict):
                    continue

                for name, statistics in atoms.items():

                    for statistic, value in (
                        statistics.items()
                    ):

                        add_rows(
                            category,
                            name,
                            value,
                            prefix=(
                                f"{statistic}_"
                                if isinstance(
                                    value,
                                    dict,
                                )
                                else statistic
                            ),
                        )

            with open(
                filename,
                "w",
                newline="",
                encoding="utf-8",
            ) as file:

                writer = csv.DictWriter(
                    file,
                    fieldnames=[
                        "category",
                        "atom",
                        "statistic",
                        "group",
                        "value",
                    ],
                )

                writer.writeheader()
                writer.writerows(rows)

        else:

            raise ValueError(
                f"Unsupported format: {format!r}. "
                "Use 'json' or 'csv'."
            )

        return filename

    # --------------------------------------------------
    # Rich report
    # --------------------------------------------------

    def print_report(
        self,
        entity_breakdown=False,
        group="entity_type",
        extended=False,
    ):

        report = self.report(
            entity_breakdown=entity_breakdown,
            group=group,
            extended=extended,
        )

        console = self.console

        console.print()

        # --------------------------------------------------
        # Header
        # --------------------------------------------------

        header = Table(
            title="QUEUENAMICS SIMULATION REPORT",
            show_header=True,
        )

        header.add_column(
            "Metric",
            style="bold",
        )

        header.add_column(
            "Value",
            justify="right",
        )

        header.add_row(
            "Total simulation time",
            self._format_value(
                report["simulation_time"]
            ),
        )

        header.add_row(
            "Warm-up",
            self._format_value(
                report["warmup"]
            ),
        )

        header.add_row(
            "Observation time",
            self._format_value(
                report["observation_time"]
            ),
        )

        if self._has_replications():

            header.add_row(
                "Replications",
                self._format_value(
                    self.model.replication_results.count
                ),
            )

        console.print(header)
        console.print()

        # --------------------------------------------------
        # Sources
        # --------------------------------------------------

        if report["sources"]:

            console.print(
                "[bold]SOURCES[/bold]"
            )

            for name, data in (
                report["sources"].items()
            ):

                console.print(
                    self._source_panel(
                        name,
                        data,
                    )
                )

            console.print()

        # --------------------------------------------------
        # Queues
        # --------------------------------------------------

        if report["queues"]:

            console.print(
                "[bold]QUEUES[/bold]"
            )

            for name, data in (
                report["queues"].items()
            ):

                console.print(
                    self._queue_panel(
                        name,
                        data,
                        entity_breakdown,
                        group,
                        extended,
                    )
                )

            console.print()

        # --------------------------------------------------
        # Servers
        # --------------------------------------------------

        if report["servers"]:

            console.print(
                "[bold]SERVERS[/bold]"
            )

            for name, data in (
                report["servers"].items()
            ):

                console.print(
                    self._server_panel(
                        name,
                        data,
                        entity_breakdown,
                        group,
                        extended,
                    )
                )

            console.print()

        # --------------------------------------------------
        # Sinks
        # --------------------------------------------------

        if report["sinks"]:

            console.print(
                "[bold]SINKS[/bold]"
            )

            for name, data in (
                report["sinks"].items()
            ):

                console.print(
                    self._sink_panel(
                        name,
                        data,
                        entity_breakdown,
                        group,
                        extended,
                    )
                )

            console.print()

        # --------------------------------------------------
        # Resources
        # --------------------------------------------------

        if report["resources"]:

            console.print(
                "[bold]RESOURCES[/bold]"
            )

            for name, data in (
                report["resources"].items()
            ):

                console.print(
                    self._resource_panel(
                        name,
                        data,
                    )
                )

            console.print()