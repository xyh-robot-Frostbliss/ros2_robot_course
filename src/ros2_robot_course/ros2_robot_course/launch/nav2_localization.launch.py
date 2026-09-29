#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nav2_localization.launch.py  ——  任务 3 + 任务 4：加载地图 + AMCL 定位 + Nav2 导航

启动内容：
  1) 复用 robot_gazebo.launch.py（Gazebo 世界 + 机器人 + TF）
  2) map_server 加载 maps/map.yaml（先用 slam_toolbox 建好并保存的地图）
  3) AMCL 粒子滤波定位（map -> odom）
  4) Nav2 导航栈：controller_server / planner_server / behavior_server /
     bt_navigator / waypoint_follower / velocity_smoother + lifecycle_manager
  5) RViz2（config/nav2.rviz，含 2D Pose Estimate 与 Nav2 Goal 工具）

操作：
  * RViz 顶部工具栏 "2D Pose Estimate"：在地图上点击并拖动，给出机器人初始位姿
  * RViz 顶部工具栏 "Nav2 Goal"：依次点击多个目标点，实现多目标自主导航

注意：本 launch 不启动 SLAM，地图为静态加载，符合"建图后重启再导航"的考核要求。
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('ros2_robot_course')
    nav2_params_file = os.path.join(pkg_share, 'config', 'nav2_params.yaml')
    default_map = os.path.join(pkg_share, 'maps', 'map.yaml')
    rviz_file = os.path.join(pkg_share, 'config', 'nav2.rviz')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    map_yaml = LaunchConfiguration('map', default=default_map)
    autostart = LaunchConfiguration('autostart', default='true')

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='true', description='Use Gazebo /clock')
    declare_map = DeclareLaunchArgument(
        'map', default_value=default_map,
        description='Full path to the map yaml file to load')
    declare_autostart = DeclareLaunchArgument(
        'autostart', default_value='true', description='Automatically start Nav2 lifecycle nodes')

    # 公共参数：nav2 参数文件 + 仿真时间
    params = [nav2_params_file, {'use_sim_time': use_sim_time}]

    # -------------------- 复用仿真 --------------------
    robot_gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'robot_gazebo.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'gui': 'true',
            'rviz': 'false',
        }.items(),
    )

    # -------------------- 地图服务器 --------------------
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[nav2_params_file,
                    {'use_sim_time': use_sim_time,
                     'yaml_filename': map_yaml}],
    )

    # -------------------- AMCL 定位 --------------------
    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=params,
    )

    # -------------------- Nav2 控制器 / 规划器 / 行为 --------------------
    controller_server = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=params,
        # 速度链：controller_server -> /cmd_vel_nav -> velocity_smoother -> /cmd_vel -> Gazebo
        remappings=[('cmd_vel', 'cmd_vel_nav')],
    )

    planner_server = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=params,
    )

    behavior_server = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        parameters=params,
    )

    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=params,
    )

    waypoint_follower = Node(
        package='nav2_waypoint_follower',
        executable='waypoint_follower',
        name='waypoint_follower',
        output='screen',
        parameters=params,
    )

    velocity_smoother = Node(
        package='nav2_velocity_smoother',
        executable='velocity_smoother',
        name='velocity_smoother',
        output='screen',
        parameters=params,
        remappings=[('cmd_vel', 'cmd_vel_nav'),
                    ('cmd_vel_smoothed', 'cmd_vel')],
    )

    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager',
        output='screen',
        parameters=[nav2_params_file,
                    {'use_sim_time': use_sim_time,
                     'autostart': autostart,
                     'node_names': [
                         'map_server',
                         'amcl',
                         'controller_server',
                         'planner_server',
                         'behavior_server',
                         'bt_navigator',
                         'waypoint_follower',
                         'velocity_smoother',
                     ]}],
    )

    # -------------------- RViz2 --------------------
    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_file],
        parameters=[{'use_sim_time': use_sim_time}],
    )

    return LaunchDescription([
        declare_use_sim_time,
        declare_map,
        declare_autostart,
        robot_gazebo,
        map_server,
        amcl,
        controller_server,
        planner_server,
        behavior_server,
        bt_navigator,
        waypoint_follower,
        velocity_smoother,
        lifecycle_manager,
        rviz2,
    ])
