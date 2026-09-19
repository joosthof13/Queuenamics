# Queuenamics

**Python-native discrete-event simulation and queueing.**

[![TestPyPI](https://img.shields.io/pypi/v/queuenamics.svg)](https://test.pypi.org/project/queuenamics/)
[![License](https://img.shields.io/github/license/joosthof13/Queuenamics.svg)](https://github.com/joosthof13/Queuenamics)

Queuenamics is a Python library for building, simulating, and analyzing **queueing systems, service processes, and operational models**.

Define your model in Python, run discrete-event simulations, and analyze system performance.

```text
Source → Queue → Server → Sink
```

## Installation

```bash
pip install queuenamics
```

## Quick start

```python
from queuenamics import (
    Model,
    Source,
    Queue,
    Server,
    Sink,
    Exponential,
    FIFO,
)

customers = Source(
    "Customers",
    arrival=Exponential(5),
)

queue = Queue(
    "Waiting Line",
    discipline=FIFO(),
)

cashier = Server(
    "Cashier",
    service=Exponential(6),
)

exit = Sink("Exit")

model = Model(seed=42)

model.connect(customers, queue)
model.connect(queue, cashier)
model.connect(cashier, exit)

model.run(time=10_000)

model.stats.print_report()
```

Models follow a simple workflow:

**DEFINE → CONNECT → VALIDATE → RUN → ANALYZE → EXPERIMENT**

---

## Features

### Simulation

* Discrete-event simulation
* Sources, queues, servers, sinks, and resources
* Multiple and heterogeneous servers
* Entity types and custom attributes
* Reproducible simulations with random seeds
* Automatic model validation
* Warm-up periods

### Queueing & routing

* FIFO, LIFO, priority, and shortest-processing-time disciplines
* Conditional, attribute-based, and entity-type routing
* First-available and random-available routing
* Shared resources and capacity constraints

### Distributions

```python
Constant(...)
Exponential(...)
Uniform(...)
Poisson(...)
```

Additional probability distributions are available for stochastic model components.

### Statistics

Collect and analyze:

* Queue length
* Waiting time
* Service time
* Utilization
* Throughput
* Mean, median, minimum, and maximum
* Quartiles and arbitrary percentiles
* Variance and standard deviation
* Grouped statistics
* Time-weighted statistics

```python
model.stats.print_report()
```

Reports can be exported to JSON or CSV.

### Experiments

Run independent replications and quantify simulation uncertainty:

```python
from queuenamics import Experiment

experiment = Experiment(
    model_factory=create_model,
    replications=30,
    time=10_000,
    warmup=1_000,
)

results = experiment.run()

results.mean("sinks.Exit.throughput")
results.confidence_interval("sinks.Exit.throughput")
```

### Parameter sweeps

Evaluate different model configurations automatically:

```python
from queuenamics import ParameterSweep

sweep = ParameterSweep(
    model_factory=create_model,
    parameters={
        "arrival_rate": [4, 5, 6],
        "service_rate": [5, 6, 7],
    },
    replications=10,
    time=5_000,
)

results = sweep.run()
```

Structural parameters such as the number of servers can also be swept.

---

## Visualization

Queuenamics provides lightweight visualization using Matplotlib and NetworkX.

```python
from queuenamics import (
    plot_model,
    plot_queue_length,
    plot_server_utilization,
    plot_throughput,
)

plot_model(model)
plot_queue_length(queue)
plot_server_utilization(cashier)
plot_throughput(exit)
```

---

## Why Queuenamics?

Queuenamics is **Python-native by design**.

Models are ordinary Python objects, making them:

* **Reproducible** — keep models and experiments in version control.
* **Programmable** — use Python logic throughout the model.
* **Experimentable** — automate replications and parameter studies.
* **Transparent** — the model structure is visible directly in code.
* **Extensible** — integrate simulation with Python's scientific ecosystem.

```text
Python model
     ↓
Discrete-event simulation
     ↓
Statistics & experiments
     ↓
Analysis & decisions
```

---

## Example applications

Queuenamics can be used to model:

* Customer service systems
* Manufacturing processes
* Healthcare systems
* Logistics and transportation
* Call centers
* Repair and maintenance systems
* Capacity planning
* Queueing theory experiments
* Operational research studies

---

## Requirements

* Python **3.10+**
* [Matplotlib](https://matplotlib.org/)
* [NetworkX](https://networkx.org/)

---

## Documentation

Documentation and examples are available in the project repository.

For a quick overview of the API, see the `examples/` directory.

---

## Development

```bash
git clone https://github.com/joosthof13/Queuenamics.git
cd Queuenamics

python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install in editable mode:

```bash
pip install -e .
```

Run the test suite:

```bash
python -m pytest -q
```

---

## Project status

**Current version: 0.8.4**

Queuenamics is currently suitable for:

**learning · research · prototyping · operational analysis · queueing studies · discrete-event simulation**

The project is actively developed toward a stable **0.9.0** release.

---

## Contributing

Contributions, bug reports, tests, documentation, and new modelling components are welcome.

Please run the test suite before submitting changes:

```bash
python -m pytest -q
```

---

## License

Queuenamics is released under the **MIT License**.

See [`LICENSE`](LICENSE) for details.

---

> **Build operational processes in Python. Simulate them as discrete events. Analyze their performance.**
