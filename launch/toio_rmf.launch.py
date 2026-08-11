# Copyright 2026
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

"""
Bring up a whole toio fleet with one command.

Starts the Open-RMF core, the toio fleet adapter and, optionally, the
Gazebo simulation with Nav2. The RMF core portion mirrors rmf_demos'
common.launch.xml, minus the door/lift supervisors that a toio
playground does not need.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import GroupAction
from launch.actions import IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PythonExpression
from launch_ros.actions import Node
from launch_ros.actions import SetParameter
from launch_xml.launch_description_sources import XMLLaunchDescriptionSource


def generate_launch_description():
    maps_dir = get_package_share_directory('toio_rmf_maps')
    adapter_dir = get_package_share_directory('toio_fleet_adapter')
    gazebo_dir = get_package_share_directory('toio_gazebo')
    navigation_dir = get_package_share_directory('toio_navigation')
    bringup_dir = get_package_share_directory('toio_rmf_bringup')

    use_sim_time = LaunchConfiguration('use_sim_time')
    mat = LaunchConfiguration('mat')
    rmf_headless = LaunchConfiguration('rmf_headless')
    run_sim = LaunchConfiguration('run_sim')
    run_nav = LaunchConfiguration('run_nav')
    use_nav_rviz = LaunchConfiguration('use_nav_rviz')
    server_uri = LaunchConfiguration('server_uri')
    bidding_time_window = LaunchConfiguration('bidding_time_window')
    robots = LaunchConfiguration('robots')
    peer_footprint_size = LaunchConfiguration('peer_footprint_size')

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation clock (Gazebo) instead of wall clock')

    declare_mat_cmd = DeclareLaunchArgument(
        'mat',
        default_value='a3',
        description='toio play mat to use: a3 or a4')

    declare_headless_cmd = DeclareLaunchArgument(
        'rmf_headless',
        default_value='false',
        description='Do not launch the RMF schedule visualizer RViz')

    declare_run_sim_cmd = DeclareLaunchArgument(
        'run_sim',
        default_value='true',
        description='Also launch the toio_gazebo multi-robot simulation')

    declare_run_nav_cmd = DeclareLaunchArgument(
        'run_nav',
        default_value='true',
        description='Also launch toio_navigation for the robots')

    declare_use_nav_rviz_cmd = DeclareLaunchArgument(
        'use_nav_rviz',
        default_value='false',
        description='Launch the per-robot Nav2 RViz windows')

    declare_server_uri_cmd = DeclareLaunchArgument(
        'server_uri',
        default_value='',
        description='URI of the rmf-web api server (optional)')

    declare_bidding_time_window_cmd = DeclareLaunchArgument(
        'bidding_time_window',
        default_value='2.0',
        description='Time window in seconds for the task bidding process')

    declare_robots_cmd = DeclareLaunchArgument(
        'robots',
        default_value='toio1,toio2',
        description='Comma-separated robot namespaces passed to '
                    'toio_multi_navigation (the Gazebo multi simulation '
                    'itself spawns the fixed toio1/toio2 pair; for other '
                    'robot sets run the simulation or the real-robot '
                    'bringup separately with run_sim:=false)')

    declare_peer_footprint_size_cmd = DeclareLaunchArgument(
        'peer_footprint_size',
        default_value='auto',
        description='Square footprint edge (m) painted for peer robots by '
                    'peer_robot_costmap_publisher, or "auto" to pick per '
                    'mat. Collision testing showed the cube size (0.032) '
                    'lets close-range head-on encounters brush past with '
                    'body contact on A3; 0.10 keeps A3 cubes fully '
                    'separated (closest 49.2 mm). On the smaller A4 mat '
                    '0.10 blocks the corridors entirely (planner '
                    'deadlock), so auto uses 0.06 there, which is safe in '
                    'combination with its one-way nav graph')

    building_yaml = [
        maps_dir, '/maps/toio_', mat, '/toio_', mat, '.building.yaml']
    nav_graph_yaml = [maps_dir, '/maps/toio_', mat, '/nav_graphs/0.yaml']
    fleet_config_yaml = [
        adapter_dir, '/config/toio_fleet_config_', mat, '.yaml']
    world_sdf = [gazebo_dir, '/worlds/toio_', mat, '_map.sdf']
    map_yaml = [navigation_dir, '/maps/toio_', mat, '_map.yaml']

    # ------------------------------------------------------------------
    # Open-RMF core (mirrors rmf_demos common.launch.xml)
    # ------------------------------------------------------------------
    rmf_core = GroupAction([
        # Delivery hands the pickup and dropoff to workcells rather than to
        # the robot, and a play mat has none, so a delivery task would stall
        # at the pickup without these (toio_fleet_adapter#2)
        Node(
            package='toio_rmf_bringup',
            executable='mock_workcells.py',
            # No name= here: the process runs one node per workcell and names
            # them after their guid. Setting it renames both, which collides
            # ("Publisher already registered for node name") and loses the
            # distinction in the logs.
            output='both',
            arguments=[
                '--dispensers', 'toio_dispenser',
                '--ingestors', 'toio_ingestor',
            ],
            parameters=[{'use_sim_time': use_sim_time}]),
        Node(
            package='rmf_traffic_ros2',
            executable='rmf_traffic_schedule',
            name='rmf_traffic_schedule_primary',
            output='both',
            parameters=[{'use_sim_time': use_sim_time}]),
        Node(
            package='rmf_traffic_ros2',
            executable='rmf_traffic_blockade',
            output='both',
            parameters=[{'use_sim_time': use_sim_time}]),
        Node(
            package='rmf_building_map_tools',
            executable='building_map_server',
            arguments=[building_yaml],
            parameters=[{'use_sim_time': use_sim_time}]),
        Node(
            package='rmf_task_ros2',
            executable='rmf_task_dispatcher',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'bidding_time_window': bidding_time_window,
                'use_unique_hex_string_with_task_id': True,
                'server_uri': server_uri,
            }]),
        GroupAction([
            # The fleet-states visualizer draws each robot as a sphere of
            # <fleet_name>_radius (default 0.5 m, which covers the whole
            # mat); override it with half the width of the cube, which is
            # 32 mm square. The nav2 footprint half-diagonal (0.023) makes a
            # sphere noticeably wider than the robot it stands for.
            SetParameter(name='toio_radius', value=0.016),
            IncludeLaunchDescription(
                XMLLaunchDescriptionSource(
                    os.path.join(
                        get_package_share_directory('rmf_visualization'),
                        'visualization.launch.xml')),
                launch_arguments={
                    'use_sim_time': use_sim_time,
                    'map_name': 'L1',
                    'headless': rmf_headless,
                    # RViz view and marker sizes tuned for the tiny toio
                    # mats (the rmf defaults assume tens-of-meters
                    # buildings). lane_width is clamped to >= 0.1 in
                    # rmf_visualization_navgraphs, so the lanes stay 0.1 m
                    # wide; lower transparency keeps them unobtrusive.
                    # waypoint_scale/text_scale are multiples of
                    # lane_width, fleet_state_nose_scale is a multiple of
                    # the robot radius.
                    'viz_config_file':
                        os.path.join(bringup_dir, 'rviz', 'toio_rmf.rviz'),
                    'path_width': '0.01',
                    'lane_width': '0.1',
                    'lane_transparency': '0.3',
                    'waypoint_scale': '0.2',
                    'text_scale': '0.15',
                }.items()),
        ]),
    ])

    # ------------------------------------------------------------------
    # toio fleet adapter
    # ------------------------------------------------------------------
    fleet_adapter = Node(
        package='toio_fleet_adapter',
        executable='fleet_adapter',
        output='both',
        arguments=[
            '-c', fleet_config_yaml,
            '-n', nav_graph_yaml,
        ],
        parameters=[{
            'use_sim_time': use_sim_time,
            'server_uri': server_uri,
        }])

    # ------------------------------------------------------------------
    # Robot layer: Gazebo simulation + Nav2 (optional)
    # ------------------------------------------------------------------
    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                gazebo_dir, 'launch', 'toio_multi_simulation.launch.py')),
        condition=IfCondition(run_sim),
        launch_arguments={
            'world': world_sdf,
            'world_frame': ['toio_', mat, '_map'],
        }.items())

    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                navigation_dir, 'launch',
                'toio_multi_navigation.launch.py')),
        condition=IfCondition(run_nav),
        launch_arguments={
            'map': map_yaml,
            'use_sim_time': use_sim_time,
            'use_rviz': use_nav_rviz,
            'robots': robots,
            'peer_footprint_size': PythonExpression(
                ["'", peer_footprint_size, "' if '", peer_footprint_size,
                 "' != 'auto' else ('0.10' if '", mat,
                 "' == 'a3' else '0.06')"]),
        }.items())

    ld = LaunchDescription()
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_mat_cmd)
    ld.add_action(declare_headless_cmd)
    ld.add_action(declare_run_sim_cmd)
    ld.add_action(declare_run_nav_cmd)
    ld.add_action(declare_use_nav_rviz_cmd)
    ld.add_action(declare_server_uri_cmd)
    ld.add_action(declare_bidding_time_window_cmd)
    ld.add_action(declare_robots_cmd)
    ld.add_action(declare_peer_footprint_size_cmd)
    ld.add_action(rmf_core)
    ld.add_action(fleet_adapter)
    ld.add_action(simulation)
    ld.add_action(navigation)
    return ld
