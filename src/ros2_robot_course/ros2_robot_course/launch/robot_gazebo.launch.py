#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
robot_gazebo.launch.py  ——  任务 1：一键启动 Gazebo 室内场景 + 差速机器人

启动内容：
  1) Gazebo 11 载入自建 world/room.world
  2) robot_state_publisher 解析 urdf/robot.urdf.xacro，发布 base_link -> laser_link 等 TF
  3) spawn_entity 把机器人生成到仿真世界
  4) 可选打开 RViz2（robot.rviz，查看模型 / TF / LaserScan）

启动后可用：
  ros2 topic echo /scan
  ros2 topic echo /odom
  ros2 run teleop_twist_keyboard teleop_twist_keyboard
"""
import os
import shutil
import subprocess

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def build_robot_description(xacro_file, urdf_file):
    """优先用 xacro 解析 .xacro；环境缺少 xacro 时回退到展开好的 .urdf。"""
    try:
        import xacro  # ROS2 标准方式
        return xacro.process_file(xacro_file).toxml()
    except Exception:
        pass
    if shutil.which('xacro'):
        try:
            return subprocess.check_output(['xacro', xacro_file], text=True)
        except Exception:
            pass
    with open(urdf_file, 'r') as f:
        return f.read()


def generate_launch_description():
    pkg_share = get_package_share_directory('ros2_robot_course')
    xacro_file = os.path.join(pkg_share, 'urdf', 'robot.urdf.xacro')
    urdf_file = os.path.join(pkg_share, 'urdf', 'robot.urdf')
    world_file = os.path.join(pkg_share, 'world', 'room.world')
    rviz_file = os.path.join(pkg_share, 'config', 'robot.rviz')

    # 生成 URDF 字符串，作为 robot_description 参数
    robot_description = ParameterValue(
        build_robot_description(xacro_file, urdf_file), value_type=str)

    # -------------------- 启动参数 --------------------
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    gui = LaunchConfiguration('gui', default='true')
    rviz = LaunchConfiguration('rviz', default='false')
    x = LaunchConfiguration('x', default='0.0')
    y = LaunchConfiguration('y', default='-4.8')
    z = LaunchConfiguration('z', default='0.10')
    yaw = LaunchConfiguration('yaw', default='1.5708')

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='true', description='Use Gazebo /clock')
    declare_gui = DeclareLaunchArgument(
        'gui', default_value='true', description='Start Gazebo client GUI')
    declare_rviz = DeclareLaunchArgument(
        'rviz', default_value='false', description='Start RViz2')
    declare_x = DeclareLaunchArgument('x', default_value='0.0', description='Spawn x')
    declare_y = DeclareLaunchArgument('y', default_value='-4.8', description='Spawn y')
    declare_z = DeclareLaunchArgument('z', default_value='0.10', description='Spawn z')
    declare_yaw = DeclareLaunchArgument('yaw', default_value='1.5708', description='Spawn yaw')

    # -------------------- Gazebo 仿真世界 --------------------
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py')
        ),
        launch_arguments={
            'world': world_file,
            'gui': gui,
            'verbose': 'false',
            'pause': 'false',
        }.items(),
    )

    # -------------------- 机器人状态发布 (TF) --------------------
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': use_sim_time,
        }],
    )

    # -------------------- 在 Gazebo 中生成机器人 --------------------
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        name='spawn_entity',
        output='screen',
        arguments=[
            '-topic', 'robot_description',
            '-entity', 'ros2_robot',
            '-x', x, '-y', y, '-z', z, '-Y', yaw,
        ],
    )

    # -------------------- 可选 RViz2 --------------------
    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_file],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(rviz),
    )

    return LaunchDescription([
        declare_use_sim_time,
        declare_gui,
        declare_rviz,
        declare_x,
        declare_y,
        declare_z,
        declare_yaw,
        gazebo,
        robot_state_publisher,
        TimerAction(period=3.0, actions=[spawn_entity]),
        rviz2,
    ])
