import csv
import json
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich import box

class StatisticsReport:
    def __init__(self, model):
        self.model = model
        self.console = Console()

    def throughput(self, sink):
        observation_time = self.model.observation_time
        if observation_time <= 0:
            return 0.0
        return sink.entities_received / observation_time
        
    # --------------------------------------------------
    # Statistic helpers
    # --------------------------------------------------

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
                "sinks": {},
            }

            for atom in self.model.atoms:

                # --------------------------------------------------
                # SOURCE
                # --------------------------------------------------

                if atom.__class__.__name__ == "Source":

                    result["sources"][atom.name] = {
                        "created": atom.entities_created,
                    }

                # --------------------------------------------------
                # QUEUE
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
                        data["waiting_time_by_entity"] = (
                            self._entity_breakdown(
                                waiting_time,
                                group,
                            )
                        )

                    result["queues"][atom.name] = data

                # --------------------------------------------------
                # SERVER
                # --------------------------------------------------

                elif atom.__class__.__name__ == "Server":

                    waiting_time = atom.stats.waiting_time
                    service_time = atom.stats.service_time
                    occupancy = atom.stats.server_occupancy

                    busy_periods = occupancy.periods_nonzero(
                        simulation_time
                    )

                    idle_periods = occupancy.period_durations(
                        lambda value: value == 0,
                        simulation_time,
                    )

                    data = {
                        "processed": atom.processed,

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
                        data["waiting_time_by_entity"] = (
                            self._entity_breakdown(
                                waiting_time,
                                group,
                            )
                        )

                        data["service_time_by_entity"] = (
                            self._entity_breakdown(
                                service_time,
                                group,
                            )
                        )

                    result["servers"][atom.name] = data

                # --------------------------------------------------
                # SINK
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
                        data["flow_time_by_entity"] = (
                            self._entity_breakdown(
                                flow_time,
                                group,
                            )
                        )

                        data["waiting_time_by_entity"] = (
                            self._entity_breakdown(
                                waiting_time,
                                group,
                            )
                        )

                        data["service_time_by_entity"] = (
                            self._entity_breakdown(
                                service_time,
                                group,
                            )
                        )

                        data["other_time_by_entity"] = (
                            self._entity_breakdown(
                                other_time,
                                group,
                            )
                        )

                        data["completed_by_entity"] = (
                            flow_time.grouped_count(group)
                        )

                        data["throughput_by_entity"] = (
                            atom.throughput_by(group)
                        )

                    result["sinks"][atom.name] = data

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
        extended=False
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

                    for key, item in value.items():

                        if isinstance(item, dict):

                            for statistic, statistic_value in (
                                item.items()
                            ):

                                rows.append({
                                    "category":
                                        category,

                                    "atom":
                                        atom_name,

                                    "statistic":
                                        f"{prefix}{statistic}",

                                    "group":
                                        key,

                                    "value":
                                        statistic_value,
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
                                    key,

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
                                if isinstance(value, dict)
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
                f"Unsupported export format: {format!r}. "
                "Use 'json' or 'csv'."
            )

        return filename
    
    # --------------------------------------------------
    # Replication statistics
    # --------------------------------------------------

    def _replication_statistics(self):
        """
        Return replication-level statistics for the main
        performance measures.

        Replication statistics are only available after
        Model.run(..., replications > 1).
        """
        results = getattr(self.model, "replication_results", None)

        if results is None:
            return None

        # Find sink-level replication metrics.
        # These are the same metrics that are already shown
        # in the normal sink report.
        statistics = {}

        for atom in self.model.atoms:
            if atom.__class__.__name__ != "Sink":
                continue

            sink_name = atom.name

            for metric, label in [
                ("average_flow_time", "Average flow time"),
                ("average_waiting_time", "Average waiting time"),
                ("average_service_time", "Average service time"),
                ("average_other_time", "Average other time"),
                ("throughput", "Throughput"),
            ]:
                key = f"sinks.{sink_name}.{metric}"

                try:
                    statistic = results.statistic(key)
                except (KeyError, ValueError, AttributeError):
                    continue

                if statistic is not None:
                    statistics[label] = statistic

        return statistics

    def _replication_panel(self):
        """
        Create a Rich panel containing replication-level
        standard deviation, standard error and 95% CI.

        The mean is intentionally omitted because the normal
        simulation report already displays the replication mean.
        """
        statistics = self._replication_statistics()

        if not statistics:
            return None

        table = Table(
            box=box.SIMPLE,
            expand=True,
        )

        table.add_column(
            "Metric",
            style="bold",
        )

        table.add_column(
            "Std. deviation",
            justify="right",
        )

        table.add_column(
            "Std. error",
            justify="right",
        )

        table.add_column(
            "95% CI",
            justify="right",
        )

        for label, statistic in statistics.items():
            ci = statistic.confidence_interval_95

            table.add_row(
                label,
                f"{statistic.standard_deviation:,.3f}",
                f"{statistic.standard_error:,.3f}",
                f"[{ci[0]:,.3f}, {ci[1]:,.3f}]",
            )

        return Panel(
            table,
            title="[bold]REPLICATION STATISTICS[/bold]",
            border_style="magenta",
            padding=(1, 1),
        )

    # --------------------------------------------------
    # Rich formatting helpers
    # --------------------------------------------------

    def _statistic_table(
        self,
        statistic,
        extended=False,
    ):
        table = Table(
            box=box.SIMPLE,
            show_header=False,
            padding=(0, 1),
            expand=True,
        )

        table.add_column(
            "Statistic",
            style="bold",
        )

        table.add_column(
            "Value",
            justify="right",
        )

        table.add_row(
            "Count",
            f"{statistic['count']:,}",
        )

        table.add_row(
            "Total",
            f"{statistic['total']:,.3f}",
        )

        table.add_row(
            "Mean",
            f"{statistic['mean']:,.3f}",
        )

        if extended:
            table.add_row(
                "Minimum",
                f"{statistic['minimum']:,.3f}",
            )

            table.add_row(
                "Maximum",
                f"{statistic['maximum']:,.3f}",
            )

            table.add_row(
                "Variance",
                f"{statistic['variance']:,.3f}",
            )

            table.add_row(
                "Standard deviation",
                f"{statistic['standard_deviation']:,.3f}",
            )

            table.add_row(
                "P50",
                f"{statistic['percentile_50']:,.3f}",
            )

            table.add_row(
                "P90",
                f"{statistic['percentile_90']:,.3f}",
            )

            table.add_row(
                "P95",
                f"{statistic['percentile_95']:,.3f}",
            )

            table.add_row(
                "P99",
                f"{statistic['percentile_99']:,.3f}",
            )

        return table

    def _entity_breakdown_table(
        self,
        breakdown,
        extended=False,
    ):
        table = Table(
            box=box.SIMPLE,
            expand=True,
        )

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
                "Std Dev",
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
                f"{stats['count']:,}",
                f"{stats['total']:,.3f}",
                f"{stats['mean']:,.3f}",
            ]

            if extended:
                row.extend([
                    f"{stats['minimum']:,.3f}",
                    f"{stats['maximum']:,.3f}",
                    f"{stats['variance']:,.3f}",
                    f"{stats['standard_deviation']:,.3f}",
                    f"{stats['percentile_50']:,.3f}",
                    f"{stats['percentile_90']:,.3f}",
                    f"{stats['percentile_95']:,.3f}",
                    f"{stats['percentile_99']:,.3f}",
                ])

            table.add_row(*row)

        return table

    # --------------------------------------------------
    # Atom panels
    # --------------------------------------------------

    def _source_panel(self, name, data):
        table = Table(
            box=box.SIMPLE,
            show_header=False,
            expand=True,
        )

        table.add_column(
            "Metric",
            style="bold",
        )

        table.add_column(
            "Value",
            justify="right",
        )

        table.add_row(
            "Entities created",
            f"{data['created']:,}",
        )

        return Panel(
            table,
            title=f"[bold]SOURCE: {name}[/bold]",
            border_style="blue",
        )

    def _queue_panel(
        self,
        name,
        data,
        entity_breakdown,
        group,
        extended,
    ):
        parts = []

        # --------------------------------------------------
        # Overview
        # --------------------------------------------------

        overview = Table(
            box=box.SIMPLE,
            show_header=False,
            expand=True,
        )

        overview.add_column(
            "Metric",
            style="bold",
        )

        overview.add_column(
            "Value",
            justify="right",
        )

        overview.add_row(
            "Average queue length",
            f"{data['average_length']:,.3f}",
        )

        overview.add_row(
            "Maximum queue length",
            f"{data['maximum_length']:,.0f}",
        )

        overview.add_row(
            "Time empty",
            f"{data['time_empty']:,.3f}",
        )

        overview.add_row(
            "Time nonempty",
            f"{data['time_nonempty']:,.3f}",
        )

        overview.add_row(
            "Occupancy",
            f"{data['occupancy'] * 100:.2f}%",
        )

        overview.add_row(
            "Average waiting time",
            f"{data['average_waiting_time']:,.3f}",
        )

        parts.append(
            Panel(
                overview,
                title="Overview",
                border_style="cyan",
            )
        )

        # --------------------------------------------------
        # Nonempty periods
        # --------------------------------------------------

        periods = data["nonempty_periods"]

        period_table = Table(
            box=box.SIMPLE,
            show_header=False,
            expand=True,
        )

        period_table.add_column(
            "Metric",
            style="bold",
        )

        period_table.add_column(
            "Value",
            justify="right",
        )

        period_table.add_row(
            "Number of nonempty periods",
            f"{periods['count']:,}",
        )

        period_table.add_row(
            "Average nonempty period",
            f"{periods['average']:,.3f}",
        )

        period_table.add_row(
            "Maximum nonempty period",
            f"{periods['maximum']:,.3f}",
        )

        parts.append(
            Panel(
                period_table,
                title="Queue Occupancy Periods",
                border_style="cyan",
            )
        )

        # --------------------------------------------------
        # Extended statistics
        # --------------------------------------------------

        if extended:
            parts.append(
                Panel(
                    self._statistic_table(
                        data["waiting_time_statistics"],
                        extended=True,
                    ),
                    title="Waiting Time Statistics",
                    border_style="cyan",
                )
            )

        # --------------------------------------------------
        # Entity breakdown
        # --------------------------------------------------

        if entity_breakdown:
            parts.append(
                Panel(
                    self._entity_breakdown_table(
                        data["waiting_time_by_entity"],
                        extended=extended,
                    ),
                    title=(
                        "Waiting Time by "
                        f"{group}"
                    ),
                    border_style="magenta",
                )
            )

        return Panel(
            Group(*parts),
            title=f"[bold]QUEUE: {name}[/bold]",
            border_style="blue",
            padding=(1, 1),
        )

    def _server_panel(
        self,
        name,
        data,
        entity_breakdown,
        group,
        extended,
    ):
        parts = []

        # --------------------------------------------------
        # Overview
        # --------------------------------------------------

        overview = Table(
            box=box.SIMPLE,
            show_header=False,
            expand=True,
        )

        overview.add_column(
            "Metric",
            style="bold",
        )

        overview.add_column(
            "Value",
            justify="right",
        )

        overview.add_row(
            "Entities processed",
            f"{data['processed']:,}",
        )

        overview.add_row(
            "Utilization",
            f"{data['utilization'] * 100:.2f}%",
        )

        overview.add_row(
            "Busy time",
            f"{data['busy_time']:,.3f}",
        )

        overview.add_row(
            "Idle time",
            f"{data['idle_time']:,.3f}",
        )

        overview.add_row(
            "Average service time",
            f"{data['average_service_time']:,.3f}",
        )

        overview.add_row(
            "Average waiting time",
            f"{data['average_waiting_time']:,.3f}",
        )

        parts.append(
            Panel(
                overview,
                title="Overview",
                border_style="cyan",
            )
        )

        # --------------------------------------------------
        # Busy / idle periods
        # --------------------------------------------------

        busy = data["busy_periods"]
        idle = data["idle_periods"]

        period_table = Table(
            box=box.SIMPLE,
            expand=True,
        )

        period_table.add_column(
            "State",
            style="bold",
        )

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
            f"{busy['count']:,}",
            f"{busy['average']:,.3f}",
            f"{busy['maximum']:,.3f}",
        )

        period_table.add_row(
            "Idle",
            f"{idle['count']:,}",
            f"{idle['average']:,.3f}",
            f"{idle['maximum']:,.3f}",
        )

        parts.append(
            Panel(
                period_table,
                title="Busy / Idle Periods",
                border_style="green",
            )
        )

        # --------------------------------------------------
        # Extended statistics
        # --------------------------------------------------

        if extended:
            parts.append(
                Panel(
                    self._statistic_table(
                        data["service_time_statistics"],
                        extended=True,
                    ),
                    title="Service Time Statistics",
                    border_style="green",
                )
            )

            parts.append(
                Panel(
                    self._statistic_table(
                        data["waiting_time_statistics"],
                        extended=True,
                    ),
                    title="Waiting Time Statistics",
                    border_style="cyan",
                )
            )

        # --------------------------------------------------
        # Entity breakdown
        # --------------------------------------------------

        if entity_breakdown:
            parts.append(
                Panel(
                    self._entity_breakdown_table(
                        data["service_time_by_entity"],
                        extended=extended,
                    ),
                    title=(
                        "Service Time by "
                        f"{group}"
                    ),
                    border_style="green",
                )
            )

            parts.append(
                Panel(
                    self._entity_breakdown_table(
                        data["waiting_time_by_entity"],
                        extended=extended,
                    ),
                    title=(
                        "Waiting Time by "
                        f"{group}"
                    ),
                    border_style="magenta",
                )
            )

        return Panel(
            Group(*parts),
            title=f"[bold]SERVER: {name}[/bold]",
            border_style="green",
            padding=(1, 1),
        )

    def _sink_panel(
        self,
        name,
        data,
        entity_breakdown,
        group,
        extended,
    ):
        parts = []

        # --------------------------------------------------
        # Overview
        # --------------------------------------------------

        overview = Table(
            box=box.SIMPLE,
            show_header=False,
            expand=True,
        )

        overview.add_column(
            "Metric",
            style="bold",
        )

        overview.add_column(
            "Value",
            justify="right",
        )

        overview.add_row(
            "Entities completed",
            f"{data['completed']:,}",
        )

        overview.add_row(
            "Throughput",
            f"{data['throughput']:,.3f}",
        )

        overview.add_row(
            "Average flow time",
            f"{data['average_flow_time']:,.3f}",
        )

        overview.add_row(
            "Average waiting time",
            f"{data['average_waiting_time']:,.3f}",
        )

        overview.add_row(
            "Average service time",
            f"{data['average_service_time']:,.3f}",
        )

        overview.add_row(
            "Average other time",
            f"{data['average_other_time']:,.3f}",
        )

        parts.append(
            Panel(
                overview,
                title="Overview",
                border_style="cyan",
            )
        )

        # --------------------------------------------------
        # Flow-time decomposition
        # --------------------------------------------------

        decomposition = Table(
            box=box.SIMPLE,
            expand=True,
        )

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

        for label, value in components:
            percentage = (
                value / flow_time * 100
                if flow_time > 0
                else 0.0
            )

            decomposition.add_row(
                label,
                f"{value:,.3f}",
                f"{percentage:.2f}%",
            )

        decomposition.add_row(
            "Total flow time",
            f"{flow_time:,.3f}",
            "100.00%" if flow_time > 0 else "0.00%",
        )

        parts.append(
            Panel(
                decomposition,
                title="Flow Time Decomposition",
                border_style="yellow",
            )
        )

        # --------------------------------------------------
        # Extended statistics
        # --------------------------------------------------

        if extended:
            parts.append(
                Panel(
                    self._statistic_table(
                        data["flow_time_statistics"],
                        extended=True,
                    ),
                    title="Flow Time Statistics",
                    border_style="yellow",
                )
            )

            parts.append(
                Panel(
                    self._statistic_table(
                        data["waiting_time_statistics"],
                        extended=True,
                    ),
                    title="Waiting Time Statistics",
                    border_style="cyan",
                )
            )

            parts.append(
                Panel(
                    self._statistic_table(
                        data["service_time_statistics"],
                        extended=True,
                    ),
                    title="Service Time Statistics",
                    border_style="green",
                )
            )

            parts.append(
                Panel(
                    self._statistic_table(
                        data["other_time_statistics"],
                        extended=True,
                    ),
                    title="Other Time Statistics",
                    border_style="magenta",
                )
            )

        # --------------------------------------------------
        # Entity breakdown
        # --------------------------------------------------

        if entity_breakdown:
            parts.append(
                Panel(
                    self._entity_breakdown_table(
                        data["flow_time_by_entity"],
                        extended=extended,
                    ),
                    title=(
                        "Flow Time by "
                        f"{group}"
                    ),
                    border_style="yellow",
                )
            )

            parts.append(
                Panel(
                    self._entity_breakdown_table(
                        data["waiting_time_by_entity"],
                        extended=extended,
                    ),
                    title=(
                        "Waiting Time by "
                        f"{group}"
                    ),
                    border_style="cyan",
                )
            )

            parts.append(
                Panel(
                    self._entity_breakdown_table(
                        data["service_time_by_entity"],
                        extended=extended,
                    ),
                    title=(
                        "Service Time by "
                        f"{group}"
                    ),
                    border_style="green",
                )
            )

            parts.append(
                Panel(
                    self._entity_breakdown_table(
                        data["other_time_by_entity"],
                        extended=extended,
                    ),
                    title=(
                        "Other Time by "
                        f"{group}"
                    ),
                    border_style="magenta",
                )
            )

            # --------------------------------------------------
            # Completed by entity
            # --------------------------------------------------

            completed_table = Table(
                box=box.SIMPLE,
                expand=True,
            )

            completed_table.add_column(
                "Entity",
                style="bold",
            )

            completed_table.add_column(
                "Completed",
                justify="right",
            )

            for (
                entity_type,
                count,
            ) in data["completed_by_entity"].items():

                completed_table.add_row(
                    str(entity_type),
                    f"{count:,}",
                )

            parts.append(
                Panel(
                    completed_table,
                    title=(
                        "Completed by "
                        f"{group}"
                    ),
                    border_style="blue",
                )
            )

            # --------------------------------------------------
            # Throughput by entity
            # --------------------------------------------------

            throughput_table = Table(
                box=box.SIMPLE,
                expand=True,
            )

            throughput_table.add_column(
                "Entity",
                style="bold",
            )

            throughput_table.add_column(
                "Throughput",
                justify="right",
            )

            for (
                entity_type,
                throughput,
            ) in data["throughput_by_entity"].items():

                throughput_table.add_row(
                    str(entity_type),
                    f"{throughput:,.3f}",
                )

            parts.append(
                Panel(
                    throughput_table,
                    title=(
                        "Throughput by "
                        f"{group}"
                    ),
                    border_style="blue",
                )
            )

        return Panel(
            Group(*parts),
            title=f"[bold]SINK: {name}[/bold]",
            border_style="yellow",
            padding=(1, 1),
        )

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
        # HEADER
        # --------------------------------------------------

        console.print(
            Panel(
                Group(
                    f"[bold]Total simulation time:[/bold] "
                    f"{report['simulation_time']:,.2f}",
                    f"[bold]Warm-up:[/bold] "
                    f"{report['warmup']:,.2f}",
                    f"[bold]Observation time:[/bold] "
                    f"{report['observation_time']:,.2f}",
                ),
                title="QUEUENAMICS SIMULATION REPORT",
                border_style="blue",
                expand=True,
            )
        )

        # --------------------------------------------------
        # SOURCES
        # --------------------------------------------------

        if report["sources"]:

            source_panels = []

            for name, data in report["sources"].items():
                source_panels.append(
                    self._source_panel(
                        name,
                        data,
                    )
                )

            console.print(
                Panel(
                    Group(*source_panels),
                    title="[bold]SOURCES[/bold]",
                    border_style="blue",
                )
            )

        # --------------------------------------------------
        # QUEUES
        # --------------------------------------------------

        if report["queues"]:

            queue_panels = []

            for name, data in report["queues"].items():
                queue_panels.append(
                    self._queue_panel(
                        name,
                        data,
                        entity_breakdown,
                        group,
                        extended,
                    )
                )

            console.print(
                Panel(
                    Group(*queue_panels),
                    title="[bold]QUEUES[/bold]",
                    border_style="blue",
                )
            )

        # --------------------------------------------------
        # SERVERS
        # --------------------------------------------------

        if report["servers"]:

            server_panels = []

            for name, data in report["servers"].items():
                server_panels.append(
                    self._server_panel(
                        name,
                        data,
                        entity_breakdown,
                        group,
                        extended,
                    )
                )

            console.print(
                Panel(
                    Group(*server_panels),
                    title="[bold]SERVERS[/bold]",
                    border_style="green",
                )
            )

        # --------------------------------------------------
        # SINKS
        # --------------------------------------------------

        if report["sinks"]:

            sink_panels = []

            for name, data in report["sinks"].items():
                sink_panels.append(
                    self._sink_panel(
                        name,
                        data,
                        entity_breakdown,
                        group,
                        extended,
                    )
                )

            console.print(
                Panel(
                    Group(*sink_panels),
                    title="[bold]SINKS[/bold]",
                    border_style="yellow",
                )
            )

        # --------------------------------------------------
        # REPLICATION STATISTICS
        # --------------------------------------------------

        replication_panel = self._replication_panel()

        if replication_panel is not None:
            console.print(replication_panel)

        console.print()