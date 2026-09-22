# IROB Final Assignment - Skeleton

This is a skeleton for the mobile robot assignment.

## Repository layout

| Path | What it is |
| --- | --- |
| `warehouse_inventory_robot/` | The assignment package — everything you write lives here. |
| `turtlebot4/`, `turtlebot4_simulator/`, `create3_sim/` | TurtleBot 4 and Create 3 description, bringup and Gazebo simulation. |
| `xarm_ros2/` | UFACTORY Lite6 arm description, controllers and SDK. |

Only the first is course material; the rest are upstream packages vendored so
the workspace builds from source.

## What you should modify

Please only modify `./warehouse_inventory_robot/launch/mission.launch.py` and `./warehouse_inventory_robot/warehouse_inventory_robot/mission_node.py`