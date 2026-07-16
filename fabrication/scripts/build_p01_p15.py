# -*- coding: utf-8 -*-
"""P01(박스 슬리브 + 원뿔 반깔대기 2부품) · P15(튜브) 파라메트릭 재구성 (솔리드+홀)."""
import numpy as np, trimesh, os, json

OUT="/tmp/claude-0/-home-user-maestro/89feb1d7-5414-58cf-b499-d60f30aed29c/scratchpad/recon"
os.makedirs(OUT, exist_ok=True)

def box(sx,sy,sz,cx=0,cy=0,cz=0):
    b=trimesh.creation.box((sx,sy,sz)); b.apply_translation([cx,cy,cz]); return b

# ================= P01a : 4각 박스 슬리브 (버킷함) =================
# 코드: slvXhalf50(폭100), slvT3, 하단(-Y)·후단(+Z) 개방, 상판 중앙 버킷 슬롯, R6 필렛
# 월드 배치(추출): X±50.5, Y1388~1498, Z-1551~-1409 (center 0,1443,-1480; ext 101x110x142)
def build_box_sleeve():
    X=101.0; Y=110.0; Z=142.0; t=3.0
    cx,cy,cz=0.0,1443.0,-1480.0
    outer=box(X,Y,Z,cx,cy,cz)
    # 캐비티: 하단(-Y)·후단(+Z) 개방 → 그 방향으로 여유 확장, L/R/전면/상면은 t 인셋
    inner=box(X-2*t, Y+40, Z, cx, cy-20, cz+t/2+20)   # -Y로 40 확장(하단 개방), +Z로 확장(후단 개방), 전면 t 유지
    # 위 inner는 상면도 열어버림 → 상면 t 유지 위해 상단 t 다시 채움? 대신 inner를 상단 t만큼 낮춤
    inner=box(X-2*t, Y-t, Z+40, cx, cy-20-t/2, cz+20)  # 상면 t 남김, 하단+후단 개방
    shell=outer.difference(inner)
    # 상판 중앙 버킷 슬롯 (|x|<31, 후방 절반 관통)
    slot=box(62, Y+20, Z*0.62, cx, cy, cz+Z*0.19)
    shell=shell.difference(slot)
    shell.apply_translation([0,0,0])
    return shell

# ================= P01b : 원뿔 반깔대기 (토출부) =================
# 코드: mouthR44 → cylR22.5, wallT2.5, bore21.5, L~102, 축(0,-0.068,0.998), center(0,1393,-1580)
def _solid_frustum(r0,r1,L):
    prof=np.array([[0.0,0.0],[r0,0.0],[r1,L],[0.0,L]])   # 축에 닫힌 프로파일 → 수밀 솔리드
    m=trimesh.creation.revolve(prof, sections=64)
    m.merge_vertices(); trimesh.repair.fix_normals(m); return m
def build_funnel():
    mouthR=44.0; neckR=22.5; wall=2.5; L=100.0
    outer=_solid_frustum(mouthR,neckR,L)
    inner=_solid_frustum(mouthR-wall,neckR-wall,L)   # 동일 L → 양단 보어 개방
    m=outer.difference(inner)
    if not m.is_watertight: m.merge_vertices(); trimesh.repair.fill_holes(m); trimesh.repair.fix_normals(m)
    # 축 정렬: z축 → (0,-0.068,0.998), center(0,1393,-1580)로 이동 (revolve는 z=0~L, 중앙 배치)
    ax=np.array([0,-0.068,0.998]); ax=ax/np.linalg.norm(ax)
    m.apply_transform(trimesh.geometry.align_vectors([0,0,1.0],ax))
    m.apply_translation(np.array([0,1393,-1580]) - m.centroid)
    return m

# ================= P15 : 튜브 Ø60 (드롭/니플 계열) =================
# 추출: ext 60x32x60, 축 Y(높이32), center(-66,925,-2043). 튜브 OD60 ID54 H32
def build_tube():
    od=60.0; idd=54.0; h=32.0
    o=trimesh.creation.cylinder(radius=od/2,height=h,sections=48)
    i=trimesh.creation.cylinder(radius=idd/2,height=h+4,sections=48)
    t=o.difference(i)
    t.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]))  # 축 Z→Y
    t.apply_translation([-66,925,-2043])
    return t

parts={"P01a_box_sleeve":build_box_sleeve(),
       "P01b_funnel":build_funnel(),
       "P15_tube":build_tube()}
for name,m in parts.items():
    ok=m.is_watertight
    m.export(f"{OUT}/{name}.stl")
    print(f"{name}: watertight={ok} vol={m.volume:.0f} faces={len(m.faces)} extents={np.round(m.extents,1)}")
