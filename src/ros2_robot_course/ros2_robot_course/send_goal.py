#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
send_goal.py  ——  命令行一键发送 Nav2 导航目标点（免 RViz 鼠标操作）

用法（需先启动 nav2_localization.launch.py）：
  ros2 run ros2_robot_course send_goal <x> <y> [yaw_rad]

示例：
  ros2 run ros2_robot_course send_goal 3.0 0.0        # 去 (3.0, 0.0)，朝向 0°
  ros2 run ros2_robot_course send_goal -3.0 0.0 3.14  # 去 (-3.0, 0.0)，朝向 180°

到达成功会打印 “✅ 已到达目标点！”。
"""
import math
import sys

import rclpy
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node


class SendGoal(Node):
    def __init__(self):
        super().__init__('send_goal_client')
        self._client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

    def send(self, x, y, yaw):
        self.get_logger().info('等待 Nav2 导航服务器 navigate_to_pose ...')
        if not self._client.wait_for_server(timeout_sec=30.0):
            self.get_logger().error(
                '找不到 navigate_to_pose，请先确认 nav2_localization.launch.py 已启动完成')
            return False

        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = float(x)
        goal.pose.pose.position.y = float(y)
        goal.pose.pose.orientation.z = math.sin(float(yaw) / 2.0)
        goal.pose.pose.orientation.w = math.cos(float(yaw) / 2.0)

        self.get_logger().info(f'发送目标点：x={x}  y={y}  yaw={yaw}')
        fut = self._client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, fut)
        handle = fut.result()
        if handle is None or not handle.accepted:
            self.get_logger().error('目标点被拒绝')
            return False
        self.get_logger().info('目标已接受，开始导航...')

        result_fut = handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_fut)
        status = result_fut.result().status
        if status == 4:
            self.get_logger().info('✅ 已到达目标点！')
            return True
        self.get_logger().warn(f'导航结束，状态码={status}（4=成功 5=取消 6=失败）')
        return False


def main():
    argv = [a for a in sys.argv[1:] if not a.startswith('__')]
    x = argv[0] if len(argv) > 0 else '3.0'
    y = argv[1] if len(argv) > 1 else '0.0'
    yaw = argv[2] if len(argv) > 2 else '0.0'
    rclpy.init()
    node = SendGoal()
    ok = False
    try:
        ok = node.send(x, y, yaw)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
