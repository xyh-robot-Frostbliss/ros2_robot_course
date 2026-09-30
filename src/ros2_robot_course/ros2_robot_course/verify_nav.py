#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_nav.py —— Nav2 多目标导航自动验收 / 量化复盘

作用：
  启动 nav2_localization.launch.py 之后运行本脚本，它会：
    1) 等待 Nav2 导航服务器就绪；
    2) 依次发送若干个目标点（默认 3 个：东侧 / 西侧 / 北侧）；
    3) 全程订阅 /scan、/cmd_vel、/amcl_pose，统计每个目标点的：
         - 结果（成功/失败）
         - 耗时
         - 到点位置误差(m) / 朝向误差(°)
         - 全程最小激光余量(m)（用于估算是否贴障/碰撞）
      并统计整个过程的 /scan、/cmd_vel 实测频率；
    4) 在 verify_logs/verify_<时间戳>/ 下写出 summary.md 与 data.jsonl。

用法（需先 ros2 launch ros2_robot_course nav2_localization.launch.py）：
  ros2 run ros2_robot_course verify_nav
  # 或直接： python3 src/ros2_robot_course/ros2_robot_course/verify_nav.py
  # 自定义目标点（x,y,yaw 用分号隔开）：
  #   ... verify_nav --goals "4.0,-0.5,0.0;-4.0,-0.5,3.14;0.0,3.0,1.57"

证据等级：本脚本产出的所有数字均为 [实测]。
"""
import argparse
import json
import math
import os
import time

import numpy as np
import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped, Twist
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.qos import (QoSProfile, QoSDurabilityPolicy, QoSHistoryPolicy,
                       QoSReliabilityPolicy, qos_profile_sensor_data)
from sensor_msgs.msg import LaserScan

# 默认目标点（已用当前 map.pgm 校验过 clearance：2.57 / 2.56 / 1.40 m）
DEFAULT_GOALS = [
    (4.0, -0.5, 0.0),          # 东侧
    (-4.0, -0.5, math.pi),     # 西侧（穿过场地中部）
    (0.0, 3.0, math.pi / 2),   # 北侧
]

# 激光余量低于该值即视为"疑似贴障/碰撞"
COLLISION_CLEARANCE = 0.15
# 验收阈值（README 第九节）
GOAL_XY_TOL = 0.25          # m
GOAL_YAW_TOL_DEG = 15.0     # deg
GOAL_TIME_LIMIT = 60.0      # s


def yaw_to_quat(yaw):
    from geometry_msgs.msg import Quaternion
    q = Quaternion()
    q.z = math.sin(yaw / 2.0)
    q.w = math.cos(yaw / 2.0)
    return q


def quat_to_yaw(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                      1.0 - 2.0 * (q.y * q.y + q.z * q.z))


class VerifyNav(BasicNavigator):
    def __init__(self):
        super().__init__(node_name='verify_nav')
        self.latest_pose = None
        self.min_range = float('inf')
        self.scan_count = 0
        self.cmd_count = 0

        pose_qos = QoSProfile(depth=1,
                              durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
                              reliability=QoSReliabilityPolicy.RELIABLE,
                              history=QoSHistoryPolicy.KEEP_LAST)
        self.create_subscription(PoseWithCovarianceStamped, 'amcl_pose',
                                 self._on_pose, pose_qos)
        self.create_subscription(LaserScan, 'scan', self._on_scan,
                                 qos_profile_sensor_data)
        self.create_subscription(Twist, 'cmd_vel', self._on_cmd, 10)

    def _on_pose(self, msg):
        self.latest_pose = msg

    def _on_scan(self, msg):
        self.scan_count += 1
        arr = np.asarray(msg.ranges, dtype=np.float64)
        arr = arr[np.isfinite(arr)]
        arr = arr[arr >= msg.range_min]
        if arr.size:
            m = float(arr.min())
            if m < self.min_range:
                self.min_range = m

    def _on_cmd(self, msg):
        self.cmd_count += 1

    def reset_leg(self):
        self.min_range = float('inf')

    def pose_error(self, x, y, yaw):
        if self.latest_pose is None:
            return None, None
        p = self.latest_pose.pose.pose
        dist = math.hypot(p.position.x - x, p.position.y - y)
        dyaw = math.atan2(math.sin(quat_to_yaw(p.orientation) - yaw),
                          math.cos(quat_to_yaw(p.orientation) - yaw))
        return dist, math.degrees(abs(dyaw))

    def make_pose(self, x, y, yaw):
        from geometry_msgs.msg import PoseStamped
        p = PoseStamped()
        p.header.frame_id = 'map'
        p.header.stamp = self.get_clock().now().to_msg()
        p.pose.position.x = float(x)
        p.pose.position.y = float(y)
        p.pose.orientation = yaw_to_quat(yaw)
        return p


def parse_goals(s):
    goals = []
    for part in s.split(';'):
        part = part.strip()
        if not part:
            continue
        xs = [float(v) for v in part.split(',')]
        if len(xs) == 2:
            xs.append(0.0)
        goals.append((xs[0], xs[1], xs[2]))
    return goals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--goals', default=None,
                    help='目标点列表，形如 "x,y,yaw;x,y,yaw;..."')
    ap.add_argument('--outdir', default='verify_logs')
    args, _ = ap.parse_known_args()

    goals = parse_goals(args.goals) if args.goals else list(DEFAULT_GOALS)

    rclpy.init()
    nav = VerifyNav()
    logger = nav.get_logger()

    logger.info('等待 navigate_to_pose 服务器（最多 60s）...')
    if not nav.nav_to_pose_client.wait_for_server(timeout_sec=60.0):
        logger.error('找不到 navigate_to_pose，请先启动 nav2_localization.launch.py')
        nav.destroy_node()
        rclpy.shutdown()
        return 1

    stamp = time.strftime('%Y%m%d_%H%M%S')
    outdir = os.path.join(os.getcwd(), args.outdir, f'verify_{stamp}')
    os.makedirs(outdir, exist_ok=True)

    logger.info(f'开始验收：{len(goals)} 个目标点 -> {outdir}')
    run_t0 = time.monotonic()
    records = []

    for i, (gx, gy, gyaw) in enumerate(goals, 1):
        logger.info(f'[目标 {i}/{len(goals)}] ({gx}, {gy}, {gyaw:.2f})')
        nav.reset_leg()
        t0 = time.monotonic()
        nav.goToPose(nav.make_pose(gx, gy, gyaw))
        while not nav.isTaskComplete():
            rclpy.spin_once(nav, timeout_sec=0.05)
            fb = nav.getFeedback()
            if fb is not None and hasattr(fb, 'distance_remaining'):
                logger.info(f'  剩余 {fb.distance_remaining:.2f} m')
        result = nav.getResult()
        dur = time.monotonic() - t0
        # 到达瞬间测量（此时 goal_checker 刚判定成功，最能反映"到点精度"）
        dist_err, yaw_err_deg = nav.pose_error(gx, gy, gyaw)

        ok = result == TaskResult.SUCCEEDED
        collision = (nav.min_range < COLLISION_CLEARANCE)
        rec = {
            'index': i,
            'goal': [gx, gy, gyaw],
            'result': result.name if hasattr(result, 'name') else str(result),
            'success': bool(ok),
            'duration_s': round(dur, 2),
            'xy_error_m': None if dist_err is None else round(dist_err, 3),
            'yaw_error_deg': None if yaw_err_deg is None else round(yaw_err_deg, 2),
            'min_clearance_m': round(nav.min_range, 3) if math.isfinite(nav.min_range) else None,
            'collision': bool(collision),
        }
        records.append(rec)
        logger.info(f'  结果={rec["result"]} 用时={dur:.1f}s '
                    f'位置误差={rec["xy_error_m"]}m 最小余量={rec["min_clearance_m"]}m')

    elapsed = time.monotonic() - run_t0
    scan_hz = nav.scan_count / elapsed if elapsed > 0 else 0.0
    cmd_hz = nav.cmd_count / elapsed if elapsed > 0 else 0.0

    n = len(records)
    n_ok = sum(1 for r in records if r['success'])
    n_coll = sum(1 for r in records if r['collision'])
    within_xy = sum(1 for r in records if r['xy_error_m'] is not None
                    and r['xy_error_m'] <= GOAL_XY_TOL)
    within_yaw = sum(1 for r in records if r['yaw_error_deg'] is not None
                     and r['yaw_error_deg'] <= GOAL_YAW_TOL_DEG)
    within_t = sum(1 for r in records if r['duration_s'] <= GOAL_TIME_LIMIT)
    clrs = [r['min_clearance_m'] for r in records if r['min_clearance_m'] is not None]
    min_clr = min(clrs) if clrs else None

    with open(os.path.join(outdir, 'data.jsonl'), 'w') as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    lines = []
    lines.append('# Nav2 多目标导航自动验收报告（[实测]）\n')
    lines.append(f'- 生成时间：{time.strftime("%Y-%m-%d %H:%M:%S")}（仿真时间需一致）')
    lines.append(f'- 目标点：{n} 个，到达成功：{n_ok}/{n}')
    lines.append(f'- 碰撞/贴障（余量 < {COLLISION_CLEARANCE} m）：{n_coll} 次')
    lines.append(f'- 到点位置误差 ≤ {GOAL_XY_TOL} m：{within_xy}/{n}')
    lines.append(f'- 到点朝向误差 ≤ {GOAL_YAW_TOL_DEG}°：{within_yaw}/{n}')
    lines.append(f'- 单点耗时 ≤ {GOAL_TIME_LIMIT} s：{within_t}/{n}')
    lines.append(f'- 全程最小激光余量：{min_clr} m')
    lines.append(f'- 总耗时：{elapsed:.1f} s')
    lines.append(f'- 实测话题频率：/scan = {scan_hz:.2f} Hz，/cmd_vel = {cmd_hz:.2f} Hz')
    lines.append('')
    lines.append('| # | 目标 (x,y,yaw) | 结果 | 耗时(s) | 位置误差(m) | 朝向误差(°) | 最小余量(m) | 碰撞 |')
    lines.append('| - | - | - | - | - | - | - | - |')
    for r in records:
        g = r['goal']
        lines.append(f"| {r['index']} | ({g[0]}, {g[1]}, {g[2]:.2f}) | {r['result']} | "
                     f"{r['duration_s']} | {r['xy_error_m']} | {r['yaw_error_deg']} | "
                     f"{r['min_clearance_m']} | {'是' if r['collision'] else '否'} |")
    lines.append('')
    lines.append('> 数据来源：本脚本对 `/scan`、`/cmd_vel`、`/amcl_pose` 的在线采样，'
                 '逐条与终端日志一致；所有数字均为 [实测]。')

    summary_path = os.path.join(outdir, 'summary.md')
    with open(summary_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    logger.info('=' * 56)
    logger.info(f'验收完成：{n_ok}/{n} 到达，{n_coll} 次贴障，最小余量 {min_clr} m')
    logger.info(f'/scan {scan_hz:.2f} Hz，/cmd_vel {cmd_hz:.2f} Hz，总耗时 {elapsed:.1f} s')
    logger.info(f'报告：{summary_path}')
    logger.info('=' * 56)

    nav.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
