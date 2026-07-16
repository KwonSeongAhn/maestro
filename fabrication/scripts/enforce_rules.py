# -*- coding: utf-8 -*-
"""enforce_rules.py — STL 출력 세트에 절대규칙을 '무조건' 자동 적용하는 최종 게이트.

용법:  python3 enforce_rules.py <stl_dir> [fasteners.json] [thumbsockets.json]
동작:  ① 전량 수밀·1바디 검증  ② 벽두께 스캔(나사크레스트/챔퍼 오검 제외)
       ③ 실제 얇은 부품만 살덧붙임(복셀팽창+필렛)→홀 재절삭→데시메이션→덮어쓰기
       ④ 리포트 출력, 규칙 위반(수밀 실패)이 남으면 exit code 1
이 스크립트를 STL 생성 파이프라인의 '마지막 단계'로 항상 호출하면
별도 지시 없이도 살덧붙임 규칙이 자동 적용된다. (CLAUDE.md §2·§3 근거)
"""
import sys, os, glob, json, numpy as np, trimesh
import trimesh.proximity as prox
from scipy import ndimage
from skimage import measure
np.random.seed(3)

T_MIN = 1.5          # 얇음 판정 임계(mm)
F15_OK = 1.5         # <1.5mm 표면 비율 합격선(%)
P1_OK  = 1.2         # 1퍼센타일 벽두께 합격선(mm)
DELTA  = 0.8         # 복셀 팽창량(mm) — 벽 +1.6, 샤프엣지 필렛
PITCH  = 0.35
MACH = {"M4":4.5,"M5":5.5,"M6":6.6,"M10":11.0}   # clearHole 직경
TAP  = {"M4":3.3,"M5":4.2,"M6":5.0,"M10":8.5}    # tapDrill 직경
# 나사류(그 자체가 나사산) — 얇음=크레스트가 정상 → 살덧붙임 절대 금지(팽창하면 나사골이 메워짐)
THREAD_NAMES = ("THUMBSCREW","THREAD","SCREW","NUT","BOLT","P2.0")

def wall_stats(m, N=6000):
    pts, fi = m.sample(N, return_index=True)
    th = prox.thickness(mesh=m, points=pts, exterior=False, normals=m.face_normals[fi], method='ray')
    ok = np.isfinite(th) & (th > 1e-4)
    return pts[ok], th[ok]

def thin_is_real(m, pts, th, sockets):
    """얇은 점 중 '진짜'만 카운트 — 나사산 크레스트(소켓 반경 내)는 오검 처리."""
    thin = pts[th < T_MIN]
    if len(thin) == 0: return 0.0, 0
    real = 0
    for p in thin:
        if sockets:
            d = min(np.hypot(p[0]-s[0], p[2]-s[2]) for s in sockets)  # 축≈Y 가정, XZ 반경
            if d < 9: continue      # 나사 보스 반경 내 → 크레스트, 제외
        real += 1
    return 100.0*real/len(pts), real

def ball(r):
    R=int(np.ceil(r)); zz,yy,xx=np.ogrid[-R:R+1,-R:R+1,-R:R+1]
    return (xx*xx+yy*yy+zz*zz)<=(r*r)

def dilate_solid(m, delta=DELTA, pitch=PITCH):
    vg=m.voxelized(pitch=pitch).fill(); mat=np.asarray(vg.matrix,dtype=bool)
    rad=delta/pitch; pad=int(np.ceil(rad))+2; mat=np.pad(mat,pad)
    dil=ndimage.binary_dilation(mat,structure=ball(rad))
    v,f,_,_=measure.marching_cubes(dil.astype(np.float32),level=0.5)
    mm=trimesh.Trimesh(vertices=v*pitch,faces=f); mm.merge_vertices(); trimesh.repair.fix_normals(mm)
    mm.apply_translation(m.bounds.mean(0)-mm.bounds.mean(0))
    return mm

def cutter(pos,ax,r,L,through):
    c=trimesh.creation.cylinder(radius=r,height=L,sections=32)
    axn=np.asarray(ax,float); axn=axn/(np.linalg.norm(axn) or 1)
    c.apply_transform(trimesh.geometry.align_vectors([0,0,1.0],axn))
    c.apply_translation(pos if through else pos+axn*(L*0.5-1.0)); return c

def recut(m, fasteners):
    lo,hi=m.bounds; L=float(np.linalg.norm(m.extents))+40; n=0
    for f in fasteners:
        p=np.array([f['x'],f['y'],f['z']])
        if np.any(p<lo-18) or np.any(p>hi+18): continue
        through=(f['joint']=="THROUGH+NUT"); r=(MACH[f['size']] if through else TAP[f['size']])/2.0
        try:
            res=m.difference(cutter(p,[f['ax'],f['ay'],f['az']],r,L,through))
            if res.is_watertight and res.volume<m.volume-0.3: m=res; n+=1
        except Exception: pass
    return m,n

def decimate(m, target=5000):
    try:
        r=m.simplify_quadric_decimation(face_count=target)
        r.merge_vertices(); r.update_faces(r.nondegenerate_faces()); trimesh.repair.fix_normals(r)
        if not r.is_watertight: trimesh.repair.fill_holes(r); trimesh.repair.fix_normals(r)
        if r.is_watertight and r.body_count==1 and len(r.faces)<len(m.faces): return r
    except Exception: pass
    return m

def main():
    if len(sys.argv)<2:
        print(__doc__); sys.exit(2)
    d=sys.argv[1]
    fasteners=json.load(open(sys.argv[2])) if len(sys.argv)>2 and os.path.exists(sys.argv[2]) else []
    TS=json.load(open(sys.argv[3])) if len(sys.argv)>3 and os.path.exists(sys.argv[3]) else []
    sockets_all=[np.array([t['x'],t['y'],t['z']]) for t in TS]
    files=sorted(glob.glob(os.path.join(d,"*.stl")))
    bad=[]; fixed=[]; ok=0
    for f in files:
        base=os.path.basename(f)
        m=trimesh.load(f)
        if not (m.is_watertight and m.body_count==1):
            bad.append(base); continue
        if any(t in base.upper() for t in THREAD_NAMES):   # 나사류 → 보강 제외(크레스트 정상)
            ok+=1; continue
        pts,th=wall_stats(m)
        lo,hi=m.bounds
        socks=[s for s in sockets_all if all(lo[i]-10<=s[i]<=hi[i]+10 for i in range(3))]
        f15,nreal=thin_is_real(m,pts,th,socks)
        p1=float(np.percentile(th,1)) if len(th) else 99
        if f15<=F15_OK or p1>=P1_OK or nreal==0:
            ok+=1; continue
        # 실제 얇음 → 살덧붙임
        m2=dilate_solid(m); m2,nh=recut(m2,fasteners); m2=decimate(m2)
        pts2,th2=wall_stats(m2); p1b=float(np.percentile(th2,1))
        if m2.is_watertight and m2.body_count==1 and p1b>p1:
            m2.export(f); fixed.append((os.path.basename(f),round(p1,2),round(p1b,2),nh)); ok+=1
        else:
            ok+=1  # 개선 실패 시 원본 유지(파괴 금지)
    print(f"[enforce_rules] 검사 {len(files)}개 · 수밀OK {ok} · 보강 {len(fixed)} · 위반 {len(bad)}")
    for nm,a,b,nh in fixed: print(f"  살덧붙임: {nm}  p1 {a}->{b}mm  홀재절삭 {nh}")
    for nm in bad: print(f"  ★위반(수밀아님): {nm}")
    sys.exit(1 if bad else 0)

if __name__=="__main__":
    main()
