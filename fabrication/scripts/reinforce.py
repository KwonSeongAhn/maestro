# -*- coding: utf-8 -*-
"""살덧붙임 규칙 구현 — 얇은 구간(<t_target) 검출 → 외측 살 추가(보강) → 최소벽 확보 (참조: cold_air_duct)."""
import trimesh, numpy as np, json, os, shutil
import trimesh.proximity as prox
np.random.seed(7)

def thin_points(m, t_target, N=1500):
    pts,fi=m.sample(N,return_index=True); nrm=m.face_normals[fi]
    th=prox.thickness(mesh=m,points=pts,exterior=False,normals=nrm,method='ray')
    ok=np.isfinite(th)&(th>1e-3)
    mask=ok&(th<t_target)
    return pts[mask],nrm[mask],th[mask]

def cluster(pts, cell=3.0):
    if len(pts)==0: return pts
    key=np.round(pts/cell).astype(int)
    _,idx=np.unique(key,axis=0,return_index=True)
    return pts[np.sort(idx)]

def reinforce(m, t_target=2.5, iters=4):
    hist=[]
    for it in range(iters):
        tp,tn,tt=thin_points(m,t_target)
        if len(tp)==0: break
        # 대표점 클러스터 + 대응 법선/두께 (가까운 원본점)
        cp=cluster(tp, cell=3.0)
        # 각 대표점의 법선·두께 = 최근접 thin point
        from scipy.spatial import cKDTree
        tree=cKDTree(tp); d,ii=tree.query(cp)
        blobs=[]
        for p,n,t in zip(cp, tn[ii], tt[ii]):
            r=float(max(1.0,(t_target - t)*0.75 + 0.6))     # 부족분 + 여유
            c=p + n*(r - t*0.5)                              # 외측으로 밀어 벽 외면에 살 추가
            s=trimesh.creation.icosphere(subdivisions=1,radius=r); s.apply_translation(c); blobs.append(s)
        add=trimesh.util.concatenate(blobs)
        try:
            m2=m.union(add)
            if m2.is_watertight: m=m2
        except Exception: pass
        hist.append(len(cp))
    return m, hist

if __name__=="__main__":
    SP="/tmp/claude-0/-home-user-maestro/89feb1d7-5414-58cf-b499-d60f30aed29c/scratchpad"
    man=json.load(open(f"{SP}/parts_final3/parts_manifest.json"))
    targets=["P32","P23","P30"]
    for p in targets:
        x=[a for a in man if a["part"]==p][0]
        m=trimesh.load(f"{SP}/parts_final3/"+x["file"])
        tp,_,tt=thin_points(m,2.5); before=float(np.min(tt)) if len(tt) else 99
        m2,hist=reinforce(m, t_target=2.5, iters=4)
        # after
        pts,fi=m2.sample(1500,return_index=True)
        th=prox.thickness(mesh=m2,points=pts,exterior=False,normals=m2.face_normals[fi],method='ray')
        th=th[np.isfinite(th)&(th>1e-3)]
        print(f"{p}: before p1={before:.2f} -> after p1={np.percentile(th,1):.2f} min={th.min():.2f} wt={m2.is_watertight} addedIters={hist} dVol={m2.volume-m.volume:.0f}")
        m2.export(f"{SP}/parts_final3/{x['file']}")  # 덮어쓰기(보강 반영)
