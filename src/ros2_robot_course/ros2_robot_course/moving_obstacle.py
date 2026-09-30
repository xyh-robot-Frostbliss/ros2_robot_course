#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
moving_obstacle.py —— 动态移动障碍物（演示 Nav2 动态避障 / 局部重规划）

做什的：
  1) 把 world/moving_obstacle.sdf 生成到 Gazebo 世界（只在导航演示时出现，
     不参与建图，保证 SLAM 地图干净）；
  2) 让这个红色方块沿一条走廊来回巡逻（用 `gz model` 直接设置位姿）；
  3) 退出时删除该障碍物。

机器人全程用 2D 激光实时看到它，Nav2 的局部代价地图会把新位置标成障碍，
DWB 控制器据此减速/绕行，必要时全局重规划 —— 这就是"动态避障"。

用法（需先启动 nav2_localization.launch.py）：
  ros2 run ros2_robot_course moving_obstacle
  # 可调参数：
  #   --ros-args -p x0:=-3.0 -p y0:=-4.4 -p x1:=3.0 -p y1:=-4.4 -p period:=12.0
"""
import os
import subprocess
import threading
import time

import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node


def _gz(*args):
    try:
        subprocess.run(['gz', 'model', *args], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=2.0)
    except Exception:
        pass


class MovingObstacle(Node):
    def __init__(self):
        super().__init__('moving_obstacle')
        self.declare_parameter('entity', 'moving_obstacle')
        self.declare_parameter('sdf', '')
        self.declare_parameter('x0', -3.0)
        self.declare_parameter('y0', -4.4)
        self.declare_parameter('x1', 3.0)
        self.declare_parameter('y1', -4.4)
        self.declare_parameter('z', 0.35)
        self.declare_parameter('period', 12.0)   # 一个来回的周期（秒）
        self.declare_parameter('rate', 10.0)     # 更新频率（Hz）

        self.name = self.get_parameter('entity').value
        sdf = self.get_parameter('sdf').value
        if not sdf:
            sdf = os.path.join(get_package_share_directory('ros2_robot_course'),
                               'world', 'moving_obstacle.sdf')
        self.sdf = sdf
        self.x0 = float(self.get_parameter('x0').value)
        self.y0 = float(self.get_parameter('y0').value)
        self.x1 = float(self.get_parameter('x1').value)
        self.y1 = float(self.get_parameter('y1').value)
        self.z = float(self.get_parameter('z').value)
        self.period = max(1.0, float(self.get_parameter('period').value))
        self.rate = max(1.0, float(self.get_parameter('rate').value))

        self._stop = False
        self._spawn()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.get_logger().info(
            f'动态障碍物已启动：({self.x0},{self.y0}) <-> ({self.x1},{self.y1})，'
            f'周期 {self.period:.1f}s')

    def _spawn(self):
        _gz('-d', '-m', self.name)                 # 若已存在先删
        _gz('-m', self.name, '-f', self.sdf)       # 生成到世界的起点
        _gz('-m', self.name, '-x', f'{self.x0:.3f}', '-y', f'{self.y0:.3f}',
            '-z', f'{self.z:.3f}')

    def _loop(self):
        t0 = time.monotonic()
        while not self._stop and rclpy.ok():
            u = ((time.monotonic() - t0) % self.period) / self.period
            tri = 2.0 * u if u < 0.5 else 2.0 * (1.0 - u)   # 往返三角波
            x = self.x0 + (self.x1 - self.x0) * tri
            y = self.y0 + (self.y1 - self.y0) * tri
            _gz('-m', self.name, '-x', f'{x:.3f}', '-y', f'{y:.3f}',
                '-z', f'{self.z:.3f}')
            time.sleep(1.0 / self.rate)

    def destroy_node(self):
        self._stop = True
        _gz('-d', '-m', self.name)
        self.get_logger().info('动态障碍物已移除')
        super().destroy_node()


def main():
    rclpy.init()
    node = MovingObstacle()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
