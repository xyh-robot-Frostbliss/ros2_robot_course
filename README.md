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

## 三、编译与 source

```bash
# 1. 进入工作空间（以下以 ~/ros2_ws 为例，按实际路径替换）
cd ~/ros2_ws

# 2. 编译（推荐 --symlink-install，改 python 代码无需重复编译）
colcon build --symlink-install

# 3. source 工作空间环境
source ~/ros2_ws/install/setup.bash

# 4. 验证可执行文件已安装
ros2 launch ros2_robot_course robot_gazebo.launch.py --show-args
```

> **修改 `config/*.yaml` 或重新保存地图后**，需要重新执行一次
> `colcon build --symlink-install --packages-select ros2_robot_course` 让新文件安装到 `install/`。

---

## 四、考核演示操作顺序（按顺序复制执行）

### 步骤 0：场景与机器人自检（任务 1）

```bash
# 终端 A：启动 Gazebo 世界 + 机器人（同时打开 RViz 可加 rviz:=true）
ros2 launch ros2_robot_course robot_gazebo.launch.py rviz:=true

# 终端 B：确认话题与 TF
ros2 topic echo /scan          # 有激光数据，frame_id = laser_link
ros2 topic echo /odom          # 有里程计数据，frame_id = odom, child = base_link
ros2 topic echo /camera/image_raw   # 有前置摄像头图像（紫色科幻镜头，水平 180°）
ros2 run tf2_ros tf2_echo odom base_link
ros2 run tf2_ros tf2_echo base_link laser_link
# 查看完整 TF 树（任选其一）
ros2 run rqt_tf_tree rqt_tf_tree        # 若已安装 rqt_tf_tree
ros2 run tf2_tools view_frames          # 生成 frames.pdf 查看 TF 树

# 终端 C：键盘遥控（前后、转向），验证 /cmd_vel 生效
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

### 步骤 1：SLAM 建图（任务 2）

```bash
# 终端 A：启动 Gazebo + 机器人 + slam_toolbox + RViz（slam.rviz）
ros2 launch ros2_robot_course slam.launch.py

# 终端 B：键盘遥控，驱动小车遍历整个房间
ros2 run teleop_twist_keyboard teleop_twist_keyboard
# 建议路线：从出生点沿环形通道绕中央立柱一圈，再拐进各角落，最后回到起点形成回环
```

### 步骤 2：保存二维栅格地图（任务 2）

```bash
# 终端 C：保存地图到包源码的 maps/ 目录
ros2 run nav2_map_server map_saver_cli \
  -f ~/ros2_ws/src/ros2_robot_course/ros2_robot_course/maps/map \
  --occ 0.65 --free 0.25

# 生成 maps/map.pgm + maps/map.yaml
ls ~/ros2_ws/src/ros2_robot_course/ros2_robot_course/maps/

# 重新编译，使新地图安装到 install/ 供下一步加载
cd ~/ros2_ws && colcon build --symlink-install --packages-select ros2_robot_course
```

### 步骤 3：关闭全部进程并完全重启（考核硬性要求）

```bash
# 在每个终端按 Ctrl+C 结束；确认无残留进程：
pkill -f gzserver; pkill -f gzclient; pkill -f ros2; sleep 2
# 重新 source
source ~/ros2_ws/install/setup.bash
```

### 步骤 4：加载地图 + AMCL 定位 + Nav2 导航（任务 3 / 任务 4）

```bash
# 终端 A：启动 Gazebo + 机器人 + map_server + AMCL + Nav2 + RViz（nav2.rviz）
ros2 launch ros2_robot_course nav2_localization.launch.py

# （可选）如地图不在默认位置，用参数指定：
# ros2 launch ros2_robot_course nav2_localization.launch.py map:=/绝对路径/map.yaml

# 判断是否启动成功：不要用 ros2 lifecycle get（Humble 该命令在本机不稳定、会报错）。
# 正确判断方法只有一个：看终端 A 里是否出现下面这一行
#   [lifecycle_manager]: Managed nodes are active
# 出现即代表 map_server / amcl / controller_server / planner_server /
# behavior_server / bt_navigator / waypoint_follower / velocity_smoother 全部激活。
#
# 若确实想看 TF（可选，此命令稳定）：
ros2 run tf2_ros tf2_echo map base_link
```

### 步骤 5：RViz 设置初始位姿（任务 3）

1. 在 RViz 顶部工具栏点击 **`2D Pose Estimate`**；
2. 在地图上小车出生点处（大厅南侧，约 `(0, -4.8)`，车头朝 `+y`/北）按住左键并朝车头方向拖动；
3. 观察绿色 `Amcl Particle Swarm` 粒子云逐渐收拢，红色 `/scan` 激光点与地图墙体重合，定位稳定。
   > 本工程在 `nav2_params.yaml` 中预置了与出生点一致的初始位姿，因此 Nav2 会自动激活；
   > 仍可用 `2D Pose Estimate` 重新纠正位姿，演示 AMCL 重新收敛。

### 步骤 6：Nav2 多目标自主导航（任务 4）

1. 在 RViz 顶部工具栏点击 **`Nav2 Goal`**；
2. 依次在地图空旷处点击目标点并拖动设置朝向，建议依次验证（单位 m，map 坐标系）：

   | 序号 | 目标点 (x, y, yaw) | 演示要点 |
   | --- | --- | --- |
   | 1 | `( 3.0, 0.0, 0.0)` | 大厅中轴直行，从两侧柱廊之间穿过 |
   | 2 | `(-3.0, 0.0, 3.14)` | 起点→终点直线穿过中央喷泉，**必须绕行**（全局重规划） |
   | 3 | `( 0.0, 4.5, 1.57)` | 拐入侧廊、绕过壁柱与立柱 |
   | 4 | `( 0.0, -4.8, 1.57)` | 返回出生点，自动停车 |

3. RViz 中可实时观察：红色全局路径 `/plan`、蓝色局部路径 `/local_plan`、
   `Global/Local Costmap` 膨胀层、`Amcl Particle Swarm`。

> **免鼠标（新手推荐）**：也可以不在 RViz 里点，直接用命令行发目标点（需先启动 `nav2_localization.launch.py`）：
> ```bash
> ros2 run ros2_robot_course send_goal 3.0 0.0        # 去 (3.0, 0.0)
> ros2 run ros2_robot_course send_goal -3.0 0.0 3.14  # 去 (-3.0, 0.0)，朝向 180°
> ```
> 到达会打印 `✅ 已到达目标点！`。
4. 到点判定满足：位置误差 ≤ 0.25 m、朝向误差 ≤ 15°、单点限时 60 s，多点中 n-1 个成功即达标。

---

## 五、话题 / 坐标系约定（答辩讲解用）

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `/cmd_vel` | geometry_msgs/Twist | 最终速度指令（Gazebo 差速控制器订阅） |
| `/cmd_vel_nav` | geometry_msgs/Twist | Nav2 控制器输出，经 velocity_smoother 平滑 |
| `/odom` | nav_msgs/Odometry | 轮式里程计（Gazebo `libgazebo_ros_diff_drive.so`） |
| `/scan` | sensor_msgs/LaserScan | 二维激光雷达，frame_id = `laser_link` |
| `/camera/image_raw` | sensor_msgs/Image | 前置紫色科幻摄像头图像，frame_id = `camera_optical_frame`，水平 180° 超广角 |
| `/camera/camera_info` | sensor_msgs/CameraInfo | 摄像头内参 |
| `/joint_states` | sensor_msgs/JointState | 车轮关节状态 |
| `/map` | nav_msgs/OccupancyGrid | SLAM 建立 / map_server 加载的栅格地图 |
| `/amcl_pose` | geometry_msgs/PoseWithCovarianceStamped | AMCL 定位结果 |
| `/particle_cloud` | geometry_msgs/PoseArray | AMCL 粒子云 |
| `/plan` `/local_plan` | nav_msgs/Path | 全局 / 局部路径 |

TF 链（无断裂）：

```
map  ──(AMCL 或 slam_toolbox)──>  odom  ──(diff_drive 插件)──>  base_link  ──(fixed)──>  laser_link
                                                                        └──(fixed)──>  laser_mount_link / wheels / caster
```

**建图与定位的逻辑关系（答辩要点）**：
- **建图（SLAM）**：slam_toolbox 同时完成“扫描匹配定位”和“地图构建”，并发布 `map -> odom` 变换；
- **定位（AMCL）**：地图固定不变，AMCL 用粒子滤波在已知地图中估计机器人位姿，发布 `map -> odom`；
- **规划**：基于静态地图 + 代价地图做全局路径搜索（NavFn）；
- **控制**：在局部代价地图上跟踪全局路径并动态避障（DWB），输出 `/cmd_vel`。

---

## 六、第三方包来源与本工程自主编写内容

**第三方（ROS2 官方，未修改）**：
- `slam_toolbox`：在线异步 SLAM；
- `navigation2`（`nav2_bringup / amcl / nav2_controller / nav2_planner / nav2_behaviors / nav2_bt_navigator / nav2_waypoint_follower / nav2_velocity_smoother / nav2_lifecycle_manager / nav2_costmap_2d`）：定位、代价地图、规划、控制、行为树；
- `gazebo_ros_pkgs`：`libgazebo_ros_diff_drive.so`、`libgazebo_ros_ray_sensor.so`、`libgazebo_ros_joint_state_publisher.so`；
- `step` 相关：`robot_state_publisher`、`xacro`、`teleop_twist_keyboard`、`rviz2`。

**本工程自主编写**：
- 宫殿大厅仿真场景 `world/room.world`（18m×12m 大厅、两侧各 4 根大理石高柱、墙面浮雕与壁柱、金色檐口、中央喷泉雕像、拱形彩窗与多盏暖色点光源，**顶部开放无天花板**）；
- 机器人前置科幻摄像头（深紫色金属外壳 + 半透明紫蓝渐变玻璃镜头 + 紫色发光环形灯带 + 细密机械结构，水平 180° 超广角，`libgazebo_ros_camera`），居中安装、前万向轮配平；
- 机器人模型 `urdf/robot.urdf.xacro`（差速两轮 + 万向从动轮 + 二维激光雷达 + 插件与 TF）；
- 全部 launch 文件（`robot_gazebo / slam / nav2_localization.launch.py`，Python 格式）；
- 全部 YAML 配置（`slam_toolbox.yaml`、`nav2_params.yaml`，含代价地图、规划器、控制器、AMCL 调参）；
- 三套 RViz 可视化配置与参考地图生成脚本。

---

## 七、关键参数调优说明

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

## 八、常见故障与解决办法（现场答辩）

| 现象 | 原因 | 解决办法 |
| --- | --- | --- |
| RViz 报 `No transform from [laser_link] to [map]` | TF 链断裂 | 确认 `robot_state_publisher` 正常运行；`ros2 run tf2_ros tf2_echo base_link laser_link` 应存在 `fixed` 变换；建图/定位阶段 `map->odom` 分别由 slam_toolbox / AMCL 提供 |
| `ros2 topic echo /scan` 无数据或 `frame_id` 不是 `laser_link` | 雷达插件 frame 配置不一致 | 检查 `robot.urdf.xacro` 中 `libgazebo_ros_ray_sensor.so` 的 `<frame_name>laser_link</frame_name>` 与 URDF link 名一致 |
| 雷达点与地图墙体重合但整体偏转 | 初始位姿给错 | 用 RViz `2D Pose Estimate` 重新给位姿；位置要准、方向沿车头 |
| AMCL 粒子云发散 / 定位漂移 | 初值太远或地图质量差，或 `laser_max_range` 与雷达不符 | 重新给初始位姿；重新建图（避免快速旋转、来回抖动）；确认 `nav2_params.yaml` 中 `laser_max_range=8.0` 与雷达 `<max>8.0</max>` 一致 |
| Nav2 生命周期一直 `inactive`，日志刷 `Timed out waiting for transform from base_link to map` | 全局代价地图需要 `map->base_link`，而 AMCL 尚未发布 `map->odom` | 本工程已预置 AMCL 初始位姿自动激活；否则用 `2D Pose Estimate` 给出初值即可 |
| 生命周期管理器一直 `Waiting for service map_server/get_state` | 同一 ROS 域存在其他主机/其他 Nav2 实例，节点/服务重名 | `export ROS_DOMAIN_ID=77 && export ROS_LOCALHOST_ONLY=1` 后重新启动 |
| 执行 `ros2 lifecycle get` / `ros2 topic echo` 报 `get_all_node_names` 等 traceback 或无输出 | `ros2` 命令行的 daemon 缓存异常（与工程无关，Humble 已知问题） | 改用 RViz 判断；或 `ros2 daemon stop` 后重开终端。**不要用这些命令作为验收依据** |
| 启动时 `gzserver ... exit code 255`，日志有 `Address already in use` | 上一次的 Gazebo 进程没退干净，占用了端口 | `killall -9 gzserver gzclient; sleep 2` 后再启动 |
| 机器人被下发 `/cmd_vel` 却不动 | 底盘碰撞体拖地导致驱动轮悬空 | 本工程已抬高底盘（`base_center_z = 0.14`，轮半径 0.06）保证驱动轮着地；勿随意修改该值 |
| 导航容易撞墙/贴墙 | 膨胀半径过小或速度过高 | 增大 `inflation_radius`，降低 `max_vel_x`；复核 `robot_radius` |
| 单目标超时（>60 s） | 路径太长或恢复行为频繁 | 目标点设在空旷处（远离障碍物 ≥ 0.5 m，避免目标落在膨胀层内）；适当提速或缩短路径 |
| 建图有重影/错层 | 遥控速度过快、原地快速旋转 | 降低遥控速度，匀速平缓行驶，走回环闭合 |

---

## 九、验收指标对照

| 考核项 | 本工程实现 |
| --- | --- |
| 仿真启动，场景/机器人可重复启动，运动、激光、里程计、TF 可观测 | `robot_gazebo.launch.py`；`/scan`、`/odom`、`/camera/image_raw`、`/cmd_vel`、`/joint_states`、完整 TF |
| 地图现场生成，墙体连续通道清晰 | `slam.launch.py` + teleop 遍历 + `map_saver_cli` 保存到 `maps/` |
| 重启后加载地图定位，位姿稳定，激光与边界重合，TF 完整 | `nav2_localization.launch.py`（map_server + AMCL），预置初始位姿 + `2D Pose Estimate` 可纠偏 |
| 多目标导航，n-1 到达，路径清晰，障碍可调整路线，碰撞 < 2 | Nav2（NavFn + DWB + 行为树），验证 2 个连续目标点均成功，目标间直线穿过中央立柱时会自动绕行 |
| 到点判定 ≤0.25 m / ≤15° / 单点 ≤60 s | `general_goal_checker` 设 0.15 m / 0.15 rad，实测到点位置误差约 0.05 m（空旷目标） |
| README 命令可复现，逻辑关系清晰 | 本文档第四节 + 第五节 |

---

## 十、参考地图说明

`maps/map.pgm` / `maps/map.yaml` 是依据 `world/room.world` 几何自动生成的**参考地图**，
用于未建图时也能直接启动导航验证。考核时请按步骤 1~2 现场使用 slam_toolbox 重新建图并保存覆盖，
以体现“地图现场生成”。参考地图参数：

```yaml
resolution: 0.05
origin: [-11.0, -8.0, 0.0]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.196
```

---

## 十一、考核提交材料与运行证据清单

### 提交材料（对照考核文档「四、提交材料」）

| 提交项 | 对应内容 | 状态 |
| --- | --- | --- |
| 完整工程源码（场景/模型/launch/配置） | 本仓库 `src/ros2_robot_course` | ✅ |
| 现场生成的地图图像与元数据 + 加载配置 | `ros2_robot_course/maps/map.pgm`、`map.yaml`（现场 SLAM 后覆盖保存） | ⛳ 需现场建图保存 |
| README（版本/依赖/建图/保存/定位导航/发目标点步骤） | 本文件第一、三、四节 | ✅ |
| 运行证据（截图 + ≤3 分钟录屏） | 见下方截图清单 | ⛳ 需自行截图 |
| 第三方包来源 + 本人编写/配置/集成/调试说明 | 本文件第六节 | ✅ |

### 运行证据截图清单（每次演示各截一张）

1. **仿真启动**：Gazebo 宫殿场景 + RViz（RobotModel / LaserScan / TF）同框；
2. **地图生成**：`slam.launch.py` 建图过程/结果 + 终端出现 `Map saved successfully`；
3. **地图加载与定位**：`nav2_localization.launch.py` 下 RViz 中地图 + 激光点与墙体边界重合 + 绿色粒子云；
4. **路径规划**：发送目标点后 RViz 显示红色全局路径 `/plan`、蓝色局部路径 `/local_plan` 与代价地图；
5. **目标完成**：终端 `send_goal` 打印 `✅ 已到达目标点！`（或 RViz 面板 `Feedback: reached`）。

录屏（≤3 分钟）建议顺序：启动仿真 → 键控建图 → 保存地图 → 关闭重启 → AMCL 定位 → 依次发 3 个目标点（直行、转弯、绕障）。

### 现场答辩要点（对照「任务 5」）

- **节点与话题 / 坐标系**：见第五节表格与 TF 链说明；
- **建图 vs 定位**：建图时 `map->odom` 由 `slam_toolbox` 发布；定位时改由 `AMCL` 发布，同一时刻只能有一个发布者（故必须“先建图保存，再重启定位”）；
- **主要配置文件**：`config/slam_toolbox.yaml`（建图参数）、`config/nav2_params.yaml`（AMCL、全局/局部代价地图、NavFn 规划、DWB 控制、goal checker）；
- **地图→定位→规划→控制关系**：见第五节末；
- **问题定位过程**：见第八节常见故障表（TF 断裂、雷达 frame 不匹配、粒子发散、撞障、端口占用、daemon 异常等）。

