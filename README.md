# Queuenamics

**Python-native discrete-event simulation and queueing models.**

Queuenamics is a Python library for building, simulating, analyzing, and experimenting with **queueing systems, service processes, and operational models**.

It is designed for situations where processes can be represented as entities moving through a network of queues, servers, resources, and decision points over simulated time.

The goal is to make discrete-event simulation accessible through ordinary Python code rather than a proprietary graphical modelling environment.

The core workflow is:

**DEFINE → CONNECT → VALIDATE → RUN → ANALYZE → EXPORT**

---

## Table of Contents

* [Why Queuenamics?](#why-queuenamics)
* [Core concepts](#core-concepts)

  * [Entities](#entities)
  * [Atoms](#atoms)
  * [Connections](#connections)
  * [Model](#model)
* [Features](#features)
* [Installation](#installation)
* [Quick example](#quick-example)
* [Modelling workflow](#modelling-workflow)

  * [1. Define](#1-define)
  * [2. Connect](#2-connect)
  * [3. Validate](#3-validate)
  * [4. Run](#4-run)
  * [5. Analyze](#5-analyze)
  * [6. Export](#6-export)
* [Probability distributions](#probability-distributions)

  * [Exponential](#exponential)
  * [Constant](#constant)
  * [Uniform](#uniform)
  * [Poisson](#poisson)
* [Queue disciplines](#queue-disciplines)

  * [FIFO](#fifo)
  * [LIFO](#lifo)
  * [Priority](#priority)
  * [Shortest processing time](#shortest-processing-time)
* [Multiple servers](#multiple-servers)
* [Resources](#resources)
* [Routing](#routing)

  * [First available](#first-available)
  * [Random available](#random-available)
  * [Entity-type routing](#entity-type-routing)
  * [Attribute routing](#attribute-routing)
  * [Conditional routing](#conditional-routing)
  * [Destination availability](#destination-availability)
* [Entity attributes](#entity-attributes)
* [Statistics and reporting](#statistics-and-reporting)

  * [Basic statistics](#basic-statistics)
  * [Percentiles and quartiles](#percentiles-and-quartiles)
  * [Population vs sample statistics](#population-vs-sample-statistics)
  * [Grouped statistics](#grouped-statistics)
  * [Time-weighted statistics](#time-weighted-statistics)
  * [Replication statistics](#replication-statistics)
  * [Confidence intervals](#confidence-intervals)
* [Exporting results](#exporting-results)
* [Reproducibility](#reproducibility)
* [Validation](#validation)
* [Experiments and replications](#experiments-and-replications)
* [Parameter sweeps](#parameter-sweeps)
* [Warm-up periods](#warm-up-periods)
* [Visualization](#visualization)
* [Examples](#examples)
* [Design philosophy](#design-philosophy)
* [Project status](#project-status)
* [Development](#development)
* [Project structure](#project-structure)
* [Dependencies](#dependencies)
* [Contributing](#contributing)
* [License](#license)
* [Roadmap](#roadmap)
* [Queuenamics in one sentence](#queuenamics-in-one-sentence)

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
* How should different types of entities be routed?
* How sensitive is system performance to a particular parameter?

[Back to top](#table-of-contents)

---

# Core concepts

Queuenamics is built around a small number of modelling concepts.

## Entities

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
from queuenamics import Entity

entity = Entity(
    entity_type="urgent",
    creation_time=0,
)

entity.attributes["priority"] = 2
```

Sources can create entities with these properties automatically:

```python
from queuenamics import Exponential, Source

patients = Source(
    "Patients",
    arrival=Exponential(20),
    entity_type="patient",
    attributes={"priority": 1},
)
```

Each generated entity receives its own copy of the source attributes.

[Back to top](#table-of-contents)

---

## Atoms

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

More complex models can contain multiple paths, shared queues, multiple servers, resources, and different routing decisions.

[Back to top](#table-of-contents)

---

## Connections

Connections define how entities move between atoms.

```python
model.connect(source, queue)
model.connect(queue, server)
model.connect(server, sink)
```

This separates the **definition of individual components** from the **structure of the process**.

[Back to top](#table-of-contents)

---

## Model

The `Model` contains the atoms, connections, random-number generator, and simulation engine.

```python
model = Model(seed=42)
```

A model can then be validated and simulated:

```python
model.validate()

model.run(time=10_000)
```

[Back to top](#table-of-contents)

---

# Features

Queuenamics currently supports:

* discrete-event simulation
* entity creation and flow
* entity types and attributes
* sources and sinks
* FIFO queues
* LIFO queues
* priority queues
* shortest-processing-time queues
* multiple servers
* shared queues
* separate queues
* heterogeneous servers
* resources with capacities
* first-available routing
* random routing
* entity-type routing
* attribute-based routing
* conditional routing
* probability distributions
* reproducible simulations through random seeds
* descriptive statistics
* median and quartiles
* percentiles
* population and sample variance
* population and sample standard deviation
* time-weighted statistics
* queue-length statistics
* waiting-time statistics
* service-time statistics
* server utilization
* throughput measurements
* grouped statistics
* replication statistics
* standard errors
* confidence intervals
* model validation
* multiple replications
* experiments
* parameter sweeps
* warm-up periods
* model visualization
* JSON export
* CSV export

[Back to top](#table-of-contents)

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

For version **0.8.2**, this should print:

```text
0.8.2
```

[Back to top](#table-of-contents)

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

[Back to top](#table-of-contents)

---

# Modelling workflow

Queuenamics is designed around a simple workflow:

**DEFINE → CONNECT → VALIDATE → RUN → ANALYZE → EXPORT**

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

[Back to top](#table-of-contents)

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

[Back to top](#table-of-contents)

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

[Back to top](#table-of-contents)

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

[Back to top](#table-of-contents)

---

# Resources

Resources represent limited-capacity assets that can be acquired and released.

```python
from queuenamics import Resource

technicians = Resource(
    "Technicians",
    capacity=3,
)
```

Resources can be associated with servers:

```python
server = Server(
    "Repair Station",
    service=Exponential(4),
    resource=technicians,
)
```

When the server starts processing an entity, it acquires a resource unit. When service is completed, the resource is released.

This makes it possible to represent systems where service depends on a limited shared resource, such as:

* technicians
* nurses
* doctors
* forklifts
* machines
* operating rooms
* loading equipment

A resource tracks its capacity, current busy count, available capacity, and utilization.

[Back to top](#table-of-contents)

---

# Routing

Queuenamics supports several routing strategies for deciding which downstream connection should receive an entity.

Routing occurs through a queue's `router`.

## First available

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

When the queue has multiple server outputs, the first available destination can receive the selected entity.

## Random available

Randomized routing is also available:

```python
from queuenamics import RandomAvailable

queue = Queue(
    "Waiting Line",
    router=RandomAvailable(),
)
```

Random routing uses the model's seeded random-number generator, so it remains reproducible.

## Entity-type routing

Entities can be routed according to their `entity_type`.

```python
from queuenamics import EntityTypeRouter

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

The route values correspond to the queue's output connection indexes.

For example:

```python
regular = Source(
    "Regular Customers",
    arrival=Exponential(10),
    entity_type="regular",
)

urgent = Source(
    "Urgent Customers",
    arrival=Exponential(3),
    entity_type="urgent",
)
```

If the queue is connected as:

```python
model.connect(queue, regular_server)
model.connect(queue, urgent_server)
```

then:

```text
regular → output 0 → regular_server
urgent  → output 1 → urgent_server
```

An optional default route can handle unknown entity types:

```python
router = EntityTypeRouter(
    routes={
        "regular": 0,
        "urgent": 1,
    },
    default=0,
)
```

If no route exists and no default is specified, the entity remains in the queue.

## Attribute routing

Entities can also be routed using arbitrary attributes.

```python
from queuenamics import AttributeRouter

queue = Queue(
    "Customer Queue",
    router=AttributeRouter(
        attribute="customer_type",
        routes={
            "regular": 0,
            "vip": 1,
        },
    ),
)
```

Entities might be created as:

```python
regular = Source(
    "Regular",
    arrival=Exponential(10),
    attributes={
        "customer_type": "regular",
    },
)

vip = Source(
    "VIP",
    arrival=Exponential(2),
    attributes={
        "customer_type": "vip",
    },
)
```

This allows one queue to route different customer classes to different downstream processes.

## Conditional routing

For more flexible routing logic, `ConditionalRouter` accepts user-defined conditions.

```python
from queuenamics import ConditionalRouter

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

The first condition that evaluates to `True` determines the destination.

Multiple conditions can be specified:

```python
router = ConditionalRouter(
    conditions=[
        (
            lambda entity:
            entity.attributes.get("priority", 0) >= 3,
            0,
        ),
        (
            lambda entity:
            entity.attributes.get("priority", 0) >= 2,
            1,
        ),
    ],
    default=2,
)
```

This makes it possible to implement custom routing rules without creating a new routing class.

## Destination availability

Entity-based routing respects destination availability.

If an entity's selected destination is currently unavailable, the entity remains in the queue rather than being removed and lost.

This is particularly important when routing entities to busy servers or resource-constrained servers.

[Back to top](#table-of-contents)

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

Attributes can then be used by queue disciplines such as `Priority`:

```python
queue = Queue(
    "Priority Queue",
    discipline=Priority(
        attribute="priority",
        highest_first=True,
    ),
)
```

They can also be used by routing components such as `AttributeRouter` and `ConditionalRouter`.

This allows the model to distinguish between different classes of entities without requiring separate models.

For example:

```text
                    ┌→ Regular Server
                    │
Source → Queue ─────┼→ VIP Server
                    │
                    └→ Priority Server
```

where the destination is determined by information carried by each entity.

[Back to top](#table-of-contents)

---

# Statistics and reporting

Queuenamics provides several layers of statistics.

At the model level:

```python
report = model.stats.report()
```

A formatted report can be printed directly:

```python
model.stats.print_report()
```

For direct statistical analysis, Queuenamics also exposes `Statistic`, `TimeWeightedStatistic`, `ReplicationStatistic`, and `ReplicationResults`.

```python
from queuenamics import (
    Statistic,
    Statistics,
    TimeWeightedStatistic,
    ReplicationStatistic,
    ReplicationResults,
)
```

---

## Basic statistics

`Statistic` stores scalar observations and provides descriptive statistics.

```python
statistic = Statistic()

statistic.record(5)
statistic.record(10)
statistic.record(15)
```

Basic properties include:

```python
statistic.count
statistic.total
statistic.mean
statistic.minimum
statistic.maximum
```

For the observations above:

```python
statistic.count
# 3

statistic.total
# 30.0

statistic.mean
# 10.0

statistic.minimum
# 5

statistic.maximum
# 15
```

Empty statistics return `0.0` for numerical summary properties:

```python
statistic = Statistic()

statistic.mean
# 0.0

statistic.minimum
# 0.0

statistic.maximum
# 0.0
```

This provides predictable behavior when a simulation produces no observations.

---

## Percentiles and quartiles

`Statistic` supports arbitrary percentiles:

```python
statistic.percentile(90)
statistic.percentile(95)
statistic.percentile(99)
```

Percentiles use linear interpolation between ordered observations.

The following convenience properties are available:

```python
statistic.q1
statistic.median
statistic.q2
statistic.q3
statistic.iqr
```

where:

* `q1` = 25th percentile
* `q2` = 50th percentile
* `median` = 50th percentile
* `q3` = 75th percentile
* `iqr` = Q3 − Q1

For example:

```python
statistic = Statistic()

for value in [1, 2, 3, 4, 5]:
    statistic.record(value)

print(statistic.q1)
print(statistic.median)
print(statistic.q3)
print(statistic.iqr)
```

Arbitrary percentiles can also be requested:

```python
p90 = statistic.percentile(90)
p95 = statistic.percentile(95)
p99 = statistic.percentile(99)
```

Valid percentiles range from `0` to `100` inclusive.

```python
statistic.percentile(0)
statistic.percentile(100)
```

An invalid percentile raises `ValueError`.

---

## Population vs sample statistics

Queuenamics explicitly distinguishes between **population** and **sample** statistics.

### Population variance

`population_variance` uses N as the denominator:

```python
statistic.population_variance
```

### Sample variance

`sample_variance` uses N − 1:

```python
statistic.sample_variance
```

Similarly:

```python
statistic.population_standard_deviation
statistic.sample_standard_deviation
```

The existing properties:

```python
statistic.variance
statistic.standard_deviation
```

are retained for backwards compatibility and refer to the **population** versions.

Therefore:

```python
statistic.variance
```

is equivalent to:

```python
statistic.population_variance
```

and:

```python
statistic.standard_deviation
```

is equivalent to:

```python
statistic.population_standard_deviation
```

For example:

```python
statistic = Statistic()

for value in [2, 4, 6]:
    statistic.record(value)

print(statistic.population_variance)
print(statistic.sample_variance)
```

This distinction is particularly important when interpreting simulation results.

---

## Grouped statistics

Statistics can automatically be grouped by entity type or entity attributes when observations are recorded with an entity.

For example:

```python
statistic.record(
    5,
    entity=entity,
)
```

Entity-type groups can be retrieved with:

```python
statistic.group_by("entity_type")
```

Grouped results contain descriptive statistics such as:

```text
count
total
mean
minimum
maximum
median
q1
q2
q3
iqr
variance
population_variance
sample_variance
standard_deviation
population_standard_deviation
sample_standard_deviation
percentile_25
percentile_50
percentile_75
percentile_90
percentile_95
percentile_99
```

For example:

```python
groups = statistic.group_by("entity_type")

urgent = groups["urgent"]

print(urgent["mean"])
print(urgent["median"])
print(urgent["q1"])
print(urgent["q3"])
print(urgent["percentile_95"])
```

Counts can also be retrieved separately:

```python
counts = statistic.grouped_count("entity_type")
```

The same grouping mechanism can be used with arbitrary entity attributes.

---

## Time-weighted statistics

Many simulation quantities are not observations collected once per entity. Queue length and server occupancy, for example, are **state variables that change over simulation time**.

For these quantities, Queuenamics provides `TimeWeightedStatistic`.

```python
queue_length = TimeWeightedStatistic()
```

The state can be updated at simulation events:

```python
queue_length.update(0, 0)
queue_length.update(1, 2)
queue_length.update(3, 5)
queue_length.update(0, 8)
```

The time-weighted mean can then be calculated:

```python
average = queue_length.mean(10)
```

The calculation is based on the exact area under the state curve rather than periodic sampling.

This is important because queue length can change between arbitrary simulation events.

### Maximum

The maximum observed state is available through:

```python
queue_length.maximum
```

### Time at a particular value

```python
queue_length.time_at(0, 10)
```

### Time at zero

```python
queue_length.time_zero(10)
```

### Time at a nonzero value

```python
queue_length.time_nonzero(10)
```

### Occupancy

The fraction of time for which the value was nonzero can be obtained with:

```python
queue_length.occupancy(10)
```

### Period durations

Contiguous periods satisfying a condition can be retrieved with:

```python
queue_length.period_durations(
    lambda value: value > 0,
    10,
)
```

For nonzero periods, a convenience method is available:

```python
queue_length.periods_nonzero(10)
```

An ongoing final period is included up to the specified end time.

### Resetting

A time-weighted statistic can be reset at an arbitrary simulation time:

```python
queue_length.reset(
    time=100,
    current=2,
)
```

This is useful when implementing warm-up periods or restarting statistical collection.

---

## Replication statistics

A single stochastic simulation run is only one realization of a random process.

`ReplicationStatistic` is intended for analyzing measurements across **independent simulation replications**.

```python
result = ReplicationStatistic(
    [10, 12, 11, 13, 9]
)
```

Available statistics include:

```python
result.count
result.mean
result.standard_deviation
result.standard_error
```

The standard deviation is a **sample standard deviation**, using N − 1 in the denominator.

This is appropriate when replication results are treated as a sample from the underlying simulation-output distribution.

---

## Confidence intervals

Replication statistics support confidence intervals based on Student's t distribution.

The default confidence level is 95%:

```python
result.confidence_interval()
```

A 95% confidence interval can also be accessed explicitly:

```python
result.confidence_interval_95
```

Other confidence levels can be requested:

```python
result.confidence_interval(0.90)
result.confidence_interval(0.95)
result.confidence_interval(0.99)
```

The corresponding margin of error can be obtained with:

```python
result.margin_of_error(0.95)
```

The Student-t critical value can be obtained with:

```python
result.t_critical(0.95)
```

For common confidence levels, Queuenamics provides tabulated Student-t critical values for small replication counts. For larger samples or other confidence levels, a normal approximation is used.

### Summary

A complete replication summary can be obtained with:

```python
result.summary()
```

For example:

```python
{
    "count": 10,
    "mean": 12.4,
    "standard_deviation": 1.8,
    "standard_error": 0.57,
    "confidence_level": 0.95,
    "margin_of_error": 1.29,
    "confidence_interval": [11.11, 13.69],
}
```

The exact values depend on the replication results.

---

## Replication results

`ReplicationResults` collects numerical results from multiple model reports.

```python
results = ReplicationResults(reports)
```

Available metrics can be inspected with:

```python
results.metrics
```

Individual replication values can be retrieved with:

```python
results.values("servers.Cashier.utilization")
```

A `ReplicationStatistic` can be created for a metric:

```python
statistic = results.statistic(
    "servers.Cashier.utilization"
)
```

The mean can be obtained directly:

```python
results.mean(
    "servers.Cashier.utilization"
)
```

Confidence intervals can also be obtained directly:

```python
results.confidence_interval(
    "servers.Cashier.utilization",
    confidence=0.95,
)
```

A complete summary is available with:

```python
results.summary()
```

or for one metric:

```python
results.summary(
    "servers.Cashier.utilization"
)
```

Confidence level can be specified:

```python
results.summary(
    confidence=0.99
)
```

This makes replication analysis suitable for comparing alternative queueing-system configurations.

[Back to top](#table-of-contents)

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

[Back to top](#table-of-contents)

---

# Reproducibility

Stochastic simulations can be reproduced using a random seed.

```python
model = Model(seed=42)
```

The model's random-number generator is shared by stochastic components of the model, including:

* probability distributions
* random queue disciplines
* random routing

This allows experiments to be repeated under controlled random conditions.

For example, two models constructed with the same seed and the same configuration can produce the same stochastic sequence.

[Back to top](#table-of-contents)

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

[Back to top](#table-of-contents)

---

# Experiments and replications

A single simulation run is often not enough for stochastic systems.

Queuenamics provides `Experiment` for repeated simulation runs.

```python
from queuenamics import Experiment, Model


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

The resulting replications can be analyzed using the experiment's result interface and the replication statistics described in [Statistics and reporting](#statistics-and-reporting).

This makes it possible to estimate the variability of simulation results rather than relying on a single random realization.

[Back to top](#table-of-contents)

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

Parameter sweeps are useful for:

* capacity planning
* sensitivity analysis
* comparing alternative system configurations
* identifying bottlenecks
* evaluating operational decisions

[Back to top](#table-of-contents)

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

The time-weighted statistics also support resetting their statistical origin at a specified simulation time, which can be useful when implementing statistical warm-up handling.

[Back to top](#table-of-contents)

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

This visualizes server utilization.

## Throughput

```python
plot_throughput(exit)
```

This visualizes throughput information for a sink.

The visualization functions can also be used without displaying a graphical window:

```python
plot_queue_length(
    waiting_line,
    show=False,
)
```

This is useful in automated analysis and headless environments.

[Back to top](#table-of-contents)

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

[Back to top](#table-of-contents)

---

# Example: Entity-based routing

The following example demonstrates entity-based routing.

```python
from queuenamics import (
    Model,
    Source,
    Queue,
    Server,
    Sink,
    Constant,
    EntityTypeRouter,
)

regular = Source(
    "Regular Customers",
    arrival=Constant(1),
    entity_type="regular",
)

priority = Source(
    "Priority Customers",
    arrival=Constant(2),
    entity_type="priority",
)

queue = Queue(
    "Customer Queue",
    router=EntityTypeRouter(
        routes={
            "regular": 0,
            "priority": 1,
        },
    ),
)

regular_server = Server(
    "Regular Counter",
    service=Constant(0.8),
)

priority_server = Server(
    "Priority Counter",
    service=Constant(0.5),
)

regular_exit = Sink("Regular Exit")
priority_exit = Sink("Priority Exit")

model = Model(seed=42)

model.connect(regular, queue)
model.connect(priority, queue)

model.connect(queue, regular_server)
model.connect(queue, priority_server)

model.connect(regular_server, regular_exit)
model.connect(priority_server, priority_exit)

model.run(
    time=100,
    progress=False,
)

model.stats.print_report()
```

The resulting structure is:

```text
Regular Customers ──┐
                    ├──→ Customer Queue ──→ Regular Counter ──→ Regular Exit
Priority Customers ─┘              │
                                   └──────→ Priority Counter ─→ Priority Exit
```

This demonstrates how information attached to entities can directly determine their path through the model.

[Back to top](#table-of-contents)

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
* entity attributes
* priority-based queues
* entity-based routing
* attribute-based routing
* conditional routing
* resources
* experiments
* parameter studies
* visualization
* result export

The examples can also serve as starting points for your own models.

[Back to top](#table-of-contents)

---

# Design philosophy

Queuenamics is intentionally **Python-native**.

Rather than building a model primarily through a graphical interface, the model is represented directly as Python code.

This provides several advantages.

## Reproducibility

Models can be stored in version control and reproduced from source code.

## Programmability

Model logic can be combined with Python's broader ecosystem.

## Experimentation

Parameters can be changed programmatically and large numbers of simulations can be automated.

## Transparency

The model structure is visible directly in the source code.

## Extensibility

Python classes can be used to build custom modelling components and analysis workflows.

The intention is not to hide the simulation model behind a graphical interface, but to make the model itself a programmable object.

[Back to top](#table-of-contents)

---

# Project status

Queuenamics is an actively developed project.

The current focus is on building a reliable and extensible core for queueing and discrete-event simulation.

The API is intentionally kept relatively small while the underlying architecture develops.

## Version 0.8.2 — Statistics

Version **0.8.2** focuses on strengthening the statistics layer.

This release includes:

* descriptive statistics
* median and quartiles
* interquartile range
* arbitrary percentiles
* explicit population and sample variance
* explicit population and sample standard deviation
* grouped statistics
* exact time-weighted statistics
* replication statistics
* standard errors
* Student-t confidence intervals
* configurable confidence levels

The statistics layer is intended to provide the foundation for more advanced experiment analysis in future releases.

The current project is best suited to:

* learning
* experimentation
* research
* prototyping
* operational analysis
* queueing-system studies
* discrete-event simulation

[Back to top](#table-of-contents)

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

[Back to top](#table-of-contents)

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
├── tests/
│
├── examples/
│
├── README.md
├── LICENSE
└── pyproject.toml
```

[Back to top](#table-of-contents)

---

# Dependencies

Queuenamics uses a small number of Python dependencies for its core functionality and visualization:

* [Matplotlib](https://matplotlib.org/) — plotting and visualization
* [NetworkX](https://networkx.org/) — model-network visualization

The package requires:

```text
Python >= 3.10
```

[Back to top](#table-of-contents)

---

# Contributing

Contributions, ideas, bug reports, and improvements are welcome.

Useful areas for contribution include:

* new queue disciplines
* routing strategies
* probability distributions
* statistics
* simulation performance
* resource handling
* visualization
* documentation
* examples
* tests

When contributing code, please include tests for new functionality where appropriate.

Before submitting changes, run:

```bash
python -m pytest -q
```

[Back to top](#table-of-contents)

---

# License

Queuenamics is released under the **MIT License**.

See [LICENSE](LICENSE) for the full license text.

[Back to top](#table-of-contents)

---

# Roadmap

The long-term goal is to develop Queuenamics into a flexible Python-native framework for operational modelling and discrete-event simulation.

Planned areas include:

* more advanced statistical analysis
* type-dependent analysis
* more advanced resource constraints
* expanded experiment workflows
* advanced steady-state analysis
* sensitivity analysis
* improved visualization
* performance optimization
* more comprehensive documentation
* additional modelling examples
* more advanced routing and process logic

The guiding principle remains:

> **Keep the modelling API simple while making the simulation engine increasingly powerful.**

[Back to top](#table-of-contents)

---

# Queuenamics in one sentence

> **Queuenamics lets you build operational processes as Python models, simulate them as discrete events, and analyze the resulting system performance.**

[Back to top](#table-of-contents)
