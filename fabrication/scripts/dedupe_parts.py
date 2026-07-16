# -*- coding: utf-8 -*-
"""회전·미러·위치 무관 불변량으로 중복 부품 통합 → 고유 1개 + 수량 (평면, 재질 무구분)."""
import json, os, glob, shutil, math
import numpy as np, trimesh

SP="/tmp/claude-0/-home-user-maestro/89feb1d7-5414-58cf-b499-d60f30aed29c/scratchpad"
RAW=f"{SP}/parts/raw"; OUT=f"{SP}/parts_final"
if os.path.exists(OUT): shutil.rmtree(OUT)
os.makedirs(OUT, exist_ok=True)
meta=json.load(open(f"{SP}/parts/raw_meta.json"))
thumb=meta["thumbCount"]; metas={m["file"]:m for m in meta["meta"]}

def sig(mesh, ntri):
    try: ext=sorted(round(float(e),1) for e in mesh.bounding_box_oriented.extents)
    except Exception: ext=sorted(round(float(e),1) for e in mesh.extents)
    area=round(float(mesh.area),0)
    # 부피(수밀 시) 추가 판별
    vol=round(float(mesh.volume),0) if mesh.is_watertight else -1
    return (ntri, area, tuple(ext), vol)

groups={}   # sig -> {"rep":path,"mesh":mesh,"qty":n,"mats":set,"ext":ext,"ntri"}
for f in sorted(glob.glob(f"{RAW}/*.stl")):
    base=os.path.basename(f); mt=metas.get(base,{})
    m=trimesh.load(f, process=True)
    ntri=mt.get("ntri", len(m.faces))
    s=sig(m, ntri)
    g=groups.get(s)
    if g: g["qty"]+=1; g["mats"].add(mt.get("mat","?"))
    else:
        ext=sorted(round(float(e),1) for e in (m.bounding_box_oriented.extents if len(m.vertices)>3 else m.extents))
        groups[s]={"rep":f,"qty":1,"mats":{mt.get("mat","?")},"ext":ext,"ntri":ntri}

uniq=sorted(groups.values(), key=lambda g:-(g["ext"][0]*g["ext"][1]*g["ext"][2]))
manifest=[]
for i,g in enumerate(uniq,1):
    w,h,d=g["ext"]; mats="+".join(sorted(g["mats"]))
    fn=f"P{i:02d}_qty{g['qty']}_{w:.0f}x{h:.0f}x{d:.0f}_{mats}.stl"
    shutil.copyfile(g["rep"], f"{OUT}/{fn}")
    manifest.append({"part":f"P{i:02d}","file":fn,"qty":g["qty"],"dims_mm":f"{w:.0f}x{h:.0f}x{d:.0f}",
                     "material_hint":mats,"ntri":g["ntri"]})
# 섬스크류 1종
ts=f"{SP}/stl_thread/thumbscrew_PRINT_P2.0.stl"
if os.path.exists(ts):
    fn=f"P{len(uniq)+1:02d}_THUMBSCREW_qty{thumb}_M5-P2.0-headthread.stl"
    shutil.copyfile(ts, f"{OUT}/{fn}")
    manifest.append({"part":f"P{len(uniq)+1:02d}","file":fn,"qty":thumb,"dims_mm":"D12x16",
                     "material_hint":"PEEK","ntri":"thread"})
json.dump(manifest, open(f"{OUT}/parts_manifest.json","w"), ensure_ascii=False, indent=1)
tot=sum(m["qty"] for m in manifest)
print(f"raw={len(glob.glob(f'{RAW}/*.stl'))}  unique geometries={len(uniq)}  +thumbscrew  → files={len(manifest)}  total qty={tot}")
for m in manifest: print(f"{m['part']}  x{m['qty']:<3} {m['dims_mm']:<16} {m['material_hint']}")
