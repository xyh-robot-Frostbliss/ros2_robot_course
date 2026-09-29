#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_palace.py  ——  生成华丽宫殿大厅仿真世界 room.world

场景要素：
  * 18m x 12m 大厅，6m 高墙、雕花墙面（浮雕带 + 壁柱 + 金色檐口）
  * 两侧各 4 根大理石高柱构成的柱廊（同时作为导航障碍物），顶部开放无天花板
  * 中央圆形喷泉 + 雕像（中央障碍物）
  * 方格大理石地砖 + 红毯 + 金边镶嵌
  * 拱形彩窗（自发光）+ 多盏暖色点光源

碰撞体只保留：四壁、柱廊、喷泉基座、壁柱（供激光/SLAM/导航使用）；
拱窗、浮雕、地砖均为纯视觉装饰，不参与物理，保证性能。
"""
import os

# ---------------- 几何常量（地图生成脚本需保持一致） ----------------
HALL_X = 9.0          # 内部半长（x 方向）
HALL_Y = 6.0          # 内部半宽（y 方向）
WALL_T = 0.6          # 墙厚
WALL_H = 8.0          # 墙高
COL_R = 0.45          # 柱半径（视觉）
COL_COLL_R = 0.55     # 柱碰撞半径
COL_XS = [-6.0, -2.0, 2.0, 6.0]
COL_YS = [-3.0, 3.0]
FOUNTAIN_R = 1.4      # 喷泉基座碰撞半径
PILASTER_R = 0.40
PIL_XS = [-7.5, -4.5, -1.5, 1.5, 4.5, 7.5]
PIL_YS = [-4.5, 0.0, 4.5]

# ---------------- 材质 ----------------
IVORY = """<material>
        <ambient>0.42 0.40 0.36 1</ambient>
        <diffuse>0.88 0.85 0.78 1</diffuse>
        <specular>0.65 0.63 0.58 1</specular>
        <emissive>0.02 0.02 0.02 1</emissive>
      </material>"""
MARBLE_DARK = """<material>
        <ambient>0.12 0.09 0.16 1</ambient>
        <diffuse>0.26 0.20 0.34 1</diffuse>
        <specular>0.85 0.80 0.95 1</specular>
        <emissive>0.01 0.01 0.02 1</emissive>
      </material>"""
GOLD = """<material>
        <ambient>0.38 0.28 0.07 1</ambient>
        <diffuse>0.92 0.72 0.24 1</diffuse>
        <specular>1.0 0.95 0.6 1</specular>
        <emissive>0.10 0.07 0.01 1</emissive>
      </material>"""
ROSE = """<material>
        <ambient>0.30 0.08 0.09 1</ambient>
        <diffuse>0.70 0.16 0.18 1</diffuse>
        <specular>0.5 0.3 0.3 1</specular>
        <emissive>0.03 0.0 0.0 1</emissive>
      </material>"""
WALL_MAT = """<material>
        <ambient>0.45 0.42 0.38 1</ambient>
        <diffuse>0.90 0.87 0.80 1</diffuse>
        <specular>0.30 0.30 0.28 1</specular>
        <emissive>0.02 0.02 0.02 1</emissive>
      </material>"""
STAINED = """<material>
        <ambient>0.10 0.18 0.45 1</ambient>
        <diffuse>0.25 0.45 0.95 1</diffuse>
        <specular>0.9 0.9 1.0 1</specular>
        <emissive>0.18 0.28 0.55 1</emissive>
      </material>"""
STAINED_GOLD = """<material>
        <ambient>0.45 0.35 0.10 1</ambient>
        <diffuse>1.0 0.85 0.45 1</diffuse>
        <specular>1.0 1.0 0.8 1</specular>
        <emissive>0.45 0.35 0.12 1</emissive>
      </material>"""
WATER = """<material>
        <ambient>0.05 0.15 0.30 1</ambient>
        <diffuse>0.15 0.45 0.75 1</diffuse>
        <specular>1.0 1.0 1.0 1</specular>
        <emissive>0.03 0.10 0.18 1</emissive>
      </material>"""
BULB = """<material>
        <ambient>0.9 0.8 0.5 1</ambient>
        <diffuse>1.0 0.95 0.75 1</diffuse>
        <specular>1.0 1.0 0.9 1</specular>
        <emissive>0.85 0.75 0.45 1</emissive>
      </material>"""

parts = []


def add_model(name, pose, links_xml):
    parts.append(f"""
    <model name="{name}">
      <static>true</static>
      <pose>{pose}</pose>
{links_xml}
    </model>""")


def static_link(visuals="", collisions=""):
    return f"""      <link name="link">
{collisions}{visuals}      </link>"""


def vis(name, geometry, material, pose="0 0 0 0 0 0", transparency=None):
    t = f"\n          <transparency>{transparency}</transparency>" if transparency else ""
    return f"""        <visual name="{name}">
          <pose>{pose}</pose>
          <geometry>{geometry}</geometry>
          {material}{t}
        </visual>
"""


def col(name, geometry, pose="0 0 0 0 0 0"):
    return f"""        <collision name="{name}">
          <pose>{pose}</pose>
          <geometry>{geometry}</geometry>
        </collision>
"""


def box(sx, sy, sz):
    return f"<box><size>{sx} {sy} {sz}</size></box>"


def cyl(r, l):
    return f"<cylinder><radius>{r}</radius><length>{l}</length></cylinder>"


def sph(r):
    return f"<sphere><radius>{r}</radius></sphere>"


# ==================== 地面（方格大理石 + 红毯 + 金边） ====================
floor_visuals = []
tile = 2.0
i = 0
for cx in [-8, -6, -4, -2, 0, 2, 4, 6, 8]:
    for cy in [-5, -3, -1, 1, 3, 5]:
        m = IVORY if (i % 2 == 0) else MARBLE_DARK
        floor_visuals.append(vis(f"tile_{i}", box(tile, tile, 0.02), m,
                                 f"{cx} {cy} 0.01"))
        i += 1
floor_visuals.append(vis("carpet", box(12.0, 2.4, 0.03), ROSE, "0 0 0.03"))
floor_visuals.append(vis("carpet_gold_a", box(12.4, 0.10, 0.035), GOLD, "0 1.25 0.03"))
floor_visuals.append(vis("carpet_gold_b", box(12.4, 0.10, 0.035), GOLD, "0 -1.25 0.03"))
floor_visuals.append(vis("inlay_gold_ring", cyl(4.2, 0.02), GOLD, "0 0 0.03"))
floor_visuals.append(vis("inlay_gold_ring2", cyl(4.35, 0.02), GOLD, "0 0 0.03"))
add_model("palace_floor", "0 0 0 0 0 0", static_link(visuals="".join(floor_visuals)))

# ==================== 四壁（含金色檐口与墙面分割线） ====================
wall_parts = []
wall_defs = [
    ("north", f"0 {HALL_Y + WALL_T / 2} {WALL_H / 2} 0 0 0", f"{2 * (HALL_X + WALL_T)} {WALL_T} {WALL_H}"),
    ("south", f"0 {-HALL_Y - WALL_T / 2} {WALL_H / 2} 0 0 0", f"{2 * (HALL_X + WALL_T)} {WALL_T} {WALL_H}"),
    ("east", f"{HALL_X + WALL_T / 2} 0 {WALL_H / 2} 0 0 0", f"{WALL_T} {2 * (HALL_Y + WALL_T)} {WALL_H}"),
    ("west", f"{-HALL_X - WALL_T / 2} 0 {WALL_H / 2} 0 0 0", f"{WALL_T} {2 * (HALL_Y + WALL_T)} {WALL_H}"),
]
# 每面墙单独一个 model（带碰撞），檐口作为其视觉子项
for nm, pose, size in wall_defs:
    cx, cy, cz, _, _, _ = [float(v) for v in pose.split()]
    sx, sy, sz = [float(v) for v in size.split()]
    v = vis("wall", box(sx, sy, sz), WALL_MAT)
    # 金色檐口（位于墙体内侧、顶部）
    if nm in ("north", "south"):
        y_face = HALL_Y - 0.02 if nm == "north" else -HALL_Y + 0.02
        v += vis("cornice", box(sx, 0.22, 0.5), GOLD, f"0 {y_face - cy} 5.6")
    else:
        x_face = HALL_X - 0.02 if nm == "east" else -HALL_X + 0.02
        v += vis("cornice", box(0.22, sy, 0.5), GOLD, f"{x_face - cx} 0 5.6")
    add_model(f"wall_{nm}", pose, static_link(visuals=v,
              collisions=col("collision", box(sx, sy, sz))))

# ==================== 墙面浮雕带（金色/象牙交替玫瑰花饰） ====================
relief_vis = []
# 南北墙
for x in [round(-8.5 + 1.0 * k, 2) for k in range(18)]:
    for (wall_y, tag) in [(HALL_Y - 0.06, "n"), (-HALL_Y + 0.06, "s")]:
        m = GOLD if int(x * 10) % 20 == 0 else IVORY
        relief_vis.append(vis(f"r_{tag}_{x}", box(0.55, 0.14, 0.55), m, f"{x} {wall_y} 2.6"))
# 东西墙
for y in [round(-5.5 + 1.0 * k, 2) for k in range(12)]:
    for (wall_x, tag) in [(HALL_X - 0.06, "e"), (-HALL_X + 0.06, "w")]:
        m = GOLD if int(y * 10) % 20 == 0 else IVORY
        relief_vis.append(vis(f"r_{tag}_{y}", box(0.14, 0.55, 0.55), m, f"{wall_x} {y} 2.6"))
add_model("wall_reliefs", "0 0 0 0 0 0", static_link(visuals="".join(relief_vis)))

# ==================== 壁柱（半嵌墙柱，带碰撞） ====================
pil_vis = []
pil_col = []
for k, x in enumerate(PIL_XS):
    for (y, tag) in [(HALL_Y - PILASTER_R * 0.6, "n"), (-HALL_Y + PILASTER_R * 0.6, "s")]:
        pil_vis.append(vis(f"pil_{tag}_{k}", cyl(PILASTER_R, 6.6), IVORY, f"{x} {y} 3.3"))
        pil_vis.append(vis(f"pilbase_{tag}_{k}", box(1.05, 1.05, 0.35), GOLD, f"{x} {y} 0.18"))
        pil_vis.append(vis(f"pilcap_{tag}_{k}", box(0.95, 0.95, 0.35), GOLD, f"{x} {y} 6.8"))
        pil_col.append(col(f"c_{tag}_{k}", cyl(PILASTER_R, 6.6), f"{x} {y} 3.3"))
for k, y in enumerate(PIL_YS):
    for (x, tag) in [(HALL_X - PILASTER_R * 0.6, "e"), (-HALL_X + PILASTER_R * 0.6, "w")]:
        pil_vis.append(vis(f"pil_{tag}_{k}", cyl(PILASTER_R, 6.6), IVORY, f"{x} {y} 3.3"))
        pil_vis.append(vis(f"pilbase_{tag}_{k}", box(1.05, 1.05, 0.35), GOLD, f"{x} {y} 0.18"))
        pil_vis.append(vis(f"pilcap_{tag}_{k}", box(0.95, 0.95, 0.35), GOLD, f"{x} {y} 6.8"))
        pil_col.append(col(f"c_{tag}_{k}", cyl(PILASTER_R, 6.6), f"{x} {y} 3.3"))
add_model("pilasters", "0 0 0 0 0 0", static_link(visuals="".join(pil_vis),
                                                 collisions="".join(pil_col)))

# ==================== 柱廊（12 根高柱，带碰撞） ====================
col_links = []
for i, x in enumerate(COL_XS):
    for j, y in enumerate(COL_YS):
        cid = f"{i}_{j}"
        v = vis(f"shaft", cyl(COL_R, 6.6), IVORY, "0 0 3.3")
        v += vis(f"base1", box(1.10, 1.10, 0.35), GOLD, "0 0 0.18")
        v += vis(f"base2", cyl(0.55, 0.30), IVORY, "0 0 0.50")
        v += vis(f"cap1", cyl(0.55, 0.35), IVORY, "0 0 6.78")
        v += vis(f"cap2", box(1.05, 1.05, 0.35), GOLD, "0 0 7.13")
        c = col("collision", cyl(COL_COLL_R, 7.3), "0 0 3.65")
        col_links.append(f"""      <link name="col_{cid}">
        <pose>{x} {y} 0 0 0 0</pose>
{v}{c}      </link>
""")
add_model("colonnade", "0 0 0 0 0 0", "\n".join(col_links))

# ==================== 中央喷泉 + 雕像（中央障碍物，带碰撞） ====================
f_pose = f"0 0 0 0 0 0"
f_vis = vis("basin", cyl(FOUNTAIN_R, 0.6), IVORY, "0 0 0.3")
f_vis += vis("basin_rim", cyl(FOUNTAIN_R + 0.08, 0.14), GOLD, "0 0 0.62")
f_vis += vis("water", cyl(FOUNTAIN_R - 0.12, 0.02), WATER, "0 0 0.58", transparency=0.35)
f_vis += vis("pedestal", cyl(0.45, 1.6), IVORY, "0 0 1.4")
f_vis += vis("pedestal_gold", cyl(0.5, 0.12), GOLD, "0 0 2.2")
f_vis += vis("statue", cyl(0.28, 1.4), GOLD, "0 0 2.95")
f_vis += vis("statue_head", sph(0.24), GOLD, "0 0 3.8")
f_vis += vis("statue_arms", box(1.4, 0.18, 0.18), GOLD, "0 0 3.35")
f_col = col("collision", cyl(FOUNTAIN_R, 0.6), "0 0 0.3")
add_model("central_fountain", f_pose, static_link(visuals=f_vis, collisions=f_col))

# ==================== 拱形彩窗（自发光，纯视觉） ====================
win_vis = []
for x in [-6, -3, 0, 3, 6]:
    for (y, tag) in [(HALL_Y - 0.05, "n"), (-HALL_Y + 0.05, "s")]:
        win_vis.append(vis(f"win_{tag}_{x}", box(1.8, 0.10, 3.2), STAINED, f"{x} {y} 4.4", transparency=0.35))
        win_vis.append(vis(f"win_arch_{tag}_{x}", cyl(0.9, 0.10), STAINED_GOLD, f"{x} {y} 6.0", transparency=0.25))
        win_vis.append(vis(f"win_frame_{tag}_{x}", box(2.0, 0.06, 3.6), GOLD, f"{x} {y} 4.4"))
for y in [-2.5, 2.5]:
    for (x, tag) in [(HALL_X - 0.05, "e"), (-HALL_X + 0.05, "w")]:
        win_vis.append(vis(f"win_{tag}_{y}", box(0.10, 1.8, 3.2), STAINED, f"{x} {y} 4.4", transparency=0.35))
        win_vis.append(vis(f"win_frame_{tag}_{y}", box(0.06, 2.0, 3.6), GOLD, f"{x} {y} 4.4"))
add_model("stained_windows", "0 0 0 0 0 0", static_link(visuals="".join(win_vis)))

# ==================== 组装世界 ====================
head = """<?xml version="1.0" ?>
<!--
  room.world  ——  华丽宫殿大厅（Palace Hall）

  由 world/generate_palace.py 自动生成。场景包含：
    高柱廊、墙面浮雕、壁柱、金色檐口、方格大理石地面、红毯、
    中央喷泉雕像、拱形彩窗与多盏暖色点光源；顶部开放，无天花板。
  碰撞体仅保留四壁、柱廊、喷泉、壁柱，用于激光/SLAM/导航；
  其余为纯视觉装饰，保证仿真性能。
-->
<sdf version="1.6">
  <world name="palace_hall">

    <physics name="default_physics" default="true" type="ode">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1.0</real_time_factor>
      <real_time_update_rate>1000</real_time_update_rate>
    </physics>

    <scene>
      <ambient>0.60 0.58 0.62 1</ambient>
      <background>0.42 0.55 0.78 1</background>
      <shadows>true</shadows>
    </scene>

    <gui>
      <camera name="user_camera">
        <pose>-16 -14 12 0 0.75 0.85</pose>
      </camera>
    </gui>

    <include>
      <uri>model://sun</uri>
    </include>

    <include>
      <uri>model://ground_plane</uri>
    </include>
"""

lights = []
for ci, cx in enumerate([-5.0, 0.0, 5.0]):
    lights.append(f"""
    <light name="chandelier_light_{ci}" type="point">
      <pose>{cx} 0 7.6 0 0 0</pose>
      <cast_shadows>true</cast_shadows>
      <diffuse>1.0 0.86 0.60 1</diffuse>
      <specular>1.0 0.92 0.72 1</specular>
      <attenuation>
        <range>22</range><constant>0.45</constant><linear>0.04</linear><quadratic>0.006</quadratic>
      </attenuation>
    </light>""")
for ci, (lx, ly) in enumerate([(-8, -5), (8, -5), (-8, 5), (8, 5)]):
    lights.append(f"""
    <light name="corner_light_{ci}" type="point">
      <pose>{lx} {ly} 6.8 0 0 0</pose>
      <cast_shadows>true</cast_shadows>
      <diffuse>0.75 0.72 0.95 1</diffuse>
      <specular>0.8 0.8 1.0 1</specular>
      <attenuation>
        <range>18</range><constant>0.5</constant><linear>0.05</linear><quadratic>0.008</quadratic>
      </attenuation>
    </light>""")

world = head + "".join(lights) + "".join(parts) + "\n  </world>\n</sdf>\n"

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "room.world")
with open(out, "w") as f:
    f.write(world)
print(f"world written: {out} ({len(world)} bytes, {len(parts)} models)")
