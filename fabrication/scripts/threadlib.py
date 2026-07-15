# -*- coding: utf-8 -*-
"""ISO 미터 나사산 생성 (외나사 로드 / 내나사 절삭툴) + 섬스크류·너트."""
import numpy as np, trimesh

# ===== 3D 프린트용 굵은 나사 표준 (금속 M5=0.8 대비 넓게) =====
PR_PITCH = 2.0     # mm — 프린트용 굵은 피치
PR_DEPTH = 0.9     # mm — 나사산 반경 깊이 (피치와 분리, 코어 강도 확보)
PR_MAJOR = 5.0     # mm — 외경 (기존 Ø5 소켓 정합)
PR_FLAT  = 0.18    # 크레스트/루트 평탄화 비율 (사다리꼴)
PR_CLEAR = 0.40    # 너트/소켓 내나사 체결 여유 (major 증분)

def ext_thread(major, pitch, length, depth=PR_DEPTH, flat=PR_FLAT, NT=96, seg_z=20):
    """외나사 로드 = 원통 높이필드 r(theta,z) (자기교차 없는 watertight). 사다리꼴 프로파일."""
    minor_r=max(0.6, major/2.0 - depth)
    th=major/2.0 - minor_r
    NZ=max(4,int(round((length/pitch)*seg_z)))
    verts=[]; ring=np.zeros((NZ+1,NT),dtype=int); vi=0
    for j in range(NZ+1):
        z=length*j/NZ
        for i in range(NT):
            ang=2*np.pi*i/NT
            phi=((z/pitch)-(ang/(2*np.pi)))%1.0
            tri=1.0-abs(2.0*phi-1.0)            # 삼각파 0→1→0
            trap=min(1.0,max(0.0,(tri-flat)/(1.0-2.0*flat)))   # 사다리꼴(평탄 크레스트/루트)
            r=minor_r+th*trap
            verts.append([r*np.cos(ang),r*np.sin(ang),z]); ring[j,i]=vi; vi+=1
    cb=vi; verts.append([0,0,0.0]); vi+=1
    ct=vi; verts.append([0,0,length]); vi+=1
    faces=[]
    for j in range(NZ):
        for i in range(NT):
            a=ring[j,i]; b=ring[j,(i+1)%NT]; c=ring[j+1,(i+1)%NT]; d=ring[j+1,i]
            faces += [[a,b,c],[a,c,d]]
    for i in range(NT):                          # 바닥/상단 캡
        faces.append([cb, ring[0,(i+1)%NT], ring[0,i]])
        faces.append([ct, ring[NZ,i], ring[NZ,(i+1)%NT]])
    m=trimesh.Trimesh(vertices=np.array(verts),faces=np.array(faces),process=True)
    m.fix_normals()
    return m

def thumbscrew(major=PR_MAJOR,pitch=PR_PITCH,thread_len=10.0,head_d=12.0,head_h=6.0,facets=18):
    """통일 섬스크류: 프린트용 굵은 나사부 전체 + PEEK 널링(18각) 헤드."""
    rod=ext_thread(major,pitch,thread_len)
    head=trimesh.creation.cylinder(radius=head_d/2.0,height=head_h,sections=facets)
    head.apply_translation([0,0,thread_len+head_h/2.0])
    neck=trimesh.creation.cylinder(radius=major/2.0,height=1.4,sections=24)
    neck.apply_translation([0,0,thread_len+0.7])
    m=rod.union(neck).union(head)
    return m

def internal_thread_cut(major=PR_MAJOR,pitch=PR_PITCH,depth_len=12.0,clear=PR_CLEAR):
    """소켓/너트에 뺄 내나사 절삭툴 (동일 나사산 + 체결여유)."""
    cutter=ext_thread(major+clear,pitch,depth_len)
    cutter.apply_translation([0,0,-1.0])
    return cutter

def hex_nut(major=PR_MAJOR,pitch=PR_PITCH,af=8.5,height=6.0,clear=PR_CLEAR):
    """내나사 육각 너트 (동일 굵은 나사산). af=대변거리."""
    r_out=af/np.sqrt(3.0)
    body=trimesh.creation.cylinder(radius=r_out,height=height,sections=6)
    body.apply_translation([0,0,height/2.0])
    nut=body.difference(internal_thread_cut(major,pitch,height+2.0,clear))
    return nut

if __name__=="__main__":
    import os
    OUT="/tmp/claude-0/-home-user-maestro/89feb1d7-5414-58cf-b499-d60f30aed29c/scratchpad/stl_thread"
    os.makedirs(OUT,exist_ok=True)
    ts=thumbscrew()
    nut=hex_nut()
    for name,m in [("thumbscrew_M5",ts),("nut_M5",nut)]:
        m.export(f"{OUT}/{name}.stl")
        print(f"{name}: watertight={m.is_watertight} vol={m.volume:.1f}mm3 tris={len(m.faces)} bbox={np.round(m.extents,1)}")
