#!/usr/bin/env python3
"""Relocate the robot by clicking on the map in RViz.

EXAMINER TOOL. Nothing in the mission depends on this and students never edit
it -- it exists so the A-grade run can start from a pose the solution has no
knowledge of.

Usage
    ros2 run warehouse_inventory_robot relocate_robot

Then in RViz pick the "Publish Point" tool and click anywhere on the map. The
robot and its dock are teleported there, still docked, and AMCL's belief is
left stale and wrong on purpose -- re-localizing is the student's job.

Why "Publish Point" and not "2D Pose Estimate"
    The 2D Pose Estimate tool publishes /initialpose, which AMCL subscribes to.
    Using it would hand the robot its own answer and delete the exercise.
    "Publish Point" writes to /clicked_point, which nothing else consumes.

Why the gz CLI rather than a bridged service
    Teleporting needs Gazebo's /world/<world>/set_pose. Bridging it would mean
    another ros_gz_bridge entry running for the whole session purely for an
    action taken once, by hand, before a run. Shelling out keeps the tool
    self-contained; the gz CLI is in the same environment as this node.
"""

import math
import random
import subprocess
import time

import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from geometry_msgs.msg import PointStamped
from std_msgs.msg import Empty
from ament_index_python.packages import get_package_share_directory

import os
import yaml


# The dock spawns this far from the robot, rotated by the robot's yaw, and
# facing back towards it. Mirrored from turtlebot4_spawn.launch.py; if that
# offset ever changes, change it here too or the robot will land beside its
# dock rather than on it.
DOCK_OFFSET_M = 0.157
ROBOT_Z_OFFSET = -0.0025

# Generous enough to cover the robot's own footprint plus the dock sitting
# just behind it, so a click that would bury either in a shelf is refused.
CLEARANCE_RADIUS_M = 0.35

# The cube and where it belongs, taken from the world file.
#
# gz's DetachableJoint is created ATTACHED when the world loads, so from the
# moment the simulation starts the cube is welded to the vacuum gripper. That
# is why mission_node's first action is to publish detach twice. Relocating
# happens BEFORE the mission node runs, though, so the weld is still in place
# and teleporting the robot drags the cube across the warehouse with it, which
# leaves it on the floor a long way from its box.
#
# So this releases the cube first and then puts it back where the world file
# had it, which also cleans up after any earlier run that left it elsewhere.
CUBE_NAME = 'top_cube_1'
CUBE_HOME_XYZ = (2.0, 7.49, 0.35)
DETACH_TOPIC = '/vacuum_gripper/detach'
DETACH_SETTLE_S = 0.6


def load_occupancy(map_yaml_path):
    """Read a map_server YAML plus its PGM into a simple occupancy accessor."""
    with open(map_yaml_path) as f:
        meta = yaml.safe_load(f)

    pgm_path = os.path.join(os.path.dirname(map_yaml_path), meta['image'])
    data = open(pgm_path, 'rb').read()

    # Minimal P5 header parse: magic, then width/height/maxval, skipping
    # comments. PIL is not a dependency of this package and this is 15 lines.
    tokens, i = [], 2
    while len(tokens) < 3:
        while data[i:i + 1].isspace():
            i += 1
        if data[i:i + 1] == b'#':
            while data[i:i + 1] not in (b'\n', b''):
                i += 1
            continue
        j = i
        while not data[j:j + 1].isspace():
            j += 1
        tokens.append(int(data[i:j]))
        i = j
    i += 1
    width, height, _maxval = tokens
    pixels = data[i:]

    res = float(meta['resolution'])
    ox, oy = float(meta['origin'][0]), float(meta['origin'][1])
    return {
        'w': width, 'h': height, 'px': pixels,
        'res': res, 'ox': ox, 'oy': oy,
        'ymax': oy + height * res,
    }


def is_free(occ, x, y, radius_m):
    """True when every map cell within radius_m of (x, y) is free space."""
    cx = int((x - occ['ox']) / occ['res'])
    cy = int((occ['ymax'] - y) / occ['res'])
    r = int(radius_m / occ['res'])

    if not (0 <= cx < occ['w'] and 0 <= cy < occ['h']):
        return False, 'outside the map'

    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > r * r:
                continue
            gx, gy = cx + dx, cy + dy
            if not (0 <= gx < occ['w'] and 0 <= gy < occ['h']):
                return False, 'too close to the edge of the map'
            # In a trinary map_server PGM, high values are free and low values
            # are occupied. Anything not clearly free is treated as blocked.
            if occ['px'][gy * occ['w'] + gx] <= 200:
                return False, 'obstacle within the robot footprint'
    return True, 'free'


def set_entity_pose(world, name, x, y, z, yaw, timeout_ms=3000):
    """Teleport one Gazebo entity. Returns True on success."""
    req = (f'name: "{name}", '
           f'position: {{x: {x}, y: {y}, z: {z}}}, '
           f'orientation: {{x: 0, y: 0, z: {math.sin(yaw / 2.0)}, '
           f'w: {math.cos(yaw / 2.0)}}}')
    cmd = ['gz', 'service', '-s', f'/world/{world}/set_pose',
           '--reqtype', 'gz.msgs.Pose', '--reptype', 'gz.msgs.Boolean',
           '--timeout', str(timeout_ms), '--req', req]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=timeout_ms / 1000.0 + 2.0)
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return False, str(exc)
    ok = 'true' in (out.stdout or '').lower()
    return ok, (out.stdout or out.stderr or '').strip()


class RelocateRobot(Node):

    def __init__(self):
        super().__init__('relocate_robot')

        self.declare_parameter('world', 'warehouse')
        self.declare_parameter('robot_name', 'turtlebot4')
        self.declare_parameter('dock_name', 'standard_dock')
        # 'random' rotates the robot to an arbitrary heading, which is a
        # harder and more honest test of global localization than always
        # facing the same way. Set a number (radians) to pin it.
        self.declare_parameter('yaw', 'random')

        self.world = self.get_parameter('world').value
        self.robot_name = self.get_parameter('robot_name').value
        self.dock_name = self.get_parameter('dock_name').value

        map_yaml = os.path.join(
            get_package_share_directory('warehouse_inventory_robot'),
            'maps', 'warehouse.yaml')
        self.occ = load_occupancy(map_yaml)

        self._detach_pub = self.create_publisher(Empty, DETACH_TOPIC, 10)

        self.create_subscription(PointStamped, '/clicked_point',
                                 self.on_click, 10)

        self.get_logger().info(
            'Ready. In RViz choose the "Publish Point" tool and click a spot '
            'on the map to move the robot and its dock there.')
        self.get_logger().info(
            'Do NOT use "2D Pose Estimate" -- that publishes /initialpose, '
            'which AMCL reads, and would tell the robot where it is.')

    def _resolve_yaw(self):
        raw = self.get_parameter('yaw').value
        if str(raw).strip().lower() == 'random':
            return random.uniform(-math.pi, math.pi)
        try:
            return float(raw)
        except (TypeError, ValueError):
            self.get_logger().warn(f'Could not read yaw="{raw}"; using 0.0')
            return 0.0

    def on_click(self, msg):
        x, y = msg.point.x, msg.point.y

        free, why = is_free(self.occ, x, y, CLEARANCE_RADIUS_M)
        if not free:
            self.get_logger().error(
                f'Refusing to move to ({x:.2f}, {y:.2f}): {why}. '
                f'Pick a spot with at least {CLEARANCE_RADIUS_M:.2f} m of '
                f'clear space around it.')
            return

        # Break the gripper weld BEFORE moving anything, or the cube is
        # dragged along with the robot. Published twice, spaced, because this
        # crosses ROS -> ros_gz bridge -> Gazebo and the first can be lost.
        self._detach_pub.publish(Empty())
        time.sleep(DETACH_SETTLE_S / 2.0)
        self._detach_pub.publish(Empty())
        time.sleep(DETACH_SETTLE_S / 2.0)

        yaw = self._resolve_yaw()
        dock_x = x + DOCK_OFFSET_M * math.cos(yaw)
        dock_y = y + DOCK_OFFSET_M * math.sin(yaw)

        # Robot first, then the dock onto it. Both move together so the base
        # still reports is_docked and the mission's Undock precondition
        # behaves exactly as it does at the origin.
        ok_robot, msg_robot = set_entity_pose(
            self.world, self.robot_name, x, y, ROBOT_Z_OFFSET, yaw)
        ok_dock, msg_dock = set_entity_pose(
            self.world, self.dock_name, dock_x, dock_y, 0.0, yaw + math.pi)

        # Put the cube back on its box, so the mission always starts from the
        # same state no matter what a previous run left behind.
        cx, cy, cz = CUBE_HOME_XYZ
        ok_cube, msg_cube = set_entity_pose(
            self.world, CUBE_NAME, cx, cy, cz, 0.0)

        if ok_robot and ok_dock and ok_cube:
            self.get_logger().info(
                f'Moved robot to ({x:.2f}, {y:.2f}) facing {yaw:+.2f} rad, '
                f'dock to ({dock_x:.2f}, {dock_y:.2f}), and reset the cube to '
                f'({cx:.2f}, {cy:.2f}). '
                f'AMCL still believes otherwise, which is the point.')
        elif not ok_cube:
            self.get_logger().error(f'Cube reset failed: {msg_cube}')
        else:
            if not ok_robot:
                self.get_logger().error(f'Robot move failed: {msg_robot}')
            if not ok_dock:
                self.get_logger().error(
                    f'Dock move failed: {msg_dock}. The robot may now be off '
                    f'its dock, which will make Undock fail.')


def main(args=None):
    rclpy.init(args=args)
    node = RelocateRobot()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        # Ctrl-C, or the launch tearing the node down, are ordinary ways for
        # this to end. Without catching ExternalShutdownException rclpy prints
        # a traceback that looks like a crash.
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
