const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
(async () => {
  const SRC = process.argv[2];
  const OUT = process.argv[3];
  const browser = await chromium.launch({
    executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
    args: ['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist','--no-sandbox']
  });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errs=[]; page.on('pageerror',e=>errs.push(e.message));
  await page.goto('file://'+SRC, { waitUntil:'load' });
  await page.waitForTimeout(4200);   // full build incl setTimeout parts

  const parts = await page.evaluate(() => {
    const THREE = window.THREE || (window.__scene && window.__scene.type ? null : null);
    const scene = window.__scene;
    // print material palette (exact hex)
    const PAL = { 0xc0a86c:'PEEK', 0xcbb483:'PEEK', 0x2a3240:'RIG', 0x2e3440:'PETG' };
    const V = new (window.THREE ? window.THREE.Vector3 : Object)();
    function meshTris(mesh){
      const g=mesh.geometry;
      if(!g||!g.attributes||!g.attributes.position) return null;
      mesh.updateWorldMatrix(true,false);
      const m=mesh.matrixWorld, pos=g.attributes.position, idx=g.index;
      const out=[];
      const tmp=new window.THREE.Vector3();
      const wv=(i)=>{ tmp.fromBufferAttribute(pos,i); tmp.applyMatrix4(m); return [tmp.x,tmp.y,tmp.z]; };
      if(idx){ for(let i=0;i<idx.count;i+=3) out.push([wv(idx.getX(i)),wv(idx.getX(i+1)),wv(idx.getX(i+2))]); }
      else   { for(let i=0;i<pos.count;i+=3) out.push([wv(i),wv(i+1),wv(i+2)]); }
      return out;
    }
    function colHex(mat){ try{ return mat && mat.color ? mat.color.getHex() : -1; }catch(e){ return -1; } }
    const results=[];
    scene.children.forEach((child,ci)=>{
      // collect print meshes per material within this top-level child
      const byMat={};
      child.traverse(o=>{
        if(!o.isMesh) return;
        const mats = Array.isArray(o.material)?o.material:[o.material];
        let mm=null;
        for(const mt of mats){ const h=colHex(mt); if(PAL[h]){ mm=PAL[h]; break; } }
        if(!mm) return;
        const tris=meshTris(o); if(!tris||!tris.length) return;
        (byMat[mm]=byMat[mm]||[]).push(...tris);
      });
      Object.keys(byMat).forEach(mm=>{
        const tris=byMat[mm];
        // bbox
        let mnx=1e9,mny=1e9,mnz=1e9,mxx=-1e9,mxy=-1e9,mxz=-1e9;
        tris.forEach(t=>t.forEach(v=>{mnx=Math.min(mnx,v[0]);mny=Math.min(mny,v[1]);mnz=Math.min(mnz,v[2]);mxx=Math.max(mxx,v[0]);mxy=Math.max(mxy,v[1]);mxz=Math.max(mxz,v[2]);}));
        results.push({mat:mm, ci, name:child.name||'', ntri:tris.length,
          w:Math.round(mxx-mnx), h:Math.round(mxy-mny), d:Math.round(mxz-mnz), tris});
      });
    });
    return { results, errs: [] };
  });

  // dedupe identical parts by signature (mat + bbox + ntri) → 1 STL + qty
  const uniq={}; // sig -> {part, qty}
  for(const p of parts.results){
    if(p.ntri < 2) continue;
    const sig=`${p.mat}_${p.w}x${p.h}x${p.d}_${p.ntri}`;
    if(uniq[sig]) uniq[sig].qty++;
    else uniq[sig]={part:p, qty:1};
  }
  const counts={}; const summary=[];
  // sort by material then size desc
  const list=Object.values(uniq).sort((a,b)=> a.part.mat.localeCompare(b.part.mat) || (b.part.w*b.part.h*b.part.d)-(a.part.w*a.part.h*a.part.d));
  for(const {part:p, qty} of list){
    counts[p.mat]=(counts[p.mat]||0)+1;
    const idx=counts[p.mat];
    const dir=path.join(OUT, p.mat); fs.mkdirSync(dir,{recursive:true});
    const fname = `${p.mat}_${String(idx).padStart(2,'0')}_qty${qty}_${p.w}x${p.h}x${p.d}.stl`;
    let s=`solid ${p.mat}_${idx}\n`;
    for(const t of p.tris){
      const ux=t[1][0]-t[0][0], uy=t[1][1]-t[0][1], uz=t[1][2]-t[0][2];
      const vx=t[2][0]-t[0][0], vy=t[2][1]-t[0][1], vz=t[2][2]-t[0][2];
      let nx=uy*vz-uz*vy, ny=uz*vx-ux*vz, nz=ux*vy-uy*vx;
      const L=Math.hypot(nx,ny,nz)||1; nx/=L;ny/=L;nz/=L;
      s+=`facet normal ${nx} ${ny} ${nz}\nouter loop\n`;
      for(const v of t) s+=`vertex ${v[0]} ${v[1]} ${v[2]}\n`;
      s+=`endloop\nendfacet\n`;
    }
    s+=`endsolid ${p.mat}_${idx}\n`;
    fs.writeFileSync(path.join(dir,fname), s);
    summary.push({mat:p.mat, file:`${p.mat}/${fname}`, qty, ntri:p.ntri, dims:`${p.w}x${p.h}x${p.d}`});
  }
  fs.writeFileSync(path.join(OUT,'stl_manifest.json'), JSON.stringify(summary,null,1));
  const totqty={}; summary.forEach(s=>totqty[s.mat]=(totqty[s.mat]||0)+s.qty);
  console.log('UNIQUE PARTS:', summary.length, 'files/mat:', JSON.stringify(counts), 'total qty/mat:', JSON.stringify(totqty), 'err:', errs.slice(0,2).join('|')||'none');
  summary.forEach(s=>console.log(`${s.file}  x${s.qty}  tri=${s.ntri}  bbox=${s.dims}`));
  await browser.close();
})();
