# -*- coding: utf-8 -*-
"""최종: 솔리드화 + SHCS 홀(관통/블라인드탭) + 섬스크류 소켓 P2.0 암나사."""
import json, glob, os, shutil, numpy as np, trimesh
import threadlib

SP="/tmp/claude-0/-home-user-maestro/89feb1d7-5414-58cf-b499-d60f30aed29c/scratchpad"
RAW=f"{SP}/parts/raw"; OUT=f"{SP}/parts_final2"
if os.path.exists(OUT): shutil.rmtree(OUT)
os.makedirs(OUT)
Fj=json.load(open(f"{SP}/fasteners.json"))
TS=json.load(open(f"{SP}/thumbsockets.json"))
rawmeta=json.load(open(f"{SP}/parts/raw_meta.json")); meta={m["file"]:m for m in rawmeta["meta"]}; thumb=rawmeta["thumbCount"]
MACH={"M4":(4.5,3.3,6),"M5":(5.5,4.2,7.5),"M6":(6.6,5.0,9),"M10":(11.0,8.5,15)}
FAST=[]
for f in Fj:
    ch,td,mtd=MACH[f["size"]]
    FAST.append(dict(pos=np.array([f["x"],f["y"],f["z"]]),ax=np.array([f["ax"],f["ay"],f["az"]]),
                     r=(ch if f["joint"]=="THROUGH+NUT" else td)/2.0, through=(f["joint"]=="THROUGH+NUT"),
                     depth=mtd, size=f["size"]))
SOCK=[dict(pos=np.array([t["x"],t["y"],t["z"]]),ax=np.array([t["ax"],t["ay"],t["az"]])) for t in TS]

def solidify(m):
    """얇은 셸 → 수밀 솔리드화 시도."""
    if m.is_watertight: return m,"solid"
    mm=m.copy(); mm.merge_vertices(); mm.update_faces(mm.nondegenerate_faces()); trimesh.repair.fix_normals(mm)
    trimesh.repair.fill_holes(mm)
    if mm.is_watertight: return mm,"repaired"
    # 얇은 판(1축이 얇음) → 그 축으로 두께 부여(오프셋 압출)
    ext=mm.extents; a=int(np.argmin(ext))
    if ext[a] < 10:   # 얇은 판/링 → OBB 기준 슬래브로 대체 근사(외형 유지, 최소 프린트 두께 3)
        try:
            T=mm.bounding_box_oriented.primitive.transform
            e=mm.bounding_box_oriented.primitive.extents.copy();
            e[np.argmin(e)]=max(3.0,e[np.argmin(e)])
            box=trimesh.creation.box(extents=e, transform=T)
            return box,"slab-approx"
        except Exception: pass
    return mm,"open(manual)"

def cutter(pos,ax,r,L,through,start_at=None):
    c=trimesh.creation.cylinder(radius=r,height=L,sections=20)
    axn=ax/(np.linalg.norm(ax) or 1)
    c.apply_transform(trimesh.geometry.align_vectors([0,0,1.0],axn))
    center = pos if through else pos+axn*(L*0.5-1.0)   # 블라인드: pos에서 안쪽으로
    c.apply_translation(center); return c

def sig(m,nt):
    try: ext=sorted(round(float(e),1) for e in m.bounding_box_oriented.extents)
    except: ext=sorted(round(float(e),1) for e in m.extents)
    return (nt,round(float(m.area),0),tuple(ext),round(float(m.volume),0) if m.is_watertight else -1)

groups={}
for f in sorted(glob.glob(f"{RAW}/*.stl")):
    b=os.path.basename(f);mt=meta.get(b,{});m=trimesh.load(f,process=True);nt=mt.get("ntri",len(m.faces))
    s=sig(m,nt); g=groups.get(s)
    if g: g["qty"]+=1; g["mats"].add(mt.get("mat","?"))
    else: groups[s]={"rep":f,"m":m,"qty":1,"mats":{mt.get("mat","?")}}

uniq=sorted(groups.values(), key=lambda g:-np.prod(g["m"].extents))
man=[]; nholes=0; nsock=0
for i,g in enumerate(uniq,1):
    m=g["m"].copy(); mats="+".join(sorted(g["mats"]))
    m,status=solidify(m)
    holes=0; socks=0
    if m.is_watertight:
        lo,hi=m.bounds; L=float(np.linalg.norm(m.extents))+40
        for f in FAST:
            if np.any(f["pos"]<lo-18) or np.any(f["pos"]>hi+18): continue
            LL = L if f["through"] else min(L, f["depth"]+4)
            try:
                res=m.difference(cutter(f["pos"],f["ax"],f["r"],LL,f["through"]))
                if res.is_watertight and res.volume<m.volume-0.4: m=res; holes+=1
            except Exception: pass
        # 섬스크류 소켓 P2.0 암나사
        for sk in SOCK:
            if np.any(sk["pos"]<lo-16) or np.any(sk["pos"]>hi+16): continue
            try:
                cut=threadlib.ext_thread(5.0+0.4, 2.0, 16.0)   # P2.0 내나사 절삭툴
                axn=sk["ax"]/(np.linalg.norm(sk["ax"]) or 1)
                cut.apply_transform(trimesh.geometry.align_vectors([0,0,1.0],axn))
                cut.apply_translation(sk["pos"]-axn*8.0)
                res=m.difference(cut)
                if res.is_watertight and res.volume<m.volume-0.4: m=res; socks+=1
            except Exception: pass
    ext=sorted(m.extents); dims=f"{ext[0]:.0f}x{ext[1]:.0f}x{ext[2]:.0f}"
    nholes+=holes; nsock+=socks
    fn=f"P{i:02d}_qty{g['qty']}_{dims}_{mats}_h{holes}_ts{socks}.stl"
    m.export(f"{OUT}/{fn}")
    man.append(dict(part=f"P{i:02d}",file=fn,qty=g["qty"],dims=dims,material_hint=mats,
                    status=status,holes=holes,thumb_sockets=socks))
    print(f"P{i:02d} q{g['qty']} {dims:<14} {mats:<8} {status:<12} holes={holes} sockets={socks}")
# canonical thumbscrew
shutil.copyfile(f"{SP}/stl_thread/thumbscrew_PRINT_P2.0.stl", f"{OUT}/P{len(uniq)+1:02d}_THUMBSCREW_qty{thumb}_M5-P2.0.stl")
man.append(dict(part=f"P{len(uniq)+1:02d}",file=f"P{len(uniq)+1:02d}_THUMBSCREW_qty{thumb}_M5-P2.0.stl",
                qty=thumb,dims="D12x16",material_hint="PEEK",status="threaded",holes="-",thumb_sockets="-"))
json.dump(man,open(f"{OUT}/parts_manifest.json","w"),ensure_ascii=False,indent=1)
sk=sum(1 for x in man if x["status"] not in ("solid","threaded"))
print(f"\nTOTAL parts={len(uniq)}  SHCS holes={nholes}  thumb-sockets={nsock}  solidified/other={sk}")
