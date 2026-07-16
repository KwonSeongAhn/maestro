# -*- coding: utf-8 -*-
"""살덧붙임 규칙(v2) — 복셀 팽창(민코프스키 오프셋 = 살 추가 + 샤프엣지 필렛)
   후 실계측 홀 재절삭. 참조 품질: cold_air_duct_fused(수밀 1바디, 균일벽, 필렛)."""
import json, numpy as np, trimesh
from scipy import ndimage
from skimage import measure
import trimesh.proximity as prox
np.random.seed(3)
SP="/tmp/claude-0/-home-user-maestro/89feb1d7-5414-58cf-b499-d60f30aed29c/scratchpad"

def ball(r):
    R=int(np.ceil(r)); zz,yy,xx=np.ogrid[-R:R+1,-R:R+1,-R:R+1]
    return (xx*xx+yy*yy+zz*zz)<=(r*r)

def dilate_solid(m, delta=0.8, pitch=0.35):
    """m을 delta 만큼 외측 균일 팽창 → 벽 +2·delta, 샤프엣지 라운딩(필렛). 위치는 중심 정렬로 보존."""
    vg=m.voxelized(pitch=pitch).fill()
    mat=np.asarray(vg.matrix,dtype=bool)
    rad=delta/pitch
    pad=int(np.ceil(rad))+2
    mat=np.pad(mat,pad)
    dil=ndimage.binary_dilation(mat,structure=ball(rad))
    v,f,_,_=measure.marching_cubes(dil.astype(np.float32),level=0.5)
    mm=trimesh.Trimesh(vertices=v*pitch,faces=f); mm.merge_vertices(); trimesh.repair.fix_normals(mm)
    mm.apply_translation(m.bounds.mean(0)-mm.bounds.mean(0))   # 중심 정렬 → 원위치 보존
    return mm

def cutter(pos,ax,r,L,through):
    c=trimesh.creation.cylinder(radius=r,height=L,sections=32)
    axn=np.asarray(ax,float); axn=axn/(np.linalg.norm(axn) or 1)
    c.apply_transform(trimesh.geometry.align_vectors([0,0,1.0],axn))
    c.apply_translation(pos if through else pos+axn*(L*0.5-1.0)); return c

def wall_stats(m,N=6000):
    pts,fi=m.sample(N,return_index=True)
    th=prox.thickness(mesh=m,points=pts,exterior=False,normals=m.face_normals[fi],method='ray')
    th=th[np.isfinite(th)&(th>1e-4)]
    return dict(p1=float(np.percentile(th,1)),p5=float(np.percentile(th,5)),
                med=float(np.percentile(th,50)),f15=float(100*np.mean(th<1.5)))

F=json.load(open(f"{SP}/fasteners.json"))
MACH={"M4":4.5,"M5":5.5,"M6":6.6,"M10":11.0}  # clearHole dia
TAP ={"M4":3.3,"M5":4.2,"M6":5.0,"M10":8.5}

def recut(m, delta_margin=18):
    lo,hi=m.bounds; L=float(np.linalg.norm(m.extents))+40; n=0
    for f in F:
        p=np.array([f['x'],f['y'],f['z']])
        if np.any(p<lo-delta_margin) or np.any(p>hi+delta_margin): continue
        through=(f['joint']=="THROUGH+NUT")
        r=(MACH[f['size']] if through else TAP[f['size']])/2.0
        try:
            res=m.difference(cutter(p,[f['ax'],f['ay'],f['az']],r,L,through))
            if res.is_watertight and res.volume<m.volume-0.3: m=res; n+=1
        except Exception: pass
    return m,n

if __name__=="__main__":
    fn="P32_qty1_6x76x76_PEEK_h4_ts0.stl"
    m0=trimesh.load(f"{SP}/parts_final3/{fn}")
    b=wall_stats(m0)
    print("P32 BEFORE:",{k:round(v,2) for k,v in b.items()},"ext",np.round(m0.extents,2).tolist())
    m1=dilate_solid(m0, delta=0.8, pitch=0.35)
    m2,nh=recut(m1)
    a=wall_stats(m2)
    print("P32 AFTER :",{k:round(v,2) for k,v in a.items()},"ext",np.round(m2.extents,2).tolist(),
          "recut_holes",nh,"wt",m2.is_watertight,"bodies",m2.body_count)
    if m2.is_watertight and a['p1']>b['p1'] and nh==4:
        m2.export(f"{SP}/parts_final3/{fn}"); print("EXPORTED (reinforced).")
    else:
        print("NOT exported — condition failed, original kept.")
