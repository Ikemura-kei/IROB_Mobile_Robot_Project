# Copyright 2021 Clearpath Robotics, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# @author Roni Kreinin (rkreinin@clearpathrobotics.com)


from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import UnlessCondition
from launch.substitutions import Command, PathJoinSubstitution
from launch.substitutions.launch_configuration import LaunchConfiguration

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


ARGUMENTS = [
    DeclareLaunchArgument('model', default_value='standard',
                          choices=['standard', 'lite'],
                          description='Turtlebot4 Model'),
    DeclareLaunchArgument('use_sim_time', default_value='false',
                          choices=['true', 'false'],
                          description='use_sim_time'),
    DeclareLaunchArgument('robot_name', default_value='turtlebot4',
                          description='Robot name'),
    DeclareLaunchArgument('namespace', default_value=LaunchConfiguration('robot_name'),
                          description='Robot namespace'),
    # Which ros2_control config create3.urdf.xacro loads. control.yaml keeps
    # enable_odom_tf false and relies on a ground truth transform; the
    # wheel-odometry variant turns it on so odometry drifts and AMCL has
    # something to correct. Passed down from the grade argument.
    DeclareLaunchArgument('control_config', default_value='control.yaml',
                          description='ros2_control config filename'),
]


def generate_launch_description():
    pkg_turtlebot4_description = get_package_share_directory('turtlebot4_description')
    xacro_file = PathJoinSubstitution([pkg_turtlebot4_description,
                                       'urdf',
                                       LaunchConfiguration('model'),
                                       'tb4_lite6.urdf.xacro'])
    namespace = LaunchConfiguration('namespace')

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[
            {'use_sim_time': LaunchConfiguration('use_sim_time')},
            # value_type=str is required, not cosmetic. Without it launch_ros
            # tries to infer the parameter's type by running the xacro output
            # through yaml.safe_load. xacro preserves XML comments, so a single
            # comment line ending in a colon, or one starting with "- ", makes
            # the whole URDF look like a YAML mapping or list and the launch
            # dies with "Unable to parse the value of parameter
            # robot_description as yaml" -- pointing at the parameter rather
            # than at the comment that actually broke it. Declaring the type
            # skips the guess entirely.
            {'robot_description': ParameterValue(
                Command([
                    'xacro', ' ', xacro_file, ' ',
                    'gazebo:=ignition', ' ',
                    'control_config:=', LaunchConfiguration('control_config'), ' ',
                    'namespace:=', namespace]),
                value_type=str)},
        ],
        remappings=[
            ('/tf', 'tf'),
            ('/tf_static', 'tf_static')
        ]
    )

    # Simulation must NOT run this node. With no source_list parameter,
    # joint_state_publisher does not relay anything -- it invents values (zeros,
    # or the nearest joint limit) for every non-fixed joint in robot_description
    # and publishes them on /joint_states at 10 Hz. Under Gazebo,
    # joint_state_broadcaster already publishes the true state of those same
    # joints on that same topic, so robot_state_publisher receives two
    # contradictory streams and recomputes TF from whichever arrived last. The
    # result is arm frames visibly alternating in RViz between their real pose
    # and a fabricated zero pose.
    #
    # This was latent upstream: with only wheel joints the flicker is invisible,
    # because a continuous wheel joint looks identical at any angle. Mounting a
    # 6-DOF arm is what made it show. The flicker also disappears when the arm
    # sits at its default pose, since both sources then agree -- which is why it
    # only appears once the arm is commanded somewhere.
    #
    # Kept for non-simulated use (real robot, or inspecting the model in RViz
    # with no controller running), where it is the only source of joint states.
    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        output='screen',
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}],
        remappings=[
            ('/tf', 'tf'),
            ('/tf_static', 'tf_static')
        ],
        condition=UnlessCondition(LaunchConfiguration('use_sim_time'))
    )

    # Define LaunchDescription variable
    ld = LaunchDescription(ARGUMENTS)
    # Add nodes to LaunchDescription
    ld.add_action(robot_state_publisher)
    ld.add_action(joint_state_publisher)
    return ld
