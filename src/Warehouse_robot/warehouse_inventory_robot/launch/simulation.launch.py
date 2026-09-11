import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.conditions import UnlessCondition
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node

def generate_launch_description():
    pkg_share = get_package_share_directory('warehouse_inventory_robot')
    pkg_tb4_gz = get_package_share_directory('turtlebot4_gz_bringup')

    default_x = '0.0'
    default_y = '0.0'

    declare_x = DeclareLaunchArgument('x', default_value=default_x)
    declare_y = DeclareLaunchArgument('y', default_value=default_y)
    declare_z = DeclareLaunchArgument('z', default_value='0.0')
    declare_yaw = DeclareLaunchArgument('yaw', default_value='0.0')

    # One code base, three grades. Everything that differs between them is
    # derived from this single argument rather than kept on separate branches.
    #
    #   e  static world, ground truth odometry
    #   c  walking actor, ground truth odometry
    #   a  walking actor, wheel odometry that drifts, so AMCL has work to do
    # Reads GRADE when no grade:= is given, matching mission.launch.py, so this
    # behaves the same whether it is included from there or launched on its own.
    declare_grade = DeclareLaunchArgument(
        'grade', default_value=EnvironmentVariable('GRADE', default_value='e'),
        choices=['e', 'c', 'a'],
        description='Which grade to configure the simulation for (default: $GRADE, or e)')
    grade = LaunchConfiguration('grade')

    # The C and A grades add a dynamic obstacle the robot has to avoid.
    world = PythonExpression(
        ["'warehouse_dynamic' if '", grade, "' in ('c', 'a') else 'warehouse'"])

    # A needs odometry that drifts. With the ground truth transform below there
    # would be nothing for AMCL to correct, so the exercise would be hollow.
    control_config = PythonExpression(
        ["'control_wheel_odom.yaml' if '", grade,
         "' == 'a' else 'control.yaml'"])

    grade_is_a = PythonExpression(["'", grade, "' == 'a'"])

    # 1. Gazebo + TurtleBot4 Base Spawn
    turtlebot4_gz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_tb4_gz, 'launch', 'turtlebot4_gz.launch.py')
        ),
        launch_arguments={
            'world': world,
            'control_config': control_config,
            'model': 'standard',
            'rviz':  'false',
            'x':     LaunchConfiguration('x'),
            'y':     LaunchConfiguration('y'),
            'z':     LaunchConfiguration('z'),
            'yaw':   LaunchConfiguration('yaw'),
        }.items()
    )

    gripper_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/vacuum_gripper/attach@std_msgs/msg/Empty]gz.msgs.Empty',
            '/vacuum_gripper/detach@std_msgs/msg/Empty]gz.msgs.Empty',
        ],
        output='screen',
    )

    # Ground truth odometry, for the E and C grades only.
    #
    # This bridges Gazebo's exact pose into /tf as odom -> base_link, so those
    # grades never have to think about localization. The A grade must not have
    # it: with a perfect transform in place AMCL has nothing to correct, and
    # two publishers on the same TF edge would fight in any case. There the
    # diffdrive controller publishes the edge itself, from wheel encoders,
    # selected through control_config above.
    odom_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='odom_gt_bridge',
        arguments=['--ros-args', '-p', f'config_file:={os.path.join(pkg_share, "config", "odom_bridge.yaml")}'],
        output='screen',
        parameters=[{'use_sim_time': True}],
        condition=UnlessCondition(grade_is_a),
    )

    # 3. RViz2
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', os.path.join(pkg_share, 'rviz', 'warehouse.rviz')], # Make sure this file exists!
        parameters=[{'use_sim_time': True}]
    )

    # RViz is gated on the simulation actually publishing, not on a fixed delay.
    # It runs with use_sim_time, so starting it while /clock has no publisher
    # leaves its clock at zero and every TF lookup failing -- an empty view that
    # never recovers. A wall-clock delay only hides that on a fast machine.
    #
    # /clock alone, deliberately. /scan would be the stronger signal, but it is a
    # gpu_lidar: on a machine whose rendering engine fails to initialise it never
    # appears at all, and gating on it would withhold RViz for the full timeout
    # exactly when you most need to look at what the simulation is doing.
    wait_for_rviz = Node(
        package='warehouse_inventory_robot',
        executable='wait_for_ready',
        name='wait_for_rviz',
        output='screen',
        arguments=['--label', 'rviz',
                   '--topic', '/clock',
                   '--timeout', '300'],
    )

    return LaunchDescription([
        declare_grade, declare_x, declare_y, declare_z, declare_yaw,
        turtlebot4_gz, gripper_bridge, odom_bridge,
        wait_for_rviz,
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=wait_for_rviz,
                on_exit=[rviz_node],
            )
        ),
    ])