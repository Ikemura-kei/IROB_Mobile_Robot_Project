#!/usr/bin/env python3
"""Block until the given ROS 2 services and topics exist, then exit.

mission.launch.py uses this to sequence bringup on observed readiness instead of
fixed delays. Fixed delays are machine-dependent: the same numbers that work on a
fast desktop let map_server start while Gazebo is still loading the world on a
slower laptop, which starves its lifecycle transition and leaves it stuck in
Configuring (no /map, blank RViz, empty costmaps).

Exits 0 once everything is available, 1 on timeout. mission.launch.py continues
either way -- a timeout degrades startup rather than hanging the launch forever.
"""

import argparse
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, HistoryPolicy, QoSProfile,
                       ReliabilityPolicy)
from rosidl_runtime_py.utilities import get_message, get_service


def subscribe_any_qos(node, topic, type_name, on_msg):
    """Subscribe to `topic` under both common QoS profiles.

    A publisher's QoS must be at least as strong as the subscriber's, and the
    two profiles we care about are mutually exclusive:
      * latched config topics (/map) are RELIABLE + TRANSIENT_LOCAL, and only a
        TRANSIENT_LOCAL subscriber receives the already-published message;
      * sensor streams (/scan) are BEST_EFFORT + VOLATILE, which a RELIABLE
        subscriber will never match at all.
    Subscribing twice costs nothing here and means one gate handles both.
    """
    msg_type = get_message(type_name)
    subs = []
    for reliability, durability in (
        (ReliabilityPolicy.RELIABLE, DurabilityPolicy.TRANSIENT_LOCAL),
        (ReliabilityPolicy.BEST_EFFORT, DurabilityPolicy.VOLATILE),
    ):
        qos = QoSProfile(depth=1, history=HistoryPolicy.KEEP_LAST,
                         reliability=reliability, durability=durability)
        subs.append(node.create_subscription(msg_type, topic, on_msg, qos))
    return subs


def served_services(node):
    """Service names actually *offered* by some node.

    Deliberately not node.get_service_names_and_types(): that also reports names
    created by service *clients*, so a node merely waiting on a service makes it
    look available. The create3 controller spawners do exactly that, which would
    make a controller_manager gate fire before the server exists.
    """
    names = set()
    for name, namespace in node.get_node_names_and_namespaces():
        try:
            for service, _ in node.get_service_names_and_types_by_node(name, namespace):
                names.add(service)
        except Exception:
            # The node can disappear between enumeration and query; skip it.
            continue
    return names


def service_answers(node, name, type_name, call_timeout):
    """True if `name` actually responds to a call, not merely that it exists.

    Being advertised is not the same as being usable. controller_manager
    advertises list_controllers as soon as it is constructed, but while
    gz_ros2_control is still initialising under cold-start load it can take
    another minute before it services a request. Anything fired at it in that
    window fails -- which is exactly how the arm controller ends up unloaded:
    `ros2 param set ... lite6_traj_controller.type` dies, so the spawner has no
    type to load. Calls here use read-only or empty requests.
    """
    try:
        srv_type = get_service(type_name)
    except Exception:
        return False
    client = node.create_client(srv_type, name)
    try:
        if not client.service_is_ready():
            return False
        future = client.call_async(srv_type.Request())
        rclpy.spin_until_future_complete(node, future, timeout_sec=call_timeout)
        return future.done() and future.result() is not None
    finally:
        node.destroy_client(client)


def wait_for(node, nodes, services, topics, timeout, poll=0.5, call_services=(),
             call_timeout=10.0):
    """Return True once every node, service and topic is present, False on timeout."""
    pending_nodes = list(nodes)
    pending_services = list(services)
    pending_topics = list(topics)
    pending_calls = list(call_services)
    received = set()
    subscribed = {}
    deadline = time.monotonic() + timeout

    while rclpy.ok() and (pending_nodes or pending_services or pending_topics
                          or pending_calls):
        if time.monotonic() > deadline:
            node.get_logger().error(
                f'Timed out after {timeout:.0f}s. Still missing: '
                f'nodes={pending_nodes} services={pending_services} '
                f'topics={pending_topics} unanswered={pending_calls}')
            return False

        # Lets discovery run; we poll the graph rather than block on any one name.
        rclpy.spin_once(node, timeout_sec=poll)

        live_nodes = set(node.get_node_names())
        for name in [n for n in pending_nodes if n.lstrip('/') in live_nodes]:
            node.get_logger().info(f'ready: node {name}')
            pending_nodes.remove(name)

        if pending_services:
            available = served_services(node)
            for name in [s for s in pending_services if s in available]:
                node.get_logger().info(f'ready: service {name}')
                pending_services.remove(name)

        # Topics require an actual message, not merely a publisher. A publisher
        # can exist long before any data flows: nav2's map_server creates its
        # /map publisher during on_configure and only publishes during
        # on_activate, so a publisher-count check passes while map_server is
        # still stuck in Configuring -- nav2 then starts and spins forever on
        # "Can't update static costmap layer, no map received".
        graph_types = dict(node.get_topic_names_and_types())
        for name in list(pending_topics):
            if name in received:
                node.get_logger().info(f'ready: topic {name} (message received)')
                pending_topics.remove(name)
            elif name not in subscribed and name in graph_types:
                subscribed[name] = subscribe_any_qos(
                    node, name, graph_types[name][0],
                    lambda _m, n=name: received.add(n))

        if pending_calls:
            service_types = dict(node.get_service_names_and_types())
            for name in list(pending_calls):
                if name not in service_types:
                    continue
                if service_answers(node, name, service_types[name][0], call_timeout):
                    node.get_logger().info(f'ready: service {name} (answered a call)')
                    pending_calls.remove(name)

    return not (pending_nodes or pending_services or pending_topics or pending_calls)


def main(argv=None):
    # rclpy.init consumes --ros-args; argparse only sees the rest.
    rclpy.init(args=argv)
    argv = rclpy.utilities.remove_ros_args(sys.argv[1:] if argv is None else argv)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', action='append', default=[],
                        help='node that must be in the graph (repeatable)')
    parser.add_argument('--service', action='append', default=[],
                        help='service that must be served, not merely requested '
                             'by a client (repeatable)')
    parser.add_argument('--call-service', action='append', default=[],
                        help='service that must actually answer a call, not just '
                             'be advertised (repeatable)')
    parser.add_argument('--topic', action='append', default=[],
                        help='topic that must have a publisher (repeatable)')
    parser.add_argument('--timeout', type=float, default=300.0,
                        help='give up after this many seconds (default: 300)')
    parser.add_argument('--label', default='wait_for_ready',
                        help='name used in log messages')
    args = parser.parse_args(argv)

    node = Node('wait_for_ready')
    node.get_logger().info(
        f'[{args.label}] waiting for nodes={args.node} services={args.service} '
        f'answering={args.call_service} topics={args.topic} '
        f'(timeout {args.timeout:.0f}s)')

    start = time.monotonic()
    try:
        ok = wait_for(node, args.node, args.service, args.topic, args.timeout,
                      call_services=args.call_service)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

    if ok:
        print(f'[{args.label}] ready after {time.monotonic() - start:.1f}s')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
