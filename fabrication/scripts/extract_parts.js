// 부품(개별) 단위 분리 추출 — 씬 최상위 그룹이 아닌 mesh 단위로 분리, 중복 dedupe, 섬스크류 1종화
const { chromium } = require('playwright');
const fs = require('fs'); const path = require('path');
(async () => {
  const SRC = process.argv[2], OUT = process.argv[3];
  const browser = await chromium.launch({ executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
    args:['--use-gl=swiftshader','--no-sandbox'] });
  const page = await browser.newPage({ viewport:{width:1000,height:700} });
  const errs=[]; page.on('pageerror',e=>errs.push(e.message));
  await page.goto('file://'+SRC,{waitUntil:'load'}); await page.waitForTimeout(4200);

  const meshes = await page.evaluate(() => {
    const scene=window.__scene, T=window.THREE;
    // 프린트 재질: PEEK(탄색), PETG, RIG, + 섬스크류 나사부 금속(0x404040 — 나사부만, 노브와 함께 있을 때 섬스크류로)
    const PAL={0xc0a86c:'PEEK',0xcbb483:'PEEK',0x2a3240:'RIG',0x2e3440:'PETG'};
    const out=[]; const tmp=new T.Vector3();
    scene.traverse(o=>{
      if(!o.isMesh||!o.geometry||!o.geometry.attributes||!o.geometry.attributes.position) return;
      const mats=Array.isArray(o.material)?o.material:[o.material];
      let mm=null; for(const mt of mats){ try{ if(mt&&mt.color&&PAL[mt.color.getHex()]){mm=PAL[mt.color.getHex()];break;} }catch(e){} }
      if(!mm) return;
      o.updateWorldMatrix(true,false);
      const M=o.matrixWorld, pos=o.geometry.attributes.position, idx=o.geometry.index;
      const tris=[]; const wv=(i)=>{tmp.fromBufferAttribute(pos,i);tmp.applyMatrix4(M);return[tmp.x,tmp.y,tmp.z];};
      if(idx){for(let i=0;i<idx.count;i+=3)tris.push([wv(idx.getX(i)),wv(idx.getX(i+1)),wv(idx.getX(i+2))]);}
      else{for(let i=0;i<pos.count;i+=3)tris.push([wv(i),wv(i+1),wv(i+2)]);}
      if(!tris.length) return;
      let mnx=1e9,mny=1e9,mnz=1e9,mxx=-1e9,mxy=-1e9,mxz=-1e9;
      tris.forEach(t=>t.forEach(v=>{mnx=Math.min(mnx,v[0]);mny=Math.min(mny,v[1]);mnz=Math.min(mnz,v[2]);mxx=Math.max(mxx,v[0]);mxy=Math.max(mxy,v[1]);mxz=Math.max(mxz,v[2]);}));
      out.push({mat:mm,ntri:tris.length,w:+(mxx-mnx).toFixed(1),h:+(mxy-mny).toFixed(1),d:+(mxz-mnz).toFixed(1),tris});
    });
    return out;
  });

  // 섬스크류 노브 판정: PEEK + 정렬bbox ≈ (6~9, 11~14, 11~14) + ntri 60~84 (Ø12×6 18각 실린더)
  function isThumbKnob(m){
    // 섬스크류 널링 노브 Ø12×6 (18각) — 방향 무관: 큰 두 치수가 Ø12(11~14.5), 삼각면 ~72
    if(m.mat!=='PEEK') return false;
    const s=[m.w,m.h,m.d].sort((a,b)=>a-b);
    return m.ntri>=58 && m.ntri<=92 && s[1]>=11 && s[1]<=14.5 && s[2]>=11 && s[2]<=14.5;
  }
  let thumbCount=0;
  const parts=[];
  for(const m of meshes){ if(isThumbKnob(m)){thumbCount++; continue;} parts.push(m); }

  // 전 메쉬 원본 덤프 (dedupe는 Python 불변량으로 수행)
  function writeSTL(fp,tris,sol){ let s=`solid ${sol}\n`;
    for(const t of tris){ const ux=t[1][0]-t[0][0],uy=t[1][1]-t[0][1],uz=t[1][2]-t[0][2],vx=t[2][0]-t[0][0],vy=t[2][1]-t[0][1],vz=t[2][2]-t[0][2];
      let nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx; const L=Math.hypot(nx,ny,nz)||1; nx/=L;ny/=L;nz/=L;
      s+=`facet normal ${nx} ${ny} ${nz}\nouter loop\n`; for(const v of t)s+=`vertex ${v[0]} ${v[1]} ${v[2]}\n`; s+=`endloop\nendfacet\n`; }
    s+=`endsolid ${sol}\n`; fs.writeFileSync(fp,s); }
  const raw=path.join(OUT,'raw'); fs.mkdirSync(raw,{recursive:true});
  const meta=[];
  parts.forEach((p,i)=>{ const fn=`raw_${String(i).padStart(3,'0')}.stl`; writeSTL(path.join(raw,fn),p.tris,`raw_${i}`);
    meta.push({file:fn,mat:p.mat,ntri:p.ntri,w:p.w,h:p.h,d:p.d}); });
  fs.writeFileSync(path.join(OUT,'raw_meta.json'),JSON.stringify({thumbCount,meta},null,1));
  console.log('meshes:',meshes.length,'thumbscrews(→1):',thumbCount,'raw parts dumped:',parts.length,'err:',errs.slice(0,2).join('|')||'none');
  await browser.close();
})();
