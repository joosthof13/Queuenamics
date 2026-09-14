# Queuenamics

**Python-native discrete-event simulation and queueing models.**

Queuenamics is a Python library for building, simulating, and analyzing **queueing systems, service processes, and operational models**.

Build models with ordinary Python code:

**DEFINE → CONNECT → VALIDATE → RUN → ANALYZE → EXPERIMENT**

```text
Source → Queue → Server → Sink
```

## Features

* Discrete-event simulation
* Sources, queues, servers, sinks, and resources
* FIFO, LIFO, priority, and shortest-processing-time queues
* Multiple and heterogeneous servers
* Entity types and custom attributes
* Conditional and attribute-based routing
* Random and availability-based routing
* Exponential, constant, uniform, and Poisson distributions
* Reproducible simulations with random seeds
* Queue, waiting-time, service-time, utilization, and throughput statistics
* Percentiles, quartiles, variance, and standard deviation
* Grouped statistics
* Exact time-weighted statistics
* Multiple replications and confidence intervals
* Experiments and parameter sweeps
* Structural sweeps over atom counts
* Warm-up periods
* Model and result visualization
* JSON and CSV export

---

## Installation

```bash
pip install queuenamics
```

```python
import queuenamics

print(queuenamics.__version__)
```

---

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

waiting_line = Queue(
    "Waiting Line",
    discipline=FIFO(),
)

cashier = Server(
    "Cashier",
    service=Exponential(6),
)

exit = Sink("Exit")

model = Model(seed=42)

model.connect(customers, waiting_line)
model.connect(waiting_line, cashier)
model.connect(cashier, exit)

model.run(time=10_000)

model.stats.print_report()
```

The resulting system is:

```text
Customers → Waiting Line → Cashier → Exit
```

---

# Core concepts

### Entities

Entities represent objects moving through the system:

```python
entity.attributes["priority"] = 2
```

Sources can create entities with types and attributes:

```python
patients = Source(
    "Patients",
    arrival=Exponential(20),
    entity_type="patient",
    attributes={"priority": 1},
)
```

### Atoms

Atoms are the components of a model:

```text
Source
Queue
Server
Sink
Resource
```

### Connections

Connections define the process structure:

```python
model.connect(source, queue)
model.connect(queue, server)
model.connect(server, sink)
```

### Model

A `Model` contains the simulation network and random-number generator:

```python
model = Model(seed=42)
```

---

# Probability distributions

```python
from queuenamics import (
    Constant,
    Exponential,
    Uniform,
    Poisson,
)
```

Examples:

```python
Exponential(5)
Constant(2)
Uniform(5, 10)
Poisson(5)
```

Stochastic components use the model's seeded random-number generator, allowing simulations to be reproduced.

---

# Queue disciplines

Queuenamics supports:

```python
FIFO()
LIFO()

Priority(
    attribute="priority",
    highest_first=True,
)

ShortestProcessingTime(
    attribute="service_time",
)
```

For example:

```python
queue = Queue(
    "Priority Queue",
    discipline=Priority(
        attribute="priority",
        highest_first=True,
    ),
)
```

---

# Multiple servers

Servers can share a queue:

```python
queue = Queue("Waiting Line")

server_1 = Server(
    "Server 1",
    service=Exponential(6),
)

server_2 = Server(
    "Server 2",
    service=Exponential(6),
)

model.connect(queue, server_1)
model.connect(queue, server_2)
```

This creates a pooled-server system:

```text
                 ┌→ Server 1 ─┐
Queue ───────────┤             ├→ ...
                 └→ Server 2 ─┘
```

Servers may use different service distributions.

---

# Resources

Resources represent limited shared capacity:

```python
from queuenamics import Resource

technicians = Resource(
    "Technicians",
    capacity=3,
)

repair = Server(
    "Repair Station",
    service=Exponential(4),
    resource=technicians,
)
```

Resources can represent technicians, machines, nurses, forklifts, operating rooms, and other capacity constraints.

---

# Routing

Routing determines where entities go next.

Available routers include:

```python
FirstAvailable()
RandomAvailable()

EntityTypeRouter(...)
AttributeRouter(...)
ConditionalRouter(...)
```

Example:

```python
queue = Queue(
    "Customer Queue",
    router=EntityTypeRouter(
        routes={
            "regular": 0,
            "urgent": 1,
        },
    ),
)
```

Conditional routing allows arbitrary Python logic:

```python
router = ConditionalRouter(
    conditions=[
        (
            lambda entity:
            entity.attributes.get("priority", 0) >= 3,
            0,
        ),
    ],
    default=1,
)
```

---

# Statistics

Statistics are available directly from the model:

```python
report = model.stats.report()

model.stats.print_report()
```

The statistics system includes:

* Mean, minimum, and maximum
* Median and quartiles
* Arbitrary percentiles
* IQR
* Population and sample variance
* Population and sample standard deviation
* Grouped statistics
* Time-weighted statistics
* Queue length
* Waiting time
* Service time
* Server utilization
* Throughput

Example:

```python
statistic = Statistic()

for value in [5, 10, 15]:
    statistic.record(value)

print(statistic.mean)
print(statistic.median)
print(statistic.standard_deviation)
```

---

# Replications and experiments

A single stochastic simulation is only one realization. `Experiment` runs multiple independent replications.

```python
from queuenamics import Experiment

def create_model(seed):
    model = Model(seed=seed)

    # Build model...

    return model

experiment = Experiment(
    model_factory=create_model,
    replications=30,
    time=10_000,
    warmup=1_000,
)

results = experiment.run()
```

Results can be analyzed directly:

```python
results.mean("sinks.Exit.throughput")

results.standard_deviation(
    "sinks.Exit.throughput"
)

results.standard_error(
    "sinks.Exit.throughput"
)

results.confidence_interval(
    "sinks.Exit.throughput"
)
```

Custom metrics are also supported:

```python
results.mean(
    lambda model: model.some_metric
)
```

---

# Parameter sweeps

`ParameterSweep` evaluates combinations of model parameters.

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

Each combination is simulated independently.

Results can be compared and optimized:

```python
best = results.best(
    "queues.Waiting Line.average_waiting_time",
    maximize=False,
)
```

## Atom-count sweeps

Structural parameters can also be varied.

For example, test between 1 and 5 cashiers:

```python
sweep = ParameterSweep(
    model_factory=create_model,
    parameters={
        "service_rate": [5, 6, 7],
    },
    atom_counts={
        "Cashier": range(1, 6),
    },
    replications=10,
    time=5_000,
)
```

The model factory receives the atom count through:

```python
params["atoms"]["Cashier"]
```

This makes capacity studies straightforward:

```python
for i in range(params["atoms"]["Cashier"]):
    cashier = Server(
        f"Cashier {i + 1}",
        service=Exponential(
            params["service_rate"]
        ),
    )
```

You can then search for the best configuration:

```python
best = results.best(
    "queues.Waiting Line.average_waiting_time",
    maximize=False,
)
```

---

# Warm-up periods

Warm-up time can be excluded from statistical observation:

```python
experiment = Experiment(
    model_factory=create_model,
    replications=30,
    time=10_000,
    warmup=1_000,
)
```

The simulation continues running during the warm-up; statistics are collected after the observation period begins.

---

# Export

Simulation reports can be exported as JSON or CSV:

```python
model.stats.export("results.json")
model.stats.export("results.csv")
```

Experiment and parameter-sweep results can also be exported for further analysis.

---

# Visualization

Queuenamics provides lightweight visualization through Matplotlib and NetworkX:

```python
from queuenamics import (
    plot_model,
    plot_queue_length,
    plot_server_utilization,
    plot_throughput,
)

plot_model(model)
plot_queue_length(waiting_line)
plot_server_utilization(cashier)
plot_throughput(exit)
```

Plots can also be generated without displaying them:

```python
plot_queue_length(
    waiting_line,
    show=False,
)
```

---

# Validation

Models can be validated before simulation:

```python
validation = model.validate()

if not validation["valid"]:
    print(validation["errors"])
```

`model.run()` validates automatically by default:

```python
model.run(time=10_000)
```

Validation can be disabled when needed:

```python
model.run(
    time=10_000,
    validate=False,
)
```

---

# Examples

The `examples/` directory contains models demonstrating:

* Basic queues
* Multiple servers
* Heterogeneous servers
* Priority queues
* Entity attributes
* Routing
* Resources
* Replications
* Experiments
* Parameter sweeps
* Visualization
* Result export

---

# Design philosophy

Queuenamics is **Python-native by design**.

Models are represented as Python objects rather than being locked inside a graphical modelling environment.

This makes them:

* **Reproducible** — models and experiments can live in version control.
* **Programmable** — Python logic can be used throughout the model.
* **Experimentable** — simulations can be automated and parameterized.
* **Transparent** — the process structure is visible in code.
* **Extensible** — Python can be used to build custom modelling and analysis functionality.

The goal is simple:

> **Keep the modelling API simple while making the simulation engine powerful.**

---

# Project status

**Current version: 0.8.3**

### 0.8.3 — Experiments & Analysis

The current release adds a dedicated experiment and analysis layer:

* Multiple simulation replications
* Warm-up periods
* `ExperimentResults`
* Replication statistics
* Standard errors
* Student-t confidence intervals
* Metric extraction and discovery
* Result comparison
* JSON and CSV export
* Parameter sweeps
* Structural atom-count sweeps
* Best-configuration search
* Sweep filtering and comparison

Queuenamics is currently suited for:

**learning · research · prototyping · operational analysis · queueing studies · discrete-event simulation**

---

# Development

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

Run tests:

```bash
python -m pytest -q
```

---

# Project structure

```text
Queuenamics/
├── queuenamics/
│   ├── __init__.py
│   ├── atoms.py
│   ├── disciplines.py
│   ├── distributions.py
│   ├── entities.py
│   ├── experiment.py
│   ├── model.py
│   ├── report.py
│   ├── routing.py
│   ├── simulation.py
│   ├── stats.py
│   └── visualization.py
│
├── tests/
├── examples/
├── README.md
├── LICENSE
└── pyproject.toml
```

## Requirements

* Python **3.10+**
* Matplotlib
* NetworkX

---

# Roadmap

| Version   | Focus                             | Status  |
| --------- | --------------------------------- | ------- |
| 0.8.2     | Statistics                        | ✅       |
| **0.8.3** | **Experiments & Analysis**        | **✅**   |
| 0.8.4     | Model Persistence (`.qnm`)        | Planned |
| 0.8.5     | Visualization & UX                | Planned |
| 0.9.0     | API stabilization & documentation | Planned |

---

# Contributing

Contributions, bug reports, ideas, tests, and new modelling components are welcome.

Before submitting changes:

```bash
python -m pytest -q
```

Useful areas include:

* Simulation performance
* Statistics
* Routing
* Resources
* Queue disciplines
* Visualization
* Experiments
* Documentation
* Tests

---

# License

Queuenamics is released under the **MIT License**.

See [`LICENSE`](LICENSE) for the full license text.

---

> **Queuenamics lets you build operational processes as Python models, simulate them as discrete events, and analyze the resulting system performance.**
