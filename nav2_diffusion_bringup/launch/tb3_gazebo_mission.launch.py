# Copyright 2026 nav2_experimental_planner contributors
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

r"""
Automated headless Gazebo closed-loop benchmark for the DiffusionController.

Brings up the TB3 Gazebo sim (reusing tb3_gazebo_diffusion.launch.py, headless, no
RViz) and an in-launch ``sim_mission`` node that sends one NavigateToPose goal,
records the executed odometry, and writes a Markdown result file. The mission node
runs *inside* this launch so it shares the DDS graph (external-process discovery is
unreliable in restricted sandboxes — docs/simulation.md section 10.5). When the
mission node exits, the whole launch shuts down.

Example::

    ros2 launch nav2_diffusion_bringup tb3_gazebo_mission.launch.py \\
        goal_x:=0.0 goal_y:=-0.5 results_file:=/tmp/sim_mission_result.md
"""

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, EmitEvent, IncludeLaunchDescription,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_dir = get_package_share_directory('nav2_diffusion_bringup')

    goal_x = LaunchConfiguration('goal_x')
    goal_y = LaunchConfiguration('goal_y')
    goal_yaw = LaunchConfiguration('goal_yaw')
    timeout_sec = LaunchConfiguration('timeout_sec')
    label = LaunchConfiguration('label')
    results_file = LaunchConfiguration('results_file')

    declare_args = [
        DeclareLaunchArgument('goal_x', default_value='0.0'),
        DeclareLaunchArgument('goal_y', default_value='-0.5'),
        DeclareLaunchArgument('goal_yaw', default_value='0.0'),
        DeclareLaunchArgument('timeout_sec', default_value='120.0'),
        DeclareLaunchArgument(
            'label', default_value='Diffusion (Mode A) in Gazebo'),
        DeclareLaunchArgument(
            'results_file', default_value='/tmp/sim_mission_result.md'),
    ]

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_dir, 'launch', 'tb3_gazebo_diffusion.launch.py')
        ),
        launch_arguments={'use_rviz': 'False', 'headless': 'True'}.items(),
    )

    mission = Node(
        package='nav2_diffusion_bringup',
        executable='sim_mission.py',
        name='sim_mission',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'goal_x': goal_x,
            'goal_y': goal_y,
            'goal_yaw': goal_yaw,
            'timeout_sec': timeout_sec,
            'label': label,
            'results_file': results_file,
        }],
    )

    # Tear the whole launch down once the mission node finishes.
    shutdown_on_mission_exit = RegisterEventHandler(
        OnProcessExit(
            target_action=mission,
            on_exit=[EmitEvent(event=Shutdown(reason='mission complete'))],
        )
    )

    return LaunchDescription(
        declare_args + [sim, mission, shutdown_on_mission_exit])
