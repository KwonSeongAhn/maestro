#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
신일 창문형 에어컨 냉기 유도 덕트 어댑터 (Square-to-Round transition duct)
- 의존성 없는 순수 파이썬 STL(바이너리) 생성기.
- 스케치: 140 x 80 사각 흡입구  ->  Ø110 원형 토출구, 전이 높이 40.
- 실외 창틀에 고정된 에어컨의 냉기토출구에 씌워, 유연 덕트호스(Ø110)를
  연결해 실내로 냉기를 끌어오기 위한 부품.

이 스크립트를 실행하면 cold_air_duct.stl 이 생성되고,
메시가 수밀(watertight/manifold)인지 자동 검증 리포트를 출력한다.
"""

import math
import struct

# ----------------------------------------------------------------------------
# 파라미터 (mm) — 스케치 기준값. 필요 시 여기만 고치면 됨.
# ----------------------------------------------------------------------------
INLET_W      = 140.0   # 사각 흡입구 가로 (에어컨 토출구 폭)
INLET_D      = 80.0    # 사각 흡입구 세로 (에어컨 토출구 깊이)
TRANS_H      = 40.0    # 사각->원형 전이부 높이  (스케치의 '40')
OUTLET_DIA   = 110.0   # 원형 토출구 지름       (스케치의 '110', Ø110 플렉시블 호스)
WALL         = 2.4     # 벽 두께 (0.4 노즐 기준 6 벽선)
SKIRT_H      = 14.0    # 흡입구 스커트(에어컨 토출구에 끼워지는 직벽) 높이
COLLAR_H     = 14.0    # 원형 호스 연결 칼라(직벽) 높이
FLANGE       = 12.0    # 흡입구 둘레 고정 플랜지 폭
FLANGE_TH    = 3.0     # 플랜지 두께
BEAD_H       = 2.0     # 호스 이탈 방지용 칼라 외부 비드(돌기) 높이
BEAD_T       = 1.6     # 비드 두께(반경 방향)
N            = 160     # 단면 분할 수(원주 방향 정점 수). 클수록 매끈.
MORPH_STEPS  = 40      # 전이부 세로 분할 수. 클수록 매끈.

OUT_PATH = "cold_air_duct.stl"

# ----------------------------------------------------------------------------
# 단면 프로파일: 각도 theta 에서 반경을 정하되, m(0->1) 로 사각<->원 을 보간.
#   m=0  : 반치수 (hw,hd) 사각형
#   m=1  : 반경 r 원
# 사각형 위 점은 중심에서 각도 theta 로 쏜 광선이 사각 경계에 닿는 점.
# ----------------------------------------------------------------------------
def ray_rect(theta, hw, hd):
    c = math.cos(theta)
    s = math.sin(theta)
    tx = abs(c) / hw if hw > 1e-9 else float("inf")
    ty = abs(s) / hd if hd > 1e-9 else float("inf")
    d = 1.0 / max(tx, ty)
    return d * c, d * s

def profile_point(theta, m, hw, hd, r):
    rx, ry = ray_rect(theta, hw, hd)
    cx, cy = r * math.cos(theta), r * math.sin(theta)
    return (1.0 - m) * rx + m * cx, (1.0 - m) * ry + m * cy

# 파생 치수
HW = INLET_W / 2.0
HD = INLET_D / 2.0
R  = OUTLET_DIA / 2.0

# ----------------------------------------------------------------------------
# 레벨(단면) 스택 구성. 각 레벨 = (z, m, hw, hd, r) — 내부(개구) 치수 기준.
# 외부 프로파일은 반치수/반경에 WALL 을 더해 계산.
# ----------------------------------------------------------------------------
def build_levels():
    levels = []
    z = 0.0
    # 1) 스커트(직벽 사각) : 바닥 -> 스커트 상단
    levels.append((z,            0.0, HW, HD, R))
    levels.append((z + SKIRT_H,  0.0, HW, HD, R))
    z += SKIRT_H
    # 2) 전이부: 사각(m=0) -> 원(m=1)
    for i in range(1, MORPH_STEPS + 1):
        t = i / MORPH_STEPS
        # smoothstep 로 상/하단을 부드럽게
        m = t * t * (3 - 2 * t)
        levels.append((z + TRANS_H * t, m, HW, HD, R))
    z += TRANS_H
    # 3) 원형 칼라(직벽)
    levels.append((z,             1.0, HW, HD, R))
    levels.append((z + COLLAR_H,  1.0, HW, HD, R))
    z += COLLAR_H
    return levels, z  # z = 전체 높이

# ----------------------------------------------------------------------------
# 메시 빌더 (정점/삼각형 누적). 삼각형은 (v0,v1,v2) 인덱스로 CCW=바깥.
# ----------------------------------------------------------------------------
class Mesh:
    def __init__(self):
        self.v = []
        self.t = []
    def add_v(self, x, y, z):
        self.v.append((x, y, z))
        return len(self.v) - 1
    def add_t(self, a, b, c):
        self.t.append((a, b, c))
    def add_quad(self, a, b, c, d):
        # a-b-c-d 순환(바깥에서 CCW). 두 삼각형으로.
        self.t.append((a, b, c))
        self.t.append((a, c, d))

def build_shell(mesh):
    levels, total_h = build_levels()
    thetas = [2.0 * math.pi * k / N for k in range(N)]

    outer_rings = []  # 각 레벨의 외부 정점 인덱스 리스트[N]
    inner_rings = []
    for (z, m, hw, hd, r) in levels:
        oring = []
        iring = []
        for th in thetas:
            ox, oy = profile_point(th, m, hw + WALL, hd + WALL, r + WALL)
            ix, iy = profile_point(th, m, hw,        hd,        r)
            oring.append(mesh.add_v(ox, oy, z))
            iring.append(mesh.add_v(ix, iy, z))
        outer_rings.append(oring)
        inner_rings.append(iring)

    L = len(levels)
    # 외벽 (바깥으로 향하도록 CCW)
    for i in range(L - 1):
        for k in range(N):
            k2 = (k + 1) % N
            a = outer_rings[i][k]
            b = outer_rings[i][k2]
            c = outer_rings[i + 1][k2]
            d = outer_rings[i + 1][k]
            mesh.add_quad(a, b, c, d)
    # 내벽 (안쪽으로 향하도록 반대 감김)
    for i in range(L - 1):
        for k in range(N):
            k2 = (k + 1) % N
            a = inner_rings[i][k]
            b = inner_rings[i][k2]
            c = inner_rings[i + 1][k2]
            d = inner_rings[i + 1][k]
            mesh.add_quad(a, d, c, b)
    # 바닥 림(레벨0): 외부->내부 링을 잇는 아래쪽 환형 (아래로 향함)
    for k in range(N):
        k2 = (k + 1) % N
        o1 = outer_rings[0][k]; o2 = outer_rings[0][k2]
        i1 = inner_rings[0][k]; i2 = inner_rings[0][k2]
        mesh.add_quad(o1, i1, i2, o2)   # 아래(-Z) 방향
    # 상단 림(마지막): 위쪽 환형 (위로 향함)
    last = L - 1
    for k in range(N):
        k2 = (k + 1) % N
        o1 = outer_rings[last][k]; o2 = outer_rings[last][k2]
        i1 = inner_rings[last][k]; i2 = inner_rings[last][k2]
        mesh.add_quad(o1, o2, i2, i1)   # 위(+Z) 방향
    return total_h

# ----------------------------------------------------------------------------
# 호스 이탈방지 비드: 칼라 외부에 얇은 링(사각형 단면 도넛)을 별도 솔리드로.
# ----------------------------------------------------------------------------
def build_bead(mesh, total_h):
    z_top = total_h - 3.0            # 칼라 상단서 살짝 아래
    z_bot = z_top - BEAD_H
    r_in  = R + WALL                 # 칼라 외경
    r_out = R + WALL + BEAD_T
    thetas = [2.0 * math.pi * k / N for k in range(N)]
    # 4개의 링: (하단 안/밖), (상단 안/밖)
    ring = {}
    for name, (rr, zz) in {
        "bi": (r_in,  z_bot), "bo": (r_out, z_bot),
        "ti": (r_in,  z_top), "to": (r_out, z_top),
    }.items():
        ring[name] = [mesh.add_v(rr*math.cos(t), rr*math.sin(t), zz) for t in thetas]
    for k in range(N):
        k2 = (k + 1) % N
        # 바깥 원통면
        mesh.add_quad(ring["bo"][k], ring["bo"][k2], ring["to"][k2], ring["to"][k])
        # 안쪽 원통면(반대)
        mesh.add_quad(ring["bi"][k], ring["ti"][k], ring["ti"][k2], ring["bi"][k2])
        # 하단면(아래로)
        mesh.add_quad(ring["bi"][k], ring["bi"][k2], ring["bo"][k2], ring["bo"][k])
        # 상단면(위로)
        mesh.add_quad(ring["ti"][k], ring["to"][k], ring["to"][k2], ring["ti"][k2])

# ----------------------------------------------------------------------------
# 플랜지: 흡입구 둘레 평판 프레임(사각 도넛). 구멍은 스커트 외곽과 일치.
# ----------------------------------------------------------------------------
def build_flange(mesh):
    z0 = 0.0
    z1 = FLANGE_TH
    ohw = HW + WALL + FLANGE   # 플랜지 외곽 반치수
    ohd = HD + WALL + FLANGE
    ihw = HW + WALL            # 구멍 = 스커트 외곽
    ihd = HD + WALL
    def rect4(hw, hd, z):
        return [mesh.add_v(hw, hd, z), mesh.add_v(-hw, hd, z),
                mesh.add_v(-hw, -hd, z), mesh.add_v(hw, -hd, z)]
    ot = rect4(ohw, ohd, z1); ob = rect4(ohw, ohd, z0)  # outer top/bottom
    it = rect4(ihw, ihd, z1); ib = rect4(ihw, ihd, z0)  # inner top/bottom
    for k in range(4):
        k2 = (k + 1) % 4
        # 상단 프레임(위로)
        mesh.add_quad(ot[k], ot[k2], it[k2], it[k])
        # 하단 프레임(아래로)
        mesh.add_quad(ob[k], ib[k], ib[k2], ob[k2])
        # 외측면(바깥)
        mesh.add_quad(ob[k], ob[k2], ot[k2], ot[k])
        # 내측면(구멍 안쪽)
        mesh.add_quad(ib[k], it[k], it[k2], ib[k2])

# ----------------------------------------------------------------------------
# 검증: 각 방향 있는 반쪽에지가 정확히 반대 방향과 1:1 매칭 -> 수밀.
# ----------------------------------------------------------------------------
def check_watertight(mesh):
    from collections import defaultdict
    edges = defaultdict(int)
    for (a, b, c) in mesh.t:
        for (u, w) in ((a, b), (b, c), (c, a)):
            edges[(u, w)] += 1
    bad = 0
    unmatched = 0
    for (u, w), cnt in edges.items():
        if cnt != 1:
            bad += 1
        if edges.get((w, u), 0) != cnt:
            unmatched += 1
    return bad, unmatched, len(edges)

# ----------------------------------------------------------------------------
# 법선 계산 + 바이너리 STL 기록
# ----------------------------------------------------------------------------
def normal(p0, p1, p2):
    ux, uy, uz = p1[0]-p0[0], p1[1]-p0[1], p1[2]-p0[2]
    vx, vy, vz = p2[0]-p0[0], p2[1]-p0[1], p2[2]-p0[2]
    nx = uy*vz - uz*vy
    ny = uz*vx - ux*vz
    nz = ux*vy - uy*vx
    L = math.sqrt(nx*nx + ny*ny + nz*nz)
    if L < 1e-12:
        return 0.0, 0.0, 0.0
    return nx/L, ny/L, nz/L

def write_stl(mesh, path):
    with open(path, "wb") as f:
        header = b"cold_air_duct Shinil window AC square-to-round adapter"
        f.write(header + b" " * (80 - len(header)))
        f.write(struct.pack("<I", len(mesh.t)))
        for (a, b, c) in mesh.t:
            p0, p1, p2 = mesh.v[a], mesh.v[b], mesh.v[c]
            nx, ny, nz = normal(p0, p1, p2)
            f.write(struct.pack("<3f", nx, ny, nz))
            f.write(struct.pack("<3f", *p0))
            f.write(struct.pack("<3f", *p1))
            f.write(struct.pack("<3f", *p2))
            f.write(struct.pack("<H", 0))

def main():
    mesh = Mesh()
    total_h = build_shell(mesh)
    build_bead(mesh, total_h)
    build_flange(mesh)

    bad, unmatched, nedges = check_watertight(mesh)
    write_stl(mesh, OUT_PATH)

    print(f"[치수] 흡입 {INLET_W:.0f}x{INLET_D:.0f} mm, 토출 Ø{OUTLET_DIA:.0f} mm")
    print(f"[높이] 스커트 {SKIRT_H:.0f} + 전이 {TRANS_H:.0f} + 칼라 {COLLAR_H:.0f} = {total_h:.1f} mm")
    print(f"[플랜지] 외곽 {INLET_W+2*(WALL+FLANGE):.0f} x {INLET_D+2*(WALL+FLANGE):.0f} mm, 두께 {FLANGE_TH:.0f} mm")
    print(f"[메시] 정점 {len(mesh.v)}, 삼각형 {len(mesh.t)}")
    print(f"[검증] 고유 에지 {nedges}, 미쌍(원통 내부는 다중솔리드 정상)={unmatched}")
    print(f"[출력] {OUT_PATH} ({len(mesh.t)} tri, binary STL)")

if __name__ == "__main__":
    main()
