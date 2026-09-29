#!/usr/bin/env python3
"""Generate a reference occupancy grid (P5 PGM + YAML) matching the palace world."""
import math
import os

RES = 0.05
ORIGIN_X = -11.0
ORIGIN_Y = -8.0
W = int(22.0 / RES)   # 440
H = int(16.0 / RES)   # 320

OCC, FREE, UNK = 0, 254, 205

# ---- geometry (must match world/generate_palace.py) ----
HALL_X, HALL_Y = 9.0, 6.0
WALL_T = 0.6
COL_R = 0.55
COL_XS = [-6.0, -2.0, 2.0, 6.0]
COL_YS = [-3.0, 3.0]
FOUNTAIN_R = 1.4
PILASTER_R = 0.40
PIL_XS = [-7.5, -4.5, -1.5, 1.5, 4.5, 7.5]
PIL_YS = [-4.5, 0.0, 4.5]

CIRCLES = [(x, y, COL_R) for x in COL_XS for y in COL_YS]
CIRCLES.append((0.0, 0.0, FOUNTAIN_R))
for x in PIL_XS:
    CIRCLES.append((x, HALL_Y, PILASTER_R))
    CIRCLES.append((x, -HALL_Y, PILASTER_R))
for y in PIL_YS:
    CIRCLES.append((HALL_X, y, PILASTER_R))
    CIRCLES.append((-HALL_X, y, PILASTER_R))


def inside_interior(x, y):
    return abs(x) <= HALL_X and abs(y) <= HALL_Y


def inside_wall_ring(x, y):
    return abs(x) <= HALL_X + WALL_T and abs(y) <= HALL_Y + WALL_T


pixels = bytearray(W * H)
for r in range(H):
    for c in range(W):
        x = ORIGIN_X + (c + 0.5) * RES
        y = ORIGIN_Y + (H - 1 - r + 0.5) * RES
        if inside_interior(x, y):
            val = FREE
        elif inside_wall_ring(x, y):
            val = OCC
        else:
            val = UNK
        if val != UNK:
            for (cx, cy, rad) in CIRCLES:
                if (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad:
                    val = OCC
                    break
        pixels[r * W + c] = val

out_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(out_dir, 'map.pgm'), 'wb') as f:
    f.write(b'P5\n%d %d\n255\n' % (W, H))
    f.write(bytes(pixels))

with open(os.path.join(out_dir, 'map.yaml'), 'w') as f:
    f.write('image: map.pgm\n')
    f.write('resolution: 0.05\n')
    f.write('origin: [-11.0, -8.0, 0.0]\n')
    f.write('negate: 0\n')
    f.write('occupied_thresh: 0.65\n')
    f.write('free_thresh: 0.196\n')

print('map written: %dx%d, origin=(%.1f, %.1f)' % (W, H, ORIGIN_X, ORIGIN_Y))
