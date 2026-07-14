#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
신일 창문형 에어컨 냉기 유도 덕트 — 측면도 기준 상향 벤드 어댑터 (모서리 R)
  - 사각(모서리 R) 흡입구 140 x 80 이 에어컨 토출면(수직)에 수직 플랜지로 밀착,
    냉기를 큰 반경으로 말아 올려 Ø148 원통으로 토출.
  - 측면도: 왼쪽 수직 = 에어컨 본체/토출면(상·하 립으로 물림),
            큰 라운드 코너로 부드럽게 꺾여 위로 뻗는 목 = 원통 토출.
  - 모든 모서리에 R(필렛): 단면 사각 모서리 + 벤드 + 플랜지 외곽.

좌표계: 에어컨 토출면 = x=0 (YZ). 냉기 +X 유입 → 벤드 → +Y(수평 옆) 토출.
        Y = 가로(140, 벤드 평면 내), Z = 세로(80, 평면 밖=수직).
        ※ 원통 토출을 위(+Z)에서 90° 돌려 수평(+Y)으로 배출.

의존성 없는 순수 파이썬 STL(바이너리) 생성 + 수밀 자동 검증.
  python3 generate_stl.py   ->  cold_air_duct.stl
"""

import math
import struct

# ----------------------------------------------------------------------------
# 파라미터 (mm)
# ----------------------------------------------------------------------------
INLET_W    = 140.0   # 사각 흡입구 가로 (수평, Y, 벤드 평면 내)
INLET_D    = 80.0    # 사각 흡입구 세로 (수직, Z, 평면 밖)
CORNER_R   = 20.0    # ★ 단면 사각 모서리 라운드 반경 (모서리 R)
OUTLET_DIA = 142.0   # 원통 토출 보어(내경). 수나사 체결용으로 Ø150 호스 안에 들어가도록 축소.
BEND_DEG   = 90.0    # 벤드 각도 (90=옆으로 수평, 180=반대편)
BEND_R     = 80.0    # ★ 벤드 중심선 반경 (꺾임 거리 최소화 → 타이트)
LIP_IN     = 8.0     # 사각 흡입 직선 스냅(+X) — 최소화(거의 흡입면서 바로 꺾임)
LIP_OUT    = 46.0    # 원통 토출 직선 칼라(나사부 길이 확보)
WALL       = 2.6     # 벽 두께
FLANGE     = 14.0    # 흡입 수직 플랜지 폭 (0=없음)
FLANGE_TH  = 3.0     # 플랜지 두께(X)
FLANGE_R   = 10.0    # ★ 플랜지 외곽 모서리 라운드
MOUNT_R    = 250.0   # ★ 에어컨 접촉면 곡률 반경(추정). 세로(수직) 방향 곡면. 0=평면
MOUNT_START= 1.0/3   # ★ 세로 아래에서 이 비율 지점부터 곡면 시작(그 아래는 평면). 1/3
BEAD_T     = 0.0     # 호스 이탈방지 비드(나사산으로 대체, 0=없음)
BEAD_H     = 3.0     # 비드 높이(축)

# ── 토출 수나사(외부 나사산) — Ø150 호스/커넥터가 위로 체결 ──
THREAD_ON     = True
HOSE_DIA      = 150.0  # 연결 호스/커넥터 공칭경(내부 나사산)
THREAD_PITCH  = 15.0   # 나사 피치(호스 주름 간격에 맞춰 실측·조정)
THREAD_ROUND  = 2.0    # 나사산 단면 반경(둥근 프로파일). 마루=칼라외경+이 값
THREAD_STARTS = 2      # 나사 줄 수(샘플 커넥터 내부 리브 2개 → 2줄)
THREAD_MARGIN = 3.0    # 칼라 양끝 나사 없는 여유
THR_RSTEP     = 12     # 나사 단면 분할
THR_SSTEP_PT  = 28     # 한 바퀴당 세로 분할

N          = 160     # 원주 분할
BEND_STEPS = 80      # 벤드 분할
LIP_STEPS  = 5       # 직선 립 분할

OUT_PATH = "cold_air_duct.stl"

# 벤드 평면 = X-Y(수평).  U=면내(입구에서 Y, 가로140),  V=면밖(Z, 세로80)
HU = INLET_W / 2.0   # U-반치수(가로 140, 벤드 평면 내)
HV = INLET_D / 2.0   # V-반치수(세로 80, 평면 밖=수직)
YH = INLET_W / 2.0   # 플랜지 Y(가로)-반치수
ZH = INLET_D / 2.0   # 플랜지 Z(세로)-반치수
R  = OUTLET_DIA / 2.0

# ----------------------------------------------------------------------------
# 벡터 유틸
# ----------------------------------------------------------------------------
def sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def add(a, b): return (a[0]+b[0], a[1]+b[1], a[2]+b[2])
def scale(a, s): return (a[0]*s, a[1]*s, a[2]*s)
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def dot(a, b): return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def norm(a):
    L = math.sqrt(dot(a, a)) or 1.0
    return (a[0]/L, a[1]/L, a[2]/L)

# ----------------------------------------------------------------------------
# 둥근 사각형 SDF (반치수 hu,hv, 코너반경 rc) — 각도 theta 광선의 경계 반지름
# ----------------------------------------------------------------------------
def rrect_sdf(x, y, hu, hv, rc):
    qx = abs(x) - (hu - rc)
    qy = abs(y) - (hv - rc)
    outside = math.hypot(max(qx, 0.0), max(qy, 0.0))
    inside = min(max(qx, qy), 0.0)
    return outside + inside - rc

def rrect_radius(theta, hu, hv, rc):
    rc = max(0.0, min(rc, min(hu, hv)))
    c, s = math.cos(theta), math.sin(theta)
    lo, hi = 0.0, hu + hv + rc + 1.0
    for _ in range(40):                       # 이분법으로 경계 t 탐색
        mid = 0.5 * (lo + hi)
        if rrect_sdf(mid*c, mid*s, hu, hv, rc) < 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)

# 단면 프로파일 점: 둥근사각(m=0) <-> 원(m=1)
def profile_point(theta, m, hu, hv, rc, r):
    rr = rrect_radius(theta, hu, hv, rc)
    rx, ry = rr*math.cos(theta), rr*math.sin(theta)
    cx, cy = r*math.cos(theta),  r*math.sin(theta)
    return (1.0-m)*rx + m*cx, (1.0-m)*ry + m*cy

def ss(t): return t*t*(3-2*t)

# ----------------------------------------------------------------------------
# 중심선 스테이션 프레임: V=(0,1,0)(평면밖), U=norm(cross(V,T))
# ----------------------------------------------------------------------------
def build_stations():
    V = (0.0, 0.0, 1.0)                    # 평면 밖 축(Z, 세로80) — 벤드는 X-Y 평면
    st = []
    bend = math.radians(BEND_DEG)

    def frame(C, T): return {"C": C, "U": norm(cross(V, norm(T))), "V": V}
    def arc_C(a): return (LIP_IN + BEND_R*math.sin(a), BEND_R*(1-math.cos(a)), 0.0)
    def arc_T(a): return (math.cos(a), math.sin(a), 0.0)

    for i in range(LIP_STEPS + 1):            # 흡입 직선 스냅 x:0→LIP_IN
        x = LIP_IN * i / LIP_STEPS
        f = frame((x, 0.0, 0.0), (1.0, 0.0, 0.0)); f["m"] = 0.0
        st.append(f)
    for i in range(1, BEND_STEPS + 1):        # 벤드 +X→+Z
        a = bend * i / BEND_STEPS
        f = frame(arc_C(a), arc_T(a)); f["m"] = ss(i / BEND_STEPS)
        st.append(f)
    Te, Ce = arc_T(bend), arc_C(bend)         # 토출 직선 칼라
    for i in range(1, LIP_STEPS + 1):
        s = LIP_OUT * i / LIP_STEPS
        f = frame(add(Ce, scale(Te, s)), Te); f["m"] = 1.0
        st.append(f)
    return st

# ----------------------------------------------------------------------------
# 메시
# ----------------------------------------------------------------------------
class Mesh:
    def __init__(self): self.v = []; self.t = []
    def add_v(self, p): self.v.append(p); return len(self.v)-1
    def quad(self, a, b, c, d): self.t.append((a, b, c)); self.t.append((a, c, d))

def prof3d(f, theta, off):
    pu, pv = profile_point(theta, f["m"], HU+off, HV+off, CORNER_R+off, R+off)
    C, U, V = f["C"], f["U"], f["V"]
    return (C[0]+pu*U[0]+pv*V[0], C[1]+pu*U[1]+pv*V[1], C[2]+pu*U[2]+pv*V[2])

def build_shell(mesh):
    st = build_stations()
    thetas = [2.0*math.pi*k/N for k in range(N)]
    outer = [[mesh.add_v(prof3d(f, th, WALL)) for th in thetas] for f in st]
    inner = [[mesh.add_v(prof3d(f, th, 0.0))  for th in thetas] for f in st]
    L = len(st)
    for i in range(L-1):
        for k in range(N):
            k2 = (k+1) % N
            mesh.quad(outer[i][k], outer[i][k2], outer[i+1][k2], outer[i+1][k])
            mesh.quad(inner[i][k], inner[i+1][k], inner[i+1][k2], inner[i][k2])
    for k in range(N):                        # 흡입 림
        k2 = (k+1) % N
        mesh.quad(outer[0][k], inner[0][k], inner[0][k2], outer[0][k2])
    for k in range(N):                        # 토출 림
        k2 = (k+1) % N
        mesh.quad(outer[L-1][k], outer[L-1][k2], inner[L-1][k2], inner[L-1][k])
    return st

# ----------------------------------------------------------------------------
# 흡입 플랜지: 수직(YZ) 둥근사각 프레임, 두께 -X
# ----------------------------------------------------------------------------
def build_flange(mesh, st):
    if FLANGE <= 0: return
    x1, x0 = 0.0, -FLANGE_TH
    thetas = [2.0*math.pi*k/N for k in range(N)]
    def ring(hu, hv, rc, x, curve=False):
        out = []
        for th in thetas:
            rr = rrect_radius(th, hu, hv, rc)
            Y = rr*math.cos(th); Z = rr*math.sin(th)
            xx = x
            # 접촉면(뒷면) 수직(세로) 곡면: 축=수평(Y), 세로 아래 1/3 지점부터 뒤로 말림
            if curve and MOUNT_R > 0:
                oz_full = ZH + WALL + FLANGE
                z_start = -oz_full + 2*oz_full*MOUNT_START   # 아래에서 1/3
                if Z > z_start:
                    d = Z - z_start
                    sag = MOUNT_R - math.sqrt(max(0.0, MOUNT_R*MOUNT_R - d*d)) if d < MOUNT_R else MOUNT_R
                    xx = x - sag
            out.append(mesh.add_v((xx, Y, Z)))
        return out
    # 플랜지는 YZ평면.  rrect_radius(hu,hv): x=cos→Y(가로), y=sin→Z(세로)
    iy, iz = YH+WALL, ZH+WALL          # 구멍 = 스커트 외곽 (Y가로반, Z세로반)
    oy, oz = YH+WALL+FLANGE, ZH+WALL+FLANGE
    of = ring(oy, oz, FLANGE_R+FLANGE, x1); ob = ring(oy, oz, FLANGE_R+FLANGE, x0, curve=True)
    iff = ring(iy, iz, CORNER_R+WALL, x1);  ib = ring(iy, iz, CORNER_R+WALL, x0, curve=True)
    for k in range(N):
        k2 = (k+1) % N
        mesh.quad(of[k], of[k2], iff[k2], iff[k])   # 앞면
        mesh.quad(ob[k], ib[k], ib[k2], ob[k2])     # 뒷면(에어컨 밀착)
        mesh.quad(ob[k], ob[k2], of[k2], of[k])     # 외측
        mesh.quad(ib[k], iff[k], iff[k2], ib[k2])   # 내측(구멍)

# ----------------------------------------------------------------------------
# 호스 이탈방지 비드 (토출 국소 프레임 기준 링)
# ----------------------------------------------------------------------------
def build_bead(mesh, st):
    if BEAD_T <= 0: return
    f = st[-1]; C, U, V = f["C"], f["U"], f["V"]
    T = norm(cross(U, V))
    thetas = [2.0*math.pi*k/N for k in range(N)]
    Cc = sub(C, scale(T, 4.0))
    def ring(rr, along):
        base = add(Cc, scale(T, along))
        out = []
        for th in thetas:
            d = (math.cos(th), math.sin(th))
            p = (base[0]+rr*(d[0]*U[0]+d[1]*V[0]),
                 base[1]+rr*(d[0]*U[1]+d[1]*V[1]),
                 base[2]+rr*(d[0]*U[2]+d[1]*V[2]))
            out.append(mesh.add_v(p))
        return out
    ri, ro = R+WALL, R+WALL+BEAD_T
    bi=ring(ri,-BEAD_H/2); bo=ring(ro,-BEAD_H/2); ti=ring(ri,BEAD_H/2); to=ring(ro,BEAD_H/2)
    for k in range(N):
        k2 = (k+1) % N
        mesh.quad(bo[k], bo[k2], to[k2], to[k])
        mesh.quad(bi[k], ti[k], ti[k2], bi[k2])
        mesh.quad(bi[k], bi[k2], bo[k2], bo[k])
        mesh.quad(ti[k], to[k], to[k2], ti[k2])

# ----------------------------------------------------------------------------
# 토출 수나사(외부 나사산): 칼라 바깥면에 나선 튜브(둥근 리브)를 감아 생성.
#   호스/커넥터(내부 나사산, Ø150)가 위로 돌려 끼워짐.
# ----------------------------------------------------------------------------
def build_thread(mesh, st):
    if not THREAD_ON: return
    f = st[-1]
    U, V = f["U"], f["V"]
    T = norm(cross(U, V))                     # 축(진행) 방향
    C_end = f["C"]                            # 토출 개구 중심
    C_start = sub(C_end, scale(T, LIP_OUT))   # 칼라 시작(벤드 끝)
    rr = R + WALL                             # 칼라 외경(나사 골 표면)
    dphi = 2.0*math.pi / THREAD_PITCH
    s0, s1 = THREAD_MARGIN, LIP_OUT - THREAD_MARGIN
    length = s1 - s0
    steps = max(8, int(length / THREAD_PITCH * THR_SSTEP_PT))
    M = THR_RSTEP
    for k in range(THREAD_STARTS):
        phase0 = 2.0*math.pi*k/THREAD_STARTS
        rings, centers = [], []
        for i in range(steps+1):
            s = s0 + length*i/steps
            phi = dphi*s + phase0
            cp, sp = math.cos(phi), math.sin(phi)
            radial = (cp*U[0]+sp*V[0], cp*U[1]+sp*V[1], cp*U[2]+sp*V[2])
            H = (C_start[0]+s*T[0]+rr*radial[0],
                 C_start[1]+s*T[1]+rr*radial[1],
                 C_start[2]+s*T[2]+rr*radial[2])
            drad = (-sp*U[0]+cp*V[0], -sp*U[1]+cp*V[1], -sp*U[2]+cp*V[2])
            Th = norm((T[0]+rr*dphi*drad[0], T[1]+rr*dphi*drad[1], T[2]+rr*dphi*drad[2]))
            n1 = norm(sub(radial, scale(Th, dot(radial, Th))))
            n2 = cross(Th, n1)
            ring = []
            for j in range(M):
                psi = 2.0*math.pi*j/M
                c2, s2 = math.cos(psi), math.sin(psi)
                p = (H[0]+THREAD_ROUND*(c2*n1[0]+s2*n2[0]),
                     H[1]+THREAD_ROUND*(c2*n1[1]+s2*n2[1]),
                     H[2]+THREAD_ROUND*(c2*n1[2]+s2*n2[2]))
                ring.append(mesh.add_v(p))
            rings.append(ring); centers.append(H)
        for i in range(len(rings)-1):
            for j in range(M):
                j2 = (j+1) % M
                mesh.quad(rings[i][j], rings[i][j2], rings[i+1][j2], rings[i+1][j])
        c0 = mesh.add_v(centers[0]); cN = mesh.add_v(centers[-1])
        for j in range(M):
            j2 = (j+1) % M
            mesh.t.append((c0, rings[0][j2], rings[0][j]))      # 시작 캡
            mesh.t.append((cN, rings[-1][j], rings[-1][j2]))    # 끝 캡

# ----------------------------------------------------------------------------
# 검증 / 기록
# ----------------------------------------------------------------------------
def check_watertight(mesh):
    from collections import defaultdict
    e = defaultdict(int)
    for (a, b, c) in mesh.t:
        for u, w in ((a, b), (b, c), (c, a)): e[(u, w)] += 1
    bad = sum(1 for cnt in e.values() if cnt != 1)
    unmatched = sum(1 for (u, w), cnt in e.items() if e.get((w, u), 0) != cnt)
    return bad, unmatched, len(e)

def tri_normal(p0, p1, p2):
    n = cross(sub(p1, p0), sub(p2, p0)); L = math.sqrt(dot(n, n))
    return (0.0, 0.0, 0.0) if L < 1e-12 else (n[0]/L, n[1]/L, n[2]/L)

def bbox(mesh):
    xs=[p[0] for p in mesh.v]; ys=[p[1] for p in mesh.v]; zs=[p[2] for p in mesh.v]
    return (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))

def write_stl(mesh, path):
    with open(path, "wb") as fp:
        h = b"cold_air_duct Shinil AC rounded elbow 140x80 to D148"
        fp.write(h + b" "*(80-len(h)))
        fp.write(struct.pack("<I", len(mesh.t)))
        for (a, b, c) in mesh.t:
            p0, p1, p2 = mesh.v[a], mesh.v[b], mesh.v[c]
            fp.write(struct.pack("<3f", *tri_normal(p0, p1, p2)))
            fp.write(struct.pack("<3f", *p0)); fp.write(struct.pack("<3f", *p1)); fp.write(struct.pack("<3f", *p2))
            fp.write(struct.pack("<H", 0))

def main():
    mesh = Mesh()
    st = build_shell(mesh)
    build_flange(mesh, st)
    build_bead(mesh, st)
    build_thread(mesh, st)
    bad, unmatched, ne = check_watertight(mesh)
    write_stl(mesh, OUT_PATH)
    bx, by, bz = bbox(mesh)
    crest = OUTLET_DIA + 2*WALL + 2*THREAD_ROUND
    print(f"[형상] {BEND_DEG:.0f}° 수평 벤드, 흡입 {INLET_W:.0f}x{INLET_D:.0f}(R{CORNER_R:.0f}) → Ø{OUTLET_DIA:.0f} 보어 원통")
    print(f"[나사] 외부 수나사 {THREAD_STARTS}줄, 피치 {THREAD_PITCH:.0f}, 마루 Ø{crest:.1f} (호스 Ø{HOSE_DIA:.0f} 체결)")
    if MOUNT_R > 0:
        oz_full = ZH+WALL+FLANGE
        d_top = oz_full - (-oz_full + 2*oz_full*MOUNT_START)   # 상단까지 곡면 거리
        sag = MOUNT_R - math.sqrt(max(0.0, MOUNT_R*MOUNT_R - d_top*d_top))
        print(f"[접촉면] 수직 곡면 R={MOUNT_R:.0f}, 아래 {MOUNT_START*100:.0f}% 지점부터 곡면, 상단 새그 {sag:.1f}mm")
    print(f"[벤드] 중심선 R={BEND_R:.0f}, 흡입립 {LIP_IN:.0f}, 토출칼라 {LIP_OUT:.0f}, 벽 {WALL}")
    print(f"[외형] 약 {bx:.0f} x {by:.0f} x {bz:.0f} mm  (X x Y x Z)")
    print(f"[메시] 정점 {len(mesh.v)}, 삼각형 {len(mesh.t)}")
    print(f"[검증] 고유에지 {ne}, 비매너폴드(!=1)={bad}, 미쌍={unmatched}  → 0/0 이면 수밀")
    print(f"[출력] {OUT_PATH} ({len(mesh.t)} tri, binary STL)")

if __name__ == "__main__":
    main()
