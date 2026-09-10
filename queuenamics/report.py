import csv
import json

class StatisticsReport:

    def __init__(self, model):
        self.model = model

    def utilization(self, server):
        simulation_time = self.model.simulation.time

        if simulation_time <= 0:
            return 0.0

        busy_time = server.busy_time

        if server.busy and server.service_start_time is not None:
            busy_time += (
                simulation_time
                - server.service_start_time
            )

        return busy_time / simulation_time

    def throughput(self, sink):
        simulation_time = self.model.simulation.time

        if simulation_time <= 0:
            return 0.0

        return sink.entities_received / simulation_time

    def report(self):

        result = {
            "simulation_time": self.model.simulation.time,
            "sources": {},
            "queues": {},
            "servers": {},
            "sinks": {},
        }

        for atom in self.model.atoms:

            if atom.__class__.__name__ == "Source":

                result["sources"][atom.name] = {
                    "created": atom.entities_created,
                }

            elif atom.__class__.__name__ == "Queue":

                result["queues"][atom.name] = {
                    "average_length":
                        atom.average_length,

                    "maximum_length":
                        atom.maximum_length,

                    "average_waiting_time":
                        atom.average_waiting_time,
                }

            elif atom.__class__.__name__ == "Server":

                result["servers"][atom.name] = {
                    "processed":
                        atom.processed,

                    "utilization":
                        self.utilization(atom),

                    "average_service_time":
                        atom.average_service_time,
                }

            elif atom.__class__.__name__ == "Sink":

                result["sinks"][atom.name] = {
                    "completed":
                        atom.entities_received,

                    "throughput":
                        self.throughput(atom),
                }

        return result
    
    def export(self, filename, format=None):

        report = self.report()

        if format is None:

            if "." in filename:
                format = filename.rsplit(".", 1)[1].lower()
            else:
                raise ValueError(
                    "Could not determine export format. "
                    "Specify format='json' or format='csv'."
                )

        if format == "json":

            with open(
                filename,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    report,
                    file,
                    indent=4
                )

        elif format == "csv":

            rows = []

            for category, atoms in report.items():

                if category == "simulation_time":
                    continue

                for name, statistics in atoms.items():

                    for statistic, value in statistics.items():

                        rows.append({
                            "category": category,
                            "atom": name,
                            "statistic": statistic,
                            "value": value,
                        })

            with open(
                filename,
                "w",
                newline="",
                encoding="utf-8"
            ) as file:

                writer = csv.DictWriter(
                    file,
                    fieldnames=[
                        "category",
                        "atom",
                        "statistic",
                        "value",
                    ]
                )

                writer.writeheader()
                writer.writerows(rows)

        else:

            raise ValueError(
                f"Unsupported export format: {format!r}. "
                "Use 'json' or 'csv'."
            )

        return filename

    def format_report(self):

        report = self.report()

        width = 64
        lines = []

        lines.append("=" * width)
        lines.append(
            "QUEUENAMICS SIMULATION REPORT".center(width)
        )
        lines.append("=" * width)

        lines.append("")
        lines.append("MODEL")
        lines.append("-" * width)

        lines.append(
            f"  {'Simulation time':<32}"
            f"{report['simulation_time']:>14,.2f}"
        )

        lines.append("")

        if report["sources"]:

            lines.append("SOURCES")
            lines.append("-" * width)

            for name, data in report["sources"].items():

                lines.append(f"  {name}")

                lines.append(
                    f"    {'Entities created':<28}"
                    f"{data['created']:>14,}"
                )

        if report["queues"]:

            lines.append("")
            lines.append("QUEUES")
            lines.append("-" * width)

            for name, data in report["queues"].items():

                lines.append(f"  {name}")

                lines.append(
                    f"    {'Average queue length':<28}"
                    f"{data['average_length']:>14,.3f}"
                )

                lines.append(
                    f"    {'Maximum queue length':<28}"
                    f"{data['maximum_length']:>14,.0f}"
                )

                lines.append(
                    f"    {'Average waiting time':<28}"
                    f"{data['average_waiting_time']:>14,.3f}"
                )

        if report["servers"]:

            lines.append("")
            lines.append("SERVERS")
            lines.append("-" * width)

            for name, data in report["servers"].items():

                lines.append(f"  {name}")

                lines.append(
                    f"    {'Entities processed':<28}"
                    f"{data['processed']:>14,}"
                )

                lines.append(
                    f"    {'Utilization':<28}"
                    f"{data['utilization'] * 100:>13.2f}%"
                )

                lines.append(
                    f"    {'Average service time':<28}"
                    f"{data['average_service_time']:>14,.3f}"
                )

        if report["sinks"]:

            lines.append("")
            lines.append("SINKS")
            lines.append("-" * width)

            for name, data in report["sinks"].items():

                lines.append(f"  {name}")

                lines.append(
                    f"    {'Entities completed':<28}"
                    f"{data['completed']:>14,}"
                )

                lines.append(
                    f"    {'Throughput':<28}"
                    f"{data['throughput']:>14,.3f}"
                )

        lines.append("")
        lines.append("=" * width)

        return "\n".join(lines)

    def print_report(self):

        print(self.format_report())