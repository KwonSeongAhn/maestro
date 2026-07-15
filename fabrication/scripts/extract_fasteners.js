const { chromium } = require('playwright');
const fs=require('fs');
(async () => {
  const SRC=process.argv[2], OUT=process.argv[3];
  const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome',args:['--use-gl=swiftshader','--no-sandbox']});
  const p=await b.newPage(); await p.goto('file://'+SRC,{waitUntil:'load'}); await p.waitForTimeout(4200);
  const data=await p.evaluate(()=>{
    const T=window.THREE, scene=window.__scene, out=[]; const wp=new T.Vector3(), wq=new T.Quaternion();
    scene.traverse(o=>{
      if(o.userData && o.userData.fastener){
        o.getWorldPosition(wp); o.getWorldQuaternion(wq);
        const f=o.userData.fastener;
        // 홀 축방향(월드) = 볼트 로컬 -Y(나사 진행) 회전 적용
        const ax=new T.Vector3(0,-1,0).applyQuaternion(wq);
        out.push({size:f.size,joint:f.joint,clearHole:f.clearHole,tapDrill:f.tapDrill,pitch:f.pitch,
          threadLen:f.threadLen,orderLen:f.orderLen,
          x:+wp.x.toFixed(2),y:+wp.y.toFixed(2),z:+wp.z.toFixed(2),
          ax:+ax.x.toFixed(3),ay:+ax.y.toFixed(3),az:+ax.z.toFixed(3),visible:o.visible});
      }
    });
    return out;
  });
  fs.writeFileSync(OUT, JSON.stringify(data,null,1));
  // 집계
  const by={}; const jt={};
  data.forEach(d=>{ by[d.size]=(by[d.size]||0)+1; const k=d.size+'/'+d.joint; jt[k]=(jt[k]||0)+1; });
  console.log('TOTAL fasteners with spec:', data.length);
  console.log('by size:', JSON.stringify(by));
  console.log('by size/joint:', JSON.stringify(jt,null,0));
  await b.close();
})();
