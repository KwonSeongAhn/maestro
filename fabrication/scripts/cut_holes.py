# -*- coding: utf-8 -*-
"""211개 실계측 체결 데이터로 부품에 기능별 홀 부울 절삭 (탭=tapDrill / 관통=clearHole)."""
import json, glob, os, shutil, numpy as np, trimesh

SP="/tmp/claude-0/-home-user-maestro/89feb1d7-5414-58cf-b499-d60f30aed29c/scratchpad"
RAW=f"{SP}/parts/raw"; OUT=f"{SP}/parts_holed"
if os.path.exists(OUT): shutil.rmtree(OUT);
os.makedirs(OUT, exist_ok=True)
F=json.load(open(f"{SP}/fasteners.json"))
meta={m["file"]:m for m in json.load(open(f"{SP}/parts/raw_meta.json"))["meta"]}
FAST=[dict(pos=np.array([f["x"],f["y"],f["z"]]),ax=np.array([f["ax"],f["ay"],f["az"]]),
           r=(f["clearHole"] if f["joint"]=="THROUGH+NUT" else f["tapDrill"])/2.0,
           joint=f["joint"],size=f["size"]) for f in F]

def sig(m,ntri):
    try: ext=sorted(round(float(e),1) for e in m.bounding_box_oriented.extents)
    except Exception: ext=sorted(round(float(e),1) for e in m.extents)
    return (ntri, round(float(m.area),0), tuple(ext), round(float(m.volume),0) if m.is_watertight else -1)

# group raw by invariant
groups={}
for f in sorted(glob.glob(f"{RAW}/*.stl")):
    b=os.path.basename(f); mt=meta.get(b,{}); m=trimesh.load(f,process=True); nt=mt.get("ntri",len(m.faces))
    s=sig(m,nt); g=groups.get(s)
    if g: g["qty"]+=1; g["mats"].add(mt.get("mat","?"))
    else: groups[s]={"rep":f,"mesh":m,"qty":1,"mats":{mt.get("mat","?")},"ntri":nt}

def cutter(pos,ax,r,L):
    c=trimesh.creation.cylinder(radius=r,height=L,sections=20)
    T=trimesh.geometry.align_vectors([0,0,1.0], ax/ (np.linalg.norm(ax) or 1))
    c.apply_transform(T); c.apply_translation(pos); return c

uniq=sorted(groups.values(), key=lambda g:-np.prod(g["mesh"].extents))
manifest=[]; open_shell=0; total_holes=0
for i,g in enumerate(uniq,1):
    m=g["mesh"].copy(); mats="+".join(sorted(g["mats"]))
    ext=sorted(m.extents); dims=f"{ext[0]:.0f}x{ext[1]:.0f}x{ext[2]:.0f}"
    holed=0; status="solid"
    if not m.is_watertight:
        status="open-shell(skip holes)"; open_shell+=1
    else:
        lo,hi=m.bounds; margin=20; L=float(np.linalg.norm(m.extents))+40
        for f in FAST:
            p=f["pos"]
            if np.any(p<lo-margin) or np.any(p>hi+margin): continue
            try:
                res=m.difference(cutter(p,f["ax"],f["r"],L))
                if res.is_watertight and res.volume < m.volume-0.5:
                    m=res; holed+=1
            except Exception: pass
        total_holes+=holed
    fn=f"P{i:02d}_qty{g['qty']}_{dims}_{mats}_holes{holed}.stl"
    m.export(f"{OUT}/{fn}")
    manifest.append({"part":f"P{i:02d}","file":fn,"qty":g["qty"],"dims":dims,"material_hint":mats,
                     "holes":holed,"status":status})
# thumbscrew (already threaded)
ts=f"{SP}/stl_thread/thumbscrew_PRINT_P2.0.stl"
thumb=json.load(open(f"{SP}/parts/raw_meta.json"))["thumbCount"]
shutil.copyfile(ts, f"{OUT}/P{len(uniq)+1:02d}_THUMBSCREW_qty{thumb}_M5-P2.0.stl")
manifest.append({"part":f"P{len(uniq)+1:02d}","file":f"P{len(uniq)+1:02d}_THUMBSCREW_qty{thumb}_M5-P2.0.stl",
                 "qty":thumb,"dims":"D12x16","material_hint":"PEEK","holes":"thread","status":"threaded"})
json.dump(manifest,open(f"{OUT}/parts_manifest.json","w"),ensure_ascii=False,indent=1)
print(f"parts={len(uniq)} open-shell(skipped)={open_shell} total holes cut={total_holes}")
print("parts with holes:")
for x in manifest:
    if isinstance(x["holes"],int) and x["holes"]>0: print(f"  {x['part']} x{x['qty']} {x['dims']:<14} {x['material_hint']:<8} holes={x['holes']}")
