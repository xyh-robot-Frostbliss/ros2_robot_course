#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
slam.launch.py  ——  任务 2：Gazebo + 机器人 + slam_toolbox 在线异步建图 + RViz2

启动内容：
  1) 复用 robot_gazebo.launch.py（Gazebo 世界 + 机器人 + TF）
  2) slam_toolbox async_slam_toolbox_node（使用 config/slam_toolbox.yaml）
  3) RViz2（config/slam.rviz，预设 Map / LaserScan / RobotModel / TF 面板）

建图流程：
  另开终端执行 teleop_twist_keyboard 遥控小车遍历房间，
  保存地图：
    ros2 run nav2_map_server map_saver_cli -f <包源码目录>/maps/map
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
    slam_params_file = os.path.join(pkg_share, 'config', 'slam_toolbox.yaml')
    rviz_file = os.path.join(pkg_share, 'config', 'slam.rviz')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='true', description='Use Gazebo /clock')

    # 复用仿真启动
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

    # slam_toolbox 在线异步建图节点
    slam_toolbox = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[slam_params_file, {'use_sim_time': use_sim_time}],
    )

    # RViz2 可视化
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
        robot_gazebo,
        slam_toolbox,
        rviz2,
    ])
