# Queuenamics

**Python-native discrete-event simulation and queueing models.**

Queuenamics is a Python library for building, simulating, analyzing, and experimenting with **queueing systems, service processes, and operational models**.

It is designed for situations where processes can be represented as entities moving through a network of queues, servers, resources, and decision points over simulated time.

The goal is to make discrete-event simulation accessible through ordinary Python code rather than a proprietary graphical modelling environment.

The core workflow is:

**DEFINE → CONNECT → VALIDATE → RUN → ANALYZE → EXPORT**

---

## Why Queuenamics?

Many operational systems can be described as:

> Entities arrive → wait → receive service → move to another process → eventually leave the system.

Examples include:

* hospitals and emergency departments
* call centers
* banks and service desks
* manufacturing systems
* logistics and warehouses
* production lines
* repair and maintenance systems
* transportation systems
* customer service processes
* computer and communication systems

Queuenamics provides the building blocks needed to represent these systems and study questions such as:

* How long do customers wait?
* How large does a queue become?
* How heavily utilized are servers?
* What happens when demand increases?
* How many servers are required?
* What happens when service times become more variable?
* How does a priority rule affect waiting times?
* What happens when several servers share a queue?
* How sensitive is system performance to a particular parameter?

---

## Core concepts

Queuenamics is built around a small number of modelling concepts.

### Entities

An **Entity** represents something moving through the system.

Examples include:

* customers
* patients
* jobs
* orders
* vehicles
* repair requests

Entities can have an `entity_type` and arbitrary attributes.

```python
entity = Entity(
    entity_type="urgent",
    creation_time=0,
)

entity.attributes["priority"] = 2
```

Sources can create entities with these properties automatically:

```python
patients = Source(
    "Patients",
    arrival=Exponential(20),
    entity_type="patient",
    attributes={"priority": 1},
)
```

Each generated entity receives its own copy of the attributes.

---

### Atoms

An **Atom** is a component of the simulation model.

Queuenamics currently provides:

* `Source`
* `Queue`
* `Server`
* `Sink`
* `Resource`

Atoms can be connected to form a process network.

```text
Source → Queue → Server → Sink
```

More complex models can contain multiple paths, shared queues, multiple servers, and different routing decisions.

---

### Connections

Connections define how entities move between atoms.

```python
model.connect(source, queue)
model.connect(queue, server)
model.connect(server, sink)
```

This separates the **definition of individual components** from the **structure of the process**.

---

### Model

The `Model` contains the atoms, connections, random-number generator, and simulation engine.

```python
model = Model(seed=42)
```

A model can then be validated and simulated:

```python
model.validate()
model.run(time=10_000)
```

---

## Features

Queuenamics currently supports:

* Discrete-event simulation
* Entity creation and flow
* Entity types and attributes
* Sources and sinks
* FIFO queues
* LIFO queues
* Priority queues
* Shortest-processing-time queues
* Multiple servers
* Shared queues
* Separate queues
* Heterogeneous servers
* Resources with capacities
* Routing
* Random routing
* Probability distributions
* Reproducible simulations through random seeds
* Queue-length statistics
* Waiting-time statistics
* Service-time statistics
* Server utilization
* Throughput measurements
* Model validation
* Multiple replications
* Experiments
* Parameter sweeps
* Confidence intervals
* Model visualization
* JSON export
* CSV export

---

# Installation

Install Queuenamics from PyPI:

```bash
pip install queuenamics
```

After installation:

```python
import queuenamics

print(queuenamics.__version__)
```

---

# Quick example

The following example models a simple single-server queue.

Customers arrive according to an exponential distribution with a rate of **5 customers per hour**. A cashier serves customers according to an exponential distribution with a rate of **6 customers per hour**.

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

The resulting model is:

```text
Customers → Waiting Line → Cashier → Exit
```

The simulation produces statistics including:

* average queue length
* maximum queue length
* average waiting time
* server utilization
* average service time
* throughput

---

# Modelling workflow

Queuenamics is designed around a simple workflow.

## 1. Define

Create the components of the system.

```python
customers = Source(
    "Customers",
    arrival=Exponential(5),
)

queue = Queue("Waiting Line")

cashier = Server(
    "Cashier",
    service=Exponential(6),
)

exit = Sink("Exit")
```

## 2. Connect

Define how entities move through the system.

```python
model.connect(customers, queue)
model.connect(queue, cashier)
model.connect(cashier, exit)
```

## 3. Validate

Check the model before running it.

```python
validation = model.validate()

if not validation["valid"]:
    raise RuntimeError(
        "Model validation failed:\n"
        + "\n".join(validation["errors"])
    )
```

`model.run()` performs validation automatically by default.

## 4. Run

Run the simulation for a specified amount of simulated time.

```python
model.run(time=10_000)
```

## 5. Analyze

Inspect the resulting statistics.

```python
report = model.stats.report()
```

Or print a human-readable report:

```python
model.stats.print_report()
```

## 6. Export

Export the results for further analysis.

```python
model.stats.export("results.json")
model.stats.export("results.csv")
```

---

# Probability distributions

Queuenamics currently provides several probability distributions:

```python
from queuenamics import (
    Constant,
    Exponential,
    Uniform,
    Poisson,
)
```

## Exponential

```python
arrival = Exponential(5)
```

This represents an exponential distribution with a rate of 5 events per unit of simulation time.

For example, when simulation time is measured in hours:

```python
Exponential(5)
```

represents an average arrival rate of 5 events per hour.

## Constant

```python
service = Constant(10 / 60)
```

This represents a fixed service time of 10 minutes when simulation time is measured in hours.

## Uniform

```python
service = Uniform(5, 10)
```

This produces values uniformly distributed between 5 and 10 units of simulation time.

## Poisson

```python
arrivals = Poisson(5)
```

Queuenamics also provides a Poisson distribution for discrete random values.

All stochastic distributions use the model's random-number generator, allowing simulations to be reproduced with a fixed seed.

---

# Queue disciplines

A queue determines which entity should be selected next.

## FIFO

First In, First Out:

```python
queue = Queue(
    "Waiting Line",
    discipline=FIFO(),
)
```

The oldest waiting entity is selected first.

## LIFO

Last In, First Out:

```python
queue = Queue(
    "Waiting Line",
    discipline=LIFO(),
)
```

The most recently added entity is selected first.

## Priority

Entities can be selected according to an attribute:

```python
queue = Queue(
    "Priority Queue",
    discipline=Priority(
        attribute="priority",
        highest_first=True,
    ),
)
```

For example:

```python
urgent = Source(
    "Urgent",
    arrival=Exponential(3),
    attributes={"priority": 2},
)

regular = Source(
    "Regular",
    arrival=Exponential(20),
    attributes={"priority": 1},
)
```

A higher priority value is selected first when `highest_first=True`.

## Shortest processing time

Entities can also be selected according to an attribute representing their expected processing time:

```python
queue = Queue(
    "SPT Queue",
    discipline=ShortestProcessingTime(
        attribute="service_time",
    ),
)
```

---

# Multiple servers

Multiple servers can share the same queue.

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

This represents a pooled-server system:

```text
                 ┌→ Server 1 ─┐
Queue ───────────┤             ├→ ...
                 └→ Server 2 ─┘
```

This structure is useful for modelling:

* hospital departments
* call centers
* bank counters
* service desks
* production stations
* repair facilities

Servers can also have different service distributions:

```python
server_1 = Server(
    "Fast Server",
    service=Constant(2 / 60),
)

server_2 = Server(
    "Slow Server",
    service=Constant(5 / 60),
)
```

---

# Resources

Resources represent limited-capacity assets that can be acquired and released.

```python
from queuenamics import Resource

resource = Resource(
    "Technicians",
    capacity=3,
)
```

Resources can be associated with servers:

```python
server = Server(
    "Repair Station",
    service=Exponential(4),
    resource=resource,
)
```

This makes it possible to represent systems where service depends on a limited shared resource.

---

# Routing

Queuenamics supports routing entities to available downstream components.

The default router is:

```python
FirstAvailable()
```

For example:

```python
queue = Queue(
    "Waiting Line",
)
```

A queue connected to multiple available servers can select the first available destination.

Randomized routing is also available:

```python
from queuenamics import RandomAvailable

queue = Queue(
    "Waiting Line",
    router=RandomAvailable(),
)
```

Random routing uses the model's seeded random-number generator, so it remains reproducible.

---

# Entity attributes

Entities can carry information through the model.

For example:

```python
patients = Source(
    "Patients",
    arrival=Exponential(20),
    entity_type="patient",
    attributes={
        "priority": 1,
        "patient_type": "regular",
    },
)
```

Attributes can then be used by queue disciplines such as `Priority`.

This allows the model to distinguish between different classes of entities without requiring separate models.

---

# Statistics and reporting

After a simulation has completed, statistics can be accessed programmatically:

```python
report = model.stats.report()
```

The report contains information about the model, sources, queues, servers, and sinks.

A formatted report can be printed directly:

```python
model.stats.print_report()
```

Typical measurements include:

### Queues

* average queue length
* maximum queue length
* average waiting time

### Servers

* entities processed
* utilization
* average service time

### Sources

* entities created

### Sinks

* entities completed
* throughput

Because the statistics are available as Python data structures, they can also be incorporated into custom analysis workflows.

---

# Exporting results

Simulation results can be exported to JSON or CSV.

```python
model.stats.export("results.json")
```

or:

```python
model.stats.export("results.csv")
```

JSON is useful when preserving the hierarchical report structure.

CSV is useful for importing results into:

* Excel
* pandas
* statistical software
* data-analysis pipelines

---

# Reproducibility

Stochastic simulations can be reproduced using a random seed.

```python
model = Model(seed=42)
```

The model's random-number generator is shared by the stochastic components of the model, including:

* probability distributions
* random queue disciplines
* random routing

This allows experiments to be repeated under controlled random conditions.

---

# Validation

Queuenamics can validate a model before simulation.

```python
validation = model.validate()
```

The result contains:

```python
{
    "valid": True,
    "errors": [],
    "warnings": [],
}
```

Errors prevent a simulation from starting when validation is enabled.

Warnings identify potentially problematic model configurations without necessarily making the model invalid.

Validation is also performed automatically by:

```python
model.run(time=10_000)
```

It can be disabled when necessary:

```python
model.run(
    time=10_000,
    validate=False,
)
```

---

# Experiments and replications

A single simulation run is often not enough for stochastic systems.

Queuenamics provides `Experiment` for repeated simulation runs.

```python
from queuenamics import Experiment

def create_model(seed):
    model = Model(seed=seed)

    # Build the model here.

    return model

experiment = Experiment(
    model_factory=create_model,
    replications=10,
    time=10_000,
)

results = experiment.run()
```

The resulting replications can be analyzed using:

```python
experiment.mean(...)
experiment.standard_deviation(...)
experiment.confidence_interval(...)
```

This makes it possible to estimate the variability of simulation results rather than relying on a single random realization.

---

# Parameter sweeps

Queuenamics also supports parameter sweeps through `ParameterSweep`.

This can be used to investigate how system performance changes when model parameters vary.

For example, a study could compare:

```text
Number of servers:
1
2
3
4
```

or:

```text
Arrival rate:
10/hour
15/hour
20/hour
25/hour
30/hour
```

Parameter sweeps are useful for capacity planning, sensitivity analysis, and comparing alternative system configurations.

---

# Warm-up periods

Simulation models that represent steady-state systems may require an initial warm-up period before collecting statistics.

`Experiment` supports a warm-up period:

```python
experiment = Experiment(
    model_factory=create_model,
    replications=10,
    time=10_000,
    warmup=1_000,
)
```

The warm-up period allows the model to reach a more representative operating state before statistics are collected.

---

# Visualization

Queuenamics includes lightweight visualization functions built around Matplotlib and NetworkX.

Available functions include:

```python
from queuenamics import (
    plot_model,
    plot_queue_length,
    plot_server_utilization,
    plot_throughput,
)
```

## Model structure

```python
plot_model(model)
```

This visualizes the model's network of atoms and connections.

## Queue length

```python
plot_queue_length(waiting_line)
```

This plots the evolution of queue length over simulation time.

## Server utilization

```python
plot_server_utilization(cashier)
```

## Throughput

```python
plot_throughput(exit)
```

The visualization functions can also be used without displaying a graphical window:

```python
plot_queue_length(
    waiting_line,
    show=False,
)
```

This is useful in automated analysis and headless environments.

---

# Example: Priority-based service system

The following example demonstrates several Queuenamics concepts together.

```python
from queuenamics import (
    Model,
    Source,
    Queue,
    Server,
    Sink,
    Exponential,
    Constant,
    Priority,
)

regular = Source(
    "Regular Customers",
    arrival=Exponential(20),
    entity_type="regular",
    attributes={"priority": 1},
)

urgent = Source(
    "Urgent Customers",
    arrival=Exponential(3),
    entity_type="urgent",
    attributes={"priority": 2},
)

queue = Queue(
    "Priority Queue",
    discipline=Priority(
        attribute="priority",
        highest_first=True,
    ),
)

server_1 = Server(
    "Server 1",
    service=Constant(2.35 / 60),
)

server_2 = Server(
    "Server 2",
    service=Constant(15 / 60),
)

exit = Sink("Exit")

model = Model(seed=42)

model.connect(regular, queue)
model.connect(urgent, queue)

model.connect(queue, server_1)
model.connect(queue, server_2)

model.connect(server_1, exit)
model.connect(server_2, exit)

model.run(time=10_000)

model.stats.print_report()
```

The resulting structure is:

```text
Regular ──┐
          ├──→ Priority Queue ──┬──→ Server 1 ──┐
Urgent ───┘                     └──→ Server 2 ──┤
                                                 ↓
                                               Exit
```

This demonstrates:

* multiple entity types
* entity attributes
* priority-based queue selection
* multiple servers
* heterogeneous service times
* shared queues
* reproducible stochastic simulation
* statistical reporting

---

# Examples

The `examples/` directory contains complete example models.

Examples are intended to demonstrate how Queuenamics can be used to build increasingly complex systems, including:

* basic single-server queues
* pooled-server systems
* multiple queues
* multiple server configurations
* heterogeneous service times
* different entity types
* priority-based queues
* routing
* experiments and parameter studies

The examples can also serve as starting points for your own models.

---

# Design philosophy

Queuenamics is intentionally **Python-native**.

Rather than building a model primarily through a graphical interface, the model is represented directly as Python code.

This provides several advantages:

### Reproducibility

Models can be stored in version control and reproduced from source code.

### Programmability

Model logic can be combined with Python's broader ecosystem.

### Experimentation

Parameters can be changed programmatically and large numbers of simulations can be automated.

### Transparency

The model structure is visible directly in the source code.

### Extensibility

Python classes can be used to build custom modelling components and analysis workflows.

The intention is not to hide the simulation model behind a graphical interface, but to make the model itself a programmable object.

---

# Project status

Queuenamics is an actively developed project.

The current focus is on building a reliable and extensible core for queueing and discrete-event simulation.

The API is intentionally kept relatively small while the underlying architecture develops.

Current development areas include:

* richer entity-based routing
* more advanced statistics
* improved resource handling
* more flexible server and queue behaviour
* improved experiment and parameter-sweep functionality
* expanded visualization
* performance improvements
* documentation and examples

The project is currently best suited to **learning, experimentation, research, prototyping, and operational-analysis models**.

---

# Development

Clone the repository:

```bash
git clone https://github.com/joosthof13/Queuenamics.git

cd Queuenamics
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install the package in editable mode:

```bash
pip install -e .
```

Install the test dependencies:

```bash
pip install pytest
```

Run the test suite:

```bash
pytest
```

For a quiet test run:

```bash
python -m pytest -q
```

---

# Project structure

```text
Queuenamics/
│
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
├── examples/
│
├── tests/
│
├── README.md
├── LICENSE
└── pyproject.toml
```

---

# Dependencies

Queuenamics uses a small number of Python dependencies for its core functionality and visualization:

* [Matplotlib](https://matplotlib.org/) — plotting
* [NetworkX](https://networkx.org/) — model-network visualization

The package requires:

```text
Python >= 3.10
```

---

# Contributing

Contributions, ideas, bug reports, and improvements are welcome.

Useful areas for contribution include:

* new queue disciplines
* routing strategies
* probability distributions
* statistics
* simulation performance
* visualization
* documentation
* examples
* tests

When contributing code, please include tests for new functionality where appropriate.

---

# License

Queuenamics is released under the **MIT License**.

See [LICENSE](LICENSE) for the full license text.

---

# Roadmap

The long-term goal is to develop Queuenamics into a flexible Python-native framework for operational modelling and discrete-event simulation.

Planned areas include:

* richer entity routing
* type-dependent routing
* more advanced resource constraints
* expanded statistics
* improved warm-up and steady-state analysis
* larger experiment workflows
* sensitivity analysis
* improved visualization
* performance optimization
* more comprehensive documentation
* additional modelling examples

The guiding principle remains:

**Keep the modelling API simple while making the simulation engine increasingly powerful.**

---

## Queuenamics in one sentence

> **Queuenamics lets you build operational processes as Python models, simulate them as discrete events, and analyze the resulting system performance.**
