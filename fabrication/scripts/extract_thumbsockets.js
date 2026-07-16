const { chromium }=require('playwright'); const fs=require('fs');
(async()=>{const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome',args:['--use-gl=swiftshader','--no-sandbox']});
const p=await b.newPage(); await p.goto('file://'+process.argv[2],{waitUntil:'load'}); await p.waitForTimeout(4200);
const d=await p.evaluate(()=>{const T=window.THREE,s=window.__scene,out=[];const wp=new T.Vector3(),wq=new T.Quaternion();
 s.traverse(o=>{ if(!o.isMesh||!o.geometry) return; const mats=Array.isArray(o.material)?o.material:[o.material];
  let peek=false; for(const mt of mats){try{const h=mt&&mt.color&&mt.color.getHex();if(h===0xc0a86c||h===0xcbb483)peek=true;}catch(e){}}
  if(!peek) return; o.geometry.computeBoundingBox(); const bb=o.geometry.boundingBox; const sz=new T.Vector3(); bb.getSize(sz);
  // 노브 Ø12×6 판정: 실린더 18각 → position count 근사 + 크기
  const dims=[sz.x,sz.y,sz.z].sort((a,b)=>a-b); const nt=(o.geometry.index?o.geometry.index.count:o.geometry.attributes.position.count)/3;
  if(nt>=58&&nt<=92&&dims[1]>=5&&dims[1]<=13&&dims[2]>=5&&dims[2]<=13){
   o.getWorldPosition(wp);o.getWorldQuaternion(wq); const ax=new T.Vector3(0,1,0).applyQuaternion(wq);
   out.push({x:+wp.x.toFixed(2),y:+wp.y.toFixed(2),z:+wp.z.toFixed(2),ax:+ax.x.toFixed(3),ay:+ax.y.toFixed(3),az:+ax.z.toFixed(3)});
  }}); return out;});
fs.writeFileSync(process.argv[3],JSON.stringify(d,null,1)); console.log('thumbscrew sockets:',d.length); await b.close();})();
