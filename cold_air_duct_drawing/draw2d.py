#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""신일 창문형 에어컨 냉기 유도 덕트 — 2D 엔지니어링 도면(SVG) 생성기.
   generate_stl.py 의 파라미터/센터라인 수식을 그대로 사용해 정확한 윤곽을 계산한다."""
import math

# ---- 원본 파라미터 (generate_stl.py 와 동일) ----
INLET_W, INLET_D, CORNER_R = 140.0, 80.0, 20.0
WALL = 2.6
FLANGE, FLANGE_TH, FLANGE_R = 14.0, 3.0, 10.0
LIP_IN, BEND_R, BEND_DEG, LIP_OUT = 8.0, 80.0, 90.0, 223.0
OUTLET_DIA = 142.0
THREAD_PITCH, THREAD_LEN, THREAD_STARTS, THREAD_ROUND = 15.0, 42.0, 2, 2.0
HOSE_DIA = 150.0
MOUNT_R, MOUNT_START = 250.0, 1.0/3
HOLE_D = 4.5

HU, HV = INLET_W/2, INLET_D/2          # 70, 40 (가로 in-plane, 세로 out-of-plane)
R = OUTLET_DIA/2                        # 71
OD = R + WALL                          # 73.6  collar 외경 반경 -> Ø147.2
CREST = OD + THREAD_ROUND              # 75.6  나사 마루 반경 -> ~Ø151

# ============================================================
# 벤드(엘보) 센터라인 & 벽 윤곽 (X-Y 평면; +X 유입, 90° 벤드 후 +Y 토출)
# ============================================================
def ss(t): return t*t*(3-2*t)
def centerline():
    pts = []  # (x, y, tangent_angle_rad, m)
    bend = math.radians(BEND_DEG)
    NB = 60
    # 흡입 직선 립
    pts.append((0.0, 0.0, 0.0, 0.0))
    pts.append((LIP_IN, 0.0, 0.0, 0.0))
    # 벤드: C=(8+80 sin a, 80(1-cos a)), tangent=a
    for i in range(1, NB+1):
        a = bend*i/NB
        x = LIP_IN + BEND_R*math.sin(a)
        y = BEND_R*(1-math.cos(a))
        pts.append((x, y, a, ss(i/NB)))
    # 토출 직선 칼라 (+Y)
    Ce = (LIP_IN + BEND_R*math.sin(bend), BEND_R*(1-math.cos(bend)))
    for i in range(1, 21):
        s = LIP_OUT*i/20
        pts.append((Ce[0], Ce[1]+s, bend, 1.0))
    return pts

def hw(m, wall=True):
    base = (1-m)*HU + m*R           # 면내 반폭(가로측): 70 -> 71
    return base + (WALL if wall else 0.0)

def offset_path(sign, wall=True):
    out = []
    for (x, y, ang, m) in centerline():
        nx, ny = -math.sin(ang), math.cos(ang)   # 좌측 법선
        w = hw(m, wall)
        out.append((x + sign*nx*w, y + sign*ny*w))
    return out

# ============================================================
# 좌표 변환 헬퍼
# ============================================================
S = 1.95   # px per mm
def T_elbow(x, y, ox, oy):
    return (ox + x*S, oy - y*S)      # part +X→right, +Y→up

svg = []
W, H = 1680, 1290
def add(s): svg.append(s)

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica,Arial,sans-serif">')
add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
# 도면 외곽 프레임
add(f'<rect x="20" y="20" width="{W-40}" height="{H-40}" fill="none" stroke="#111" stroke-width="2.5"/>')
add(f'<rect x="34" y="34" width="{W-68}" height="{H-68}" fill="none" stroke="#111" stroke-width="1"/>')

# 선 스타일
OUT = 'stroke="#111" stroke-width="2" fill="none"'
HID = 'stroke="#111" stroke-width="1" fill="none" stroke-dasharray="7,4"'
CEN = 'stroke="#c0392b" stroke-width="0.9" fill="none" stroke-dasharray="14,3,2,3"'
DIM = 'stroke="#1a5276" stroke-width="0.9" fill="none"'
THN = 'stroke="#111" stroke-width="0.9" fill="none"'

def dim_txt(x, y, s, size=15, anchor="middle", col="#1a5276", rot=0):
    tr = f' transform="rotate({rot} {x} {y})"' if rot else ''
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{col}" text-anchor="{anchor}"{tr}>{s}</text>'
def label(x, y, s, size=17, anchor="start", col="#111", weight="normal"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{col}" text-anchor="{anchor}" font-weight="{weight}">{s}</text>'

# ------------------------------------------------------------
# VIEW ①  벤드 평면도  (좌측)
# ------------------------------------------------------------
OX, OY = 250, 940     # part 원점(0,0) 위치
outerL = offset_path(+1, True)
outerR = offset_path(-1, True)
boreL  = offset_path(+1, False)
boreR  = offset_path(-1, False)

def poly(pts, ox, oy):
    return " ".join(f"{'M' if i==0 else 'L'} {T_elbow(px,py,ox,oy)[0]:.1f} {T_elbow(px,py,ox,oy)[1]:.1f}" for i,(px,py) in enumerate(pts))

add(f'<g>')
add(label(150, 110, '①  벤드 평면도 (냉기 흐름 단면, +Z 방향 시)', 20, weight="bold"))
# 외벽 실루엣 (닫힌 경로: 좌측 forward + 우측 backward)
outer_all = outerL + outerR[::-1]
add(f'<path d="{poly(outer_all, OX, OY)} Z" {OUT}/>')
# 보어(내벽) — 숨은선
add(f'<path d="{poly(boreL, OX, OY)}" {HID}/>')
add(f'<path d="{poly(boreR, OX, OY)}" {HID}/>')

# 흡입 플랜지 (x:-3..0, y: ±(84))  — 세로 곡면(뒷면) 표시
fy = HU + WALL + FLANGE          # 86.6 ≈ 87 반폭
x0f, x1f = -FLANGE_TH, 0.0
p1 = T_elbow(x1f,  fy, OX, OY); p2 = T_elbow(x0f,  fy, OX, OY)
p3 = T_elbow(x0f, -fy, OX, OY); p4 = T_elbow(x1f, -fy, OX, OY)
add(f'<path d="M {p1[0]:.1f} {p1[1]:.1f} L {p2[0]:.1f} {p2[1]:.1f} L {p3[0]:.1f} {p3[1]:.1f} L {p4[0]:.1f} {p4[1]:.1f} Z" {OUT}/>')
# 볼트 구멍(플랜지) 숨은선 4개
for hy in (HV+WALL+FLANGE/2, -(HV+WALL+FLANGE/2)):
    pass
for hy in (fy-7, -(fy-7)):
    a = T_elbow(x1f, hy, OX, OY); b = T_elbow(x0f, hy, OX, OY)
    add(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" {HID}/>')

# 나사부 표시 (토출 끝 42mm) — 마루/골 crest 라인
bend = math.radians(BEND_DEG)
Ce = (LIP_IN + BEND_R*math.sin(bend), BEND_R*(1-math.cos(bend)))
y_tip = Ce[1] + LIP_OUT
for sgn in (+1, -1):
    xc = Ce[0] + sgn*CREST
    a = T_elbow(xc, y_tip-3, OX, OY); b = T_elbow(xc, y_tip-3-THREAD_LEN, OX, OY)
    add(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#111" stroke-width="1.1" fill="none"/>')
    # crest ticks
    n = int(THREAD_LEN/(THREAD_PITCH/2))
    for i in range(n+1):
        yy = y_tip-3 - i*(THREAD_PITCH/2)
        pa = T_elbow(Ce[0]+sgn*OD, yy, OX, OY); pb = T_elbow(xc, yy-2.5, OX, OY)
        add(f'<line x1="{pa[0]:.1f}" y1="{pa[1]:.1f}" x2="{pb[0]:.1f}" y2="{pb[1]:.1f}" stroke="#111" stroke-width="0.7"/>')

# 센터라인
cl = [(x,y) for (x,y,_,_) in centerline()]
add(f'<path d="{poly(cl, OX, OY)}" {CEN}/>')
# 벤드 중심점 & 반경 R80
cxp = T_elbow(LIP_IN, BEND_R, OX, OY)
midA = math.radians(45)
mcx = LIP_IN + BEND_R*math.sin(midA); mcy = BEND_R*(1-math.cos(midA))
mp = T_elbow(mcx, mcy, OX, OY)
add(f'<line x1="{cxp[0]:.1f}" y1="{cxp[1]:.1f}" x2="{mp[0]:.1f}" y2="{mp[1]:.1f}" {DIM}/>')
add(f'<circle cx="{cxp[0]:.1f}" cy="{cxp[1]:.1f}" r="2.5" fill="#1a5276"/>')
add(dim_txt((cxp[0]+mp[0])/2-6, (cxp[1]+mp[1])/2-6, 'R80', 15, "middle"))

# ---- 치수: 전체 Y 길이(≈390), 전체 X(≈165), 벤드각 90°, LIP_IN 8 ----
# 전체 세로(Y): flange(-fy) ~ tip
ymin = -fy; ymax = y_tip
dimx = OX + 175*S + 118
ta = T_elbow(0, ymax, OX, OY); tb = T_elbow(0, ymin, OX, OY)
add(f'<line x1="{dimx}" y1="{ta[1]:.1f}" x2="{dimx}" y2="{tb[1]:.1f}" {DIM}/>')
for yy in (ymax, ymin):
    p = T_elbow(0, yy, OX, OY)
    add(f'<line x1="{p[0]:.1f}" y1="{p[1]:.1f}" x2="{dimx}" y2="{p[1]:.1f}" {DIM} stroke-dasharray="3,2"/>')
add(f'<polygon points="{dimx-4},{ta[1]+8:.0f} {dimx+4},{ta[1]+8:.0f} {dimx},{ta[1]:.1f}" fill="#1a5276"/>')
add(f'<polygon points="{dimx-4},{tb[1]-8:.0f} {dimx+4},{tb[1]-8:.0f} {dimx},{tb[1]:.1f}" fill="#1a5276"/>')
add(dim_txt(dimx+16, (ta[1]+tb[1])/2, '≈390', 16, "middle", rot=90))

# 토출관 연장 길이 (칼라 LIP_OUT 223)
d2 = OX + (Ce[0]+CREST)*S + 26
pa = T_elbow(Ce[0], Ce[1], OX, OY); pb = T_elbow(Ce[0], y_tip, OX, OY)
add(f'<line x1="{d2}" y1="{pa[1]:.1f}" x2="{d2}" y2="{pb[1]:.1f}" {DIM}/>')
add(f'<polygon points="{d2-4},{pa[1]-8:.0f} {d2+4},{pa[1]-8:.0f} {d2},{pa[1]:.1f}" fill="#1a5276"/>')
add(f'<polygon points="{d2-4},{pb[1]+8:.0f} {d2+4},{pb[1]+8:.0f} {d2},{pb[1]:.1f}" fill="#1a5276"/>')
add(dim_txt(d2+14, (pa[1]+pb[1])/2, '223', 15, "middle", rot=90))

# 나사부 길이 42
d3 = OX + (Ce[0]+CREST)*S + 72
pa = T_elbow(Ce[0], y_tip-3, OX, OY); pb = T_elbow(Ce[0], y_tip-3-THREAD_LEN, OX, OY)
add(f'<line x1="{d3}" y1="{pa[1]:.1f}" x2="{d3}" y2="{pb[1]:.1f}" {DIM}/>')
add(dim_txt(d3+13, (pa[1]+pb[1])/2, '42', 14, "middle", rot=90))

# 90° 벤드각
arcp = T_elbow(LIP_IN, BEND_R, OX, OY)
add(dim_txt(arcp[0]+28, arcp[1]+6, '90°', 16, "start", col="#c0392b"))
# 흡입립 8
p = T_elbow(4, -fy, OX, OY)
add(dim_txt(p[0], p[1]+26, 'LIP 8', 13, "middle"))
# 흡입 폭 표기
p = T_elbow(0, 0, OX, OY)
add(dim_txt(p[0]-40, p[1]+4, '140', 15, "middle", rot=90))
add(f'</g>')

# ------------------------------------------------------------
# VIEW ②  흡입 플랜지면  (우측 상단) — 정면(−X 방향 시)
# ------------------------------------------------------------
def rrect_pts(hu, hv, rc, cx, cy, s, curveflat=False):
    """둥근사각 경로 (Y가로=화면X, Z세로=화면Y)."""
    pts=[]
    corners=[( hu-rc,  hv-rc, 0), (-(hu-rc),  hv-rc, 90),
             (-(hu-rc),-(hv-rc),180), ( hu-rc, -(hv-rc),270)]
    seq=[]
    for (ccx,ccy,a0) in corners:
        for j in range(0,91,15):
            ang=math.radians(a0+j)
            seq.append((ccx+rc*math.cos(ang), ccy+rc*math.sin(ang)))
    for (yy,zz) in seq:
        pts.append((cx+yy*s, cy-zz*s))
    return pts
def path_of(pts):
    return " ".join(f"{'M' if i==0 else 'L'} {x:.1f} {y:.1f}" for i,(x,y) in enumerate(pts))+" Z"

CX2, CY2, s2 = 1180, 315, 1.95
add(label(CX2, 150, '②  흡입 플랜지면  (에어컨 밀착측)', 20, "middle", weight="bold"))
# 플랜지 외곽
add(f'<path d="{path_of(rrect_pts(HU+WALL+FLANGE, HV+WALL+FLANGE, FLANGE_R+FLANGE, CX2, CY2, s2))}" {OUT}/>')
# 스커트 외곽(흡입 사각 140x80 + wall)
add(f'<path d="{path_of(rrect_pts(HU+WALL, HV+WALL, CORNER_R+WALL, CX2, CY2, s2))}" {OUT}/>')
# 보어 140x80 R20 (개구)
add(f'<path d="{path_of(rrect_pts(HU, HV, CORNER_R, CX2, CY2, s2))}" {HID}/>')
# 볼트홀 4개 (Ø4.5) — 네 변 중앙
holes=[(0, HV+WALL+FLANGE/2), (0, -(HV+WALL+FLANGE/2)),
       (HU+WALL+FLANGE/2, 0), (-(HU+WALL+FLANGE/2), 0)]
for (hy,hz) in holes:
    hx=CX2+hy*s2; hyy=CY2-hz*s2
    add(f'<circle cx="{hx:.1f}" cy="{hyy:.1f}" r="{HOLE_D/2*s2:.1f}" {THN}/>')
    add(f'<line x1="{hx-8:.1f}" y1="{hyy:.1f}" x2="{hx+8:.1f}" y2="{hyy:.1f}" {CEN}/>')
    add(f'<line x1="{hx:.1f}" y1="{hyy-8:.1f}" x2="{hx:.1f}" y2="{hyy+8:.1f}" {CEN}/>')
# 센터라인
add(f'<line x1="{CX2-(HU+WALL+FLANGE+10)*s2:.1f}" y1="{CY2}" x2="{CX2+(HU+WALL+FLANGE+10)*s2:.1f}" y2="{CY2}" {CEN}/>')
add(f'<line x1="{CX2}" y1="{CY2-(HV+WALL+FLANGE+10)*s2:.1f}" x2="{CX2}" y2="{CY2+(HV+WALL+FLANGE+10)*s2:.1f}" {CEN}/>')
# 치수 140(가로), 80(세로), 플랜지폭
yb = CY2 + (HV+WALL+FLANGE)*s2 + 34
xa=CX2-HU*s2; xb=CX2+HU*s2
add(f'<line x1="{xa:.1f}" y1="{yb}" x2="{xb:.1f}" y2="{yb}" {DIM}/>')
add(f'<polygon points="{xa+8:.0f},{yb-4} {xa+8:.0f},{yb+4} {xa:.1f},{yb}" fill="#1a5276"/>')
add(f'<polygon points="{xb-8:.0f},{yb-4} {xb-8:.0f},{yb+4} {xb:.1f},{yb}" fill="#1a5276"/>')
add(dim_txt(CX2, yb+18, '140 (흡입 가로)', 15, "middle"))
xr = CX2 + (HU+WALL+FLANGE)*s2 + 34
za=CY2-HV*s2; zb=CY2+HV*s2
add(f'<line x1="{xr}" y1="{za:.1f}" x2="{xr}" y2="{zb:.1f}" {DIM}/>')
add(f'<polygon points="{xr-4},{za+8:.0f} {xr+4},{za+8:.0f} {xr},{za:.1f}" fill="#1a5276"/>')
add(f'<polygon points="{xr-4},{zb-8:.0f} {xr+4},{zb-8:.0f} {xr},{zb:.1f}" fill="#1a5276"/>')
add(dim_txt(xr+16, CY2, '80', 15, "middle", rot=90))
# R20 지시선 (좌상단 코너 밖으로)
rc_x = CX2-(HU-CORNER_R)*s2 - CORNER_R*s2*0.7; rc_y = CY2-(HV-CORNER_R)*s2 - CORNER_R*s2*0.7
add(f'<line x1="{rc_x:.1f}" y1="{rc_y:.1f}" x2="{CX2-(HU+WALL+FLANGE)*s2-30:.1f}" y2="{CY2-(HV+WALL+FLANGE)*s2-6:.1f}" {DIM}/>')
add(dim_txt(CX2-(HU+WALL+FLANGE)*s2-34, CY2-(HV+WALL+FLANGE)*s2-10, 'R20', 14, "end", col="#111"))
add(label(CX2+(HU+WALL+FLANGE)*s2+14, CY2-(HV+WALL+FLANGE)*s2-2, '4× ⌀4.5 (4변 중앙)', 14, "start", col="#111"))
add(dim_txt(CX2, yb+40, '플랜지폭 14 · 외곽 R10 · 벽 스커트 t2.6', 13, "middle", col="#111"))

# ------------------------------------------------------------
# VIEW ③  토출 단면  (우측 중단) — +Y 방향 시
# ------------------------------------------------------------
CX3, CY3, s3 = 1075, 705, 1.95
add(label(CX3, 560, '③  토출 단면  (호스 체결측)', 20, "middle", weight="bold"))
add(f'<circle cx="{CX3}" cy="{CY3}" r="{CREST*s3:.1f}" {OUT}/>')                 # 나사 마루 Ø151
add(f'<circle cx="{CX3}" cy="{CY3}" r="{OD*s3:.1f}" stroke="#111" stroke-width="1" fill="none" stroke-dasharray="2,3"/>')  # 나사 골(칼라외경) Ø147.2
add(f'<circle cx="{CX3}" cy="{CY3}" r="{R*s3:.1f}" {OUT}/>')                     # 보어 Ø142
add(f'<line x1="{CX3-(CREST+12)*s3:.1f}" y1="{CY3}" x2="{CX3+(CREST+12)*s3:.1f}" y2="{CY3}" {CEN}/>')
add(f'<line x1="{CX3}" y1="{CY3-(CREST+12)*s3:.1f}" x2="{CX3}" y2="{CY3+(CREST+12)*s3:.1f}" {CEN}/>')
# 지시선: 보어 Ø142
ang=math.radians(35)
p1=(CX3+R*s3*math.cos(ang), CY3-R*s3*math.sin(ang)); p2=(CX3+(CREST+60)*s3*0.55+40, CY3-(CREST+40)*s3*0.55)
add(f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" y2="{p2[1]:.1f}" {DIM}/>')
add(dim_txt(p2[0]+4, p2[1]-2, '⌀142 (보어)', 15, "start"))
# 나사 마루 Ø151
ang=math.radians(150)
q1=(CX3+CREST*s3*math.cos(ang), CY3-CREST*s3*math.sin(ang)); q2=(CX3-(CREST+50)*s3*0.6-10, CY3-(CREST+35)*s3*0.6)
add(f'<line x1="{q1[0]:.1f}" y1="{q1[1]:.1f}" x2="{q2[0]:.1f}" y2="{q2[1]:.1f}" {DIM}/>')
add(dim_txt(q2[0]-4, q2[1]-2, '⌀151 나사마루', 15, "end"))
# 나사 골 Ø147
ang=math.radians(-40)
r1=(CX3+OD*s3*math.cos(ang), CY3-OD*s3*math.sin(ang)); r2=(CX3+(CREST+45)*s3*0.6+30, CY3+(CREST+30)*s3*0.6)
add(f'<line x1="{r1[0]:.1f}" y1="{r1[1]:.1f}" x2="{r2[0]:.1f}" y2="{r2[1]:.1f}" {DIM}/>')
add(dim_txt(r2[0]+4, r2[1]+4, '⌀147.2 골', 14, "start"))
add(label(CX3, CY3+(CREST)*s3+34, '외부 수나사  P15 · 2줄 · L42  (Ø150 호스 체결)', 15, "middle", col="#111"))

# ------------------------------------------------------------
#  벽 두께 상세 (DETAIL)  — 우측, 토출 단면 아래
# ------------------------------------------------------------
DX, DY = 1340, 640
add(label(DX, DY-18, '단면 상세 (벽두께)', 16, "start", weight="bold"))
add(f'<rect x="{DX}" y="{DY}" width="150" height="34" fill="#dfe9f2" stroke="#111" stroke-width="1.5"/>')
add(f'<line x1="{DX}" y1="{DY}" x2="{DX+150}" y2="{DY}" stroke="#111" stroke-width="2"/>')
add(f'<line x1="{DX}" y1="{DY+34}" x2="{DX+150}" y2="{DY+34}" stroke="#111" stroke-width="2"/>')
add(dim_txt(DX+75, DY+56, 'WALL 2.6  (벽 3줄↑ 권장)', 14, "middle", col="#111"))
add(dim_txt(DX+165, DY+21, 't2.6', 13, "start"))

# ============================================================
# 표제란 (TITLE BLOCK)  — 우측 하단
# ============================================================
TBx, TBy, TBw = 815, 964, 826
rows = [
    ("품명 / PART", "냉기 유도 덕트 (90° 벤드 어댑터)"),
    ("용도", "신일 창문형 에어컨 냉기토출면 밀착 → Ø150 호스 유도"),
    ("전체치수", "≈ 178 (X) × 390 (Y) × 151 (Z) mm"),
    ("흡입 / 토출", "사각 140×80 R20  →  원통 보어 ⌀142"),
    ("벤드 / 나사", "센터라인 R80, 90°  ·  외부수나사 ⌀151 P15 2줄 L42"),
    ("벽두께 / 재질", "2.6 mm  ·  PETG(내열·내습) 권장, 채움 15%↑"),
    ("공차 / 단위", "일반공차 ±0.5, 실측 후 ±1~2 여유  ·  단위 mm"),
    ("출처 세션", "claude/ac-noise-duct-3d-fzpgaq  (cold_air_duct)"),
]
rh = 25
add(f'<rect x="{TBx}" y="{TBy}" width="{TBw}" height="{rh*len(rows)+34}" fill="none" stroke="#111" stroke-width="2"/>')
add(f'<rect x="{TBx}" y="{TBy}" width="{TBw}" height="34" fill="#111"/>')
add(label(TBx+14, TBy+23, '2D 제작 도면  ·  COLD-AIR GUIDE DUCT', 18, "start", col="#fff", weight="bold"))
for i,(k,v) in enumerate(rows):
    yy = TBy+34+i*rh
    add(f'<line x1="{TBx}" y1="{yy}" x2="{TBx+TBw}" y2="{yy}" {THN}/>')
    add(f'<line x1="{TBx+150}" y1="{yy}" x2="{TBx+150}" y2="{yy+rh}" {THN}/>')
    add(label(TBx+12, yy+18, k, 13, "start", col="#1a5276", weight="bold"))
    add(label(TBx+160, yy+18, v, 13, "start", col="#111"))

# 주기 (NOTES) — 좌하단
NX, NY = 70, 992
notes = [
    "NOTES",
    "1. 치수 단위 mm. 인쇄 전 에어컨 실토출구를 실측해",
    "   흡입 140×80·⌀142 를 맞출 것 (+1~2 여유).",
    "2. 외부 수나사(⌀151, P15, 2줄, 끝단 L42)에",
    "   Ø150 유연호스/커넥터를 돌려 체결.",
    "3. 접촉(뒷)면은 세로 아래 1/3부터 R≈250 곡면 —",
    "   에어컨 몸체 밀착 (상단 새그 ~11.7).",
    "4. 원본: generate_stl.py / cold_air_duct.scad / *_viewer.html.",
]
add(f'<rect x="{NX-12}" y="{NY-22}" width="700" height="{len(notes)*22+12}" fill="#f7f9fb" stroke="#111" stroke-width="1"/>')
for i,n in enumerate(notes):
    add(label(NX, NY+i*22, n, 15 if i==0 else 13, "start", col="#111", weight="bold" if i==0 else "normal"))

add('</svg>')
open('/tmp/claude-0/-home-user-maestro/ed04640d-d12e-515b-a905-79644e8ff930/scratchpad/cold_air_duct_2d.svg','w').write("\n".join(svg))
print("SVG written")
