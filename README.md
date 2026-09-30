> **仓库结构**：本仓库是一个 ROS2 工作空间，功能包源码位于 `src/ros2_robot_course/`。
> 克隆后在工作空间根目录执行 `colcon build --symlink-install` 即可编译。

# ros2_robot_course —— ROS2 Humble + Gazebo 室内机器人 SLAM 建图 + AMCL + Nav2 自主导航

> 一套可直接复现的差速移动机器人仿真工程：
> **自建室内场景 → XACRO 机器人 → slam_toolbox 建图 → 地图保存 → 重启后 AMCL 定位 → Nav2 多目标自主导航避障**。
> 全部逻辑运行于 Gazebo 11 仿真，无任何真实硬件；节点均为 ROS2 官方 C++ 包 + 自写 Python launch / YAML 配置。

---

## 一、环境说明

| 项目 | 版本 / 说明 |
| --- | --- |
| 操作系统 | Ubuntu 22.04 LTS 64-bit |
| ROS | ROS2 Humble（环境变量已配置，新终端自动 source） |
| 仿真器 | Gazebo 11.10.2（gazebo_ros_pkgs） |
| 建图 | slam_toolbox 2.6.x（在线异步） |
| 导航 | Navigation2（nav2_bringup 1.1.x） |
| 遥控 | teleop_twist_keyboard |
| 可视化 | RViz2 |

依赖包（本机已预装，无需再安装；此处仅列出以便换机复现）：

```bash
# 仅列出，本机已全部安装，不需要执行
sudo apt install ros-humble-gazebo-ros-pkgs ros-humble-xacro \
     ros-humble-robot-state-publisher ros-humble-joint-state-publisher \
     ros-humble-slam-toolbox ros-humble-navigation2 ros-humble-nav2-bringup \
     ros-humble-teleop-twist-keyboard ros-humble-rviz2
```

> **说明 1（xacro 可选）**：`robot_gazebo.launch.py` 会自动优先用 `xacro` 解析 `urdf/robot.urdf.xacro`；
> 若运行环境未安装 xacro，则自动回退加载展开好的 `urdf/robot.urdf`，不影响启动。
> **说明 2（多机/实验室网络隔离）**：若同一网段有其他人也在跑 ROS2 Nav2，会出现同名节点/服务冲突，
> 表现为生命周期管理器一直 `Waiting for service .../get_state`。请先执行
> `export ROS_DOMAIN_ID=77 && export ROS_LOCALHOST_ONLY=1` 再启动本工程。

---

## 二、工程目录结构

```
ros2_ws/
└── src/
    └── ros2_robot_course/
        ├── package.xml
        ├── setup.py
        ├── setup.cfg
        ├── README.md                         # 本文档
        ├── resource/
        │   └── ros2_robot_course
        └── ros2_robot_course/
            ├── __init__.py
            ├── send_goal.py                  # 命令行一键发导航目标点（免 RViz 鼠标）
            ├── world/
            │   ├── room.world                # 华丽宫殿大厅场景（高柱廊/浮雕/喷泉/彩窗，顶部开放）
            │   └── generate_palace.py        # 宫殿场景生成脚本（可重新生成 room.world）
            ├── urdf/
            │   ├── robot.urdf.xacro          # 差速两轮机器人（源文件，优先使用）
            │   └── robot.urdf                # xacro 展开后的等价 URDF（回退用）
            ├── launch/
            │   ├── robot_gazebo.launch.py    # 任务1：Gazebo + 机器人 + TF
            │   ├── slam.launch.py            # 任务2：SLAM 建图 + RViz
            │   └── nav2_localization.launch.py # 任务3/4：地图 + AMCL + Nav2 + RViz
            ├── config/
            │   ├── slam_toolbox.yaml         # slam_toolbox 参数
            │   ├── nav2_params.yaml          # Nav2 全套参数（AMCL/代价地图/规划/控制）
            │   ├── robot.rviz                # 任务1 可视化
            │   ├── slam.rviz                 # 任务2 建图可视化
            │   └── nav2.rviz                 # 任务3/4 导航可视化
            └── maps/
                ├── map.yaml                  # 参考地图（现场建图后会覆盖）
                ├── map.pgm
                └── generate_reference_map.py # 参考地图生成脚本（可选）
```

---


**本工程编写**：
- 宫殿大厅仿真场景 `world/room.world`（18m×12m 大厅、两侧各 4 根大理石高柱、墙面浮雕与壁柱、金色檐口、中央喷泉雕像、拱形彩窗与多盏暖色点光源，**顶部开放无天花板**）；
- 机器人前置科幻摄像头（深紫色金属外壳 + 半透明紫蓝渐变玻璃镜头 + 紫色发光环形灯带 + 细密机械结构，水平 180° 超广角，`libgazebo_ros_camera`），居中安装、前万向轮配平；
- 机器人模型 `urdf/robot.urdf.xacro`（差速两轮 + 万向从动轮 + 二维激光雷达 + 插件与 TF）；
- 全部 launch 文件（`robot_gazebo / slam / nav2_localization.launch.py`，Python 格式）；
- 全部 YAML 配置（`slam_toolbox.yaml`、`nav2_params.yaml`，含代价地图、规划器、控制器、AMCL 调参）；
- 三套 RViz 可视化配置与参考地图生成脚本。

---

## 三、关键参数调优说明

- **AMCL**：`max/min_particles = 2000/500`，`laser_model_type = likelihood_field`，
  `update_min_d/a` 控制更新频率；预置与出生点一致的初始位姿，保证 Nav2 生命周期可自动激活。
- **代价地图**：机器人按包围圆半径 `robot_radius = 0.25 m`；
  膨胀半径 `inflation_radius = 0.45 m`、`cost_scaling_factor = 3.0`，防止贴墙、撞墙。
- **全局规划器**：`NavfnPlanner`，`tolerance = 0.20`，`allow_unknown = true`。
- **局部控制器**：`DWBLocalPlanner`，`max_vel_x = 0.30 m/s`、`max_vel_theta = 1.0 rad/s`，
  critics 含 `BaseObstacle / PathDist / GoalDist / RotateToGoal`，兼顾平顺与避障。
- **到点判定**：`xy_goal_tolerance = 0.15 m`、`yaw_goal_tolerance = 0.15 rad`（验收 0.25 m / 15° 以内，留余量）。
- **速度平滑**：最终 `/cmd_vel` 经 `velocity_smoother` 限幅到 `0.30 m/s / 1.0 rad/s`，避免急停急转。
- **前置摄像头**：`horizontal_fov = 3.1415 rad`（≈180° 超广角）、640×480 @30Hz、`frame_name = camera_optical_frame`；
  镜头环形灯带用 `Gazebo/PurpleGlow` 自发光材质、镜片用 `Gazebo/DarkMagentaTransparent` 半透明材质配合 `Gazebo/BlueGlow` 内芯，实现紫蓝渐变与镜头边缘紫色光晕。

---


### 运行证据截图清单（每次演示各截一张）

1. **仿真启动**：Gazebo 宫殿场景 + RViz（RobotModel / LaserScan / TF）同框；
2. **地图生成**：`slam.launch.py` 建图过程/结果 + 终端出现 `Map saved successfully`；
3. **地图加载与定位**：`nav2_localization.launch.py` 下 RViz 中地图 + 激光点与墙体边界重合 + 绿色粒子云；
4. **路径规划**：发送目标点后 RViz 显示红色全局路径 `/plan`、蓝色局部路径 `/local_plan` 与代价地图；
5. **目标完成**：终端 `send_goal` 打印 `✅ 已到达目标点！`（或 RViz 面板 `Feedback: reached`）。

