import heapq
import sys
import time as time_module


class Event:
    def __init__(self, time, action):
        self.time = time
        self.action = action

    def execute(self):
        self.action()


class ProgressBar:
    def __init__(self, total, width=40):
        self.total = total
        self.width = width
        self.start_time = time_module.perf_counter()
        self.last_percentage = -1

    def update(self, current, events_processed):
        if self.total <= 0:
            return

        percentage = min(current / self.total, 1.0)

        # Only redraw every 1%
        percentage_int = int(percentage * 100)

        if percentage_int == self.last_percentage:
            return

        self.last_percentage = percentage_int

        filled = int(self.width * percentage)
        bar = "█" * filled + "░" * (self.width - filled)

        elapsed = time_module.perf_counter() - self.start_time

        if percentage > 0:
            estimated_total = elapsed / percentage
            remaining = max(estimated_total - elapsed, 0)
        else:
            remaining = 0

        sys.stdout.write(
            "\r"
            f"Simulation: [{bar}] "
            f"{percentage * 100:6.2f}% "
            f"| Time: {current:,.2f}/{self.total:,.2f} "
            f"| Events: {events_processed:,} "
            f"| ETA: {self._format_time(remaining)}"
        )

        sys.stdout.flush()

    @staticmethod
    def _format_time(seconds):
        if seconds < 1:
            return "<1s"

        if seconds < 60:
            return f"{seconds:.0f}s"

        minutes = int(seconds // 60)
        seconds = int(seconds % 60)

        if minutes < 60:
            return f"{minutes}m {seconds:02d}s"

        hours = minutes // 60
        minutes = minutes % 60

        return f"{hours}h {minutes:02d}m"


class Simulation:
    def __init__(self):
        self.time = 0.0
        self.events = []
        self._event_counter = 0
        self.running = False
        self.events_processed = 0

    def schedule(self, time, action):
        event = Event(time, action)

        heapq.heappush(
            self.events,
            (event.time, self._event_counter, event)
        )

        self._event_counter += 1

    def run(self, until, progress=True):
        self.running = True
        self.events_processed = 0

        progress_bar = ProgressBar(until) if progress else None

        # Print immediately so the user knows the simulation started
        if progress_bar is not None:
            progress_bar.update(0, 0)

        while self.events and self.running:

            if self.events[0][0] > until:
                break

            time, _, event = heapq.heappop(self.events)

            self.time = time

            event.execute()

            self.events_processed += 1

            if progress_bar is not None:
                progress_bar.update(
                    self.time,
                    self.events_processed
                )

        self.time = until

        if progress_bar is not None:
            progress_bar.update(
                until,
                self.events_processed
            )

            sys.stdout.write("\n")
            sys.stdout.flush()

        self.running = False

    def stop(self):
        self.running = False

    def reset(self):
        self.time = 0.0
        self.events.clear()
        self._event_counter = 0
        self.events_processed = 0
        self.running = False