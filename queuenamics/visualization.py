import matplotlib.pyplot as plt
import networkx as nx

def plot_model(model, show=True):
    graph = nx.DiGraph()

    for atom in model.atoms:
        graph.add_node(
            atom.name,
            atom=atom
        )

    for connection in model.connections:
        graph.add_edge(
            connection.source.name,
            connection.destination.name
        )

    positions = nx.spring_layout(
        graph,
        seed=42
    )

    plt.figure(figsize=(10, 6))

    nx.draw(
        graph,
        positions,
        with_labels=True,
        node_size=2500,
        arrows=True
    )

    plt.title("Queuenamics Model")

    if show:
        plt.show()

    return graph

def plot_queue_length(queue, show=True):

    history = queue.stats.queue_length.history

    if not history:
        raise ValueError(
            f"Queue {queue.name!r} has no recorded history."
        )

    times = [
        point[0]
        for point in history
    ]

    lengths = [
        point[1]
        for point in history
    ]

    plt.figure(figsize=(10, 6))

    plt.step(
        times,
        lengths,
        where="post"
    )

    plt.xlabel("Simulation time")
    plt.ylabel("Queue length")
    plt.title(
        f"Queue Length — {queue.name}"
    )

    if show:
        plt.show()

    return times, lengths

def plot_server_utilization(server, show=True):

    if server.model is None:
        raise ValueError(
            f"Server {server.name!r} is not connected to a model."
        )

    simulation_time = server.model.simulation.time

    if simulation_time <= 0:
        raise ValueError(
            "Simulation must have positive elapsed time."
        )

    utilization = server.utilization

    plt.figure(figsize=(10, 6))

    plt.bar(
        [server.name],
        [utilization]
    )

    plt.ylim(0, 1)

    plt.ylabel("Utilization")
    plt.title(
        f"Server Utilization — {server.name}"
    )

    if show:
        plt.show()

    return utilization

def plot_throughput(sink, show=True):

    if sink.model is None:
        raise ValueError(
            f"Sink {sink.name!r} is not connected to a model."
        )

    simulation_time = sink.model.simulation.time

    if simulation_time <= 0:
        raise ValueError(
            "Simulation must have positive elapsed time."
        )

    throughput = sink.throughput

    plt.figure(figsize=(10, 6))

    plt.bar(
        [sink.name],
        [throughput]
    )

    plt.ylabel("Throughput")
    plt.title(
        f"Throughput — {sink.name}"
    )

    if show:
        plt.show()

    return throughput