# Copyright 2021 iRobot Corporation. All Rights Reserved.
# @author Rodrigo Jose Causarano Nunez (rcausaran@irobot.com)
#
# Launch Create(R) 3 with diffdrive controller in Gazebo and optionally also in RViz.

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration, NotEqualsSubstitution, PathJoinSubstitution
from launch_ros.actions import Node

ARGUMENTS = [
    # Must match the file the ros2_control plugin loads from the URDF. The
    # spawner's params are applied AFTER the plugin's, so whatever is named
    # here wins: leaving it hardcoded to control.yaml silently reverted
    # enable_odom_tf and left nothing publishing odom -> base_link.
    DeclareLaunchArgument('control_config', default_value='control.yaml',
                          description='ros2_control config filename'),
    DeclareLaunchArgument('namespace', default_value='',
                          description='Robot namespace'),
]


def generate_launch_description():
    pkg_create3_control = get_package_share_directory('irobot_create_control')

    namespace = LaunchConfiguration('namespace')

    control_params_file = PathJoinSubstitution(
        [pkg_create3_control, 'config', LaunchConfiguration('control_config')])

    diffdrive_controller_node = Node(
        package='controller_manager',
        executable='spawner',
        namespace=namespace,  # Namespace is not pushed when used in EventHandler
        parameters=[control_params_file],
        arguments=[
            'diffdrive_controller',
            '-c',
            'controller_manager',
            '--controller-manager-timeout',
            '30'
        ],
        output='screen',
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'joint_state_broadcaster',
            '-c',
            'controller_manager',
            '--controller-manager-timeout',
            '30'
        ],
        output='screen',
    )

    # Ensure diffdrive_controller_node starts after joint_state_broadcaster_spawner
    diffdrive_controller_callback = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[diffdrive_controller_node],
        )
    )

    # Static transform from <namespace>/odom to odom
    # See https://github.com/ros-controls/ros2_controllers/pull/533
    tf_namespaced_odom_publisher = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='tf_namespaced_odom_publisher',
        arguments=['0', '0', '0',
                   '0', '0', '0',
                   'odom', [namespace, '/odom']],
        remappings=[
            ('/tf', 'tf'),
            ('/tf_static', 'tf_static')
        ],
        output='screen',
        condition=IfCondition(NotEqualsSubstitution(LaunchConfiguration('namespace'), ''))
    )

    # Static transform from <namespace>/base_link to base_link
    tf_namespaced_base_link_publisher = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='tf_namespaced_base_link_publisher',
        arguments=['0', '0', '0',
                   '0', '0', '0',
                   [namespace, '/base_link'], 'base_link'],
        remappings=[
            ('/tf', 'tf'),
            ('/tf_static', 'tf_static')
        ],
        output='screen',
        condition=IfCondition(NotEqualsSubstitution(LaunchConfiguration('namespace'), ''))
    )

    ld = LaunchDescription(ARGUMENTS)

    ld.add_action(joint_state_broadcaster_spawner)
    ld.add_action(diffdrive_controller_callback)
    ld.add_action(tf_namespaced_odom_publisher)
    ld.add_action(tf_namespaced_base_link_publisher)

    return ld
