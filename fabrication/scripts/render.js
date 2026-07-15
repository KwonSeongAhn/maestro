const { chromium } = require('playwright');
(async () => {
  const file = process.argv[2], out = process.argv[3];
  const browser = await chromium.launch({
    executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
    args: ['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist','--no-sandbox']
  });
  const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } });
  const errs = [];
  page.on('pageerror', e => errs.push('PAGEERR: '+e.message));
  await page.goto('file://' + file, { waitUntil: 'load' });
  await page.waitForTimeout(3600);
  const rep = await page.evaluate(() => {
    const s = window.__scene; let vis=0, hid=0;
    s.children.forEach(o=>{ if(o.isLight) return; if(o.visible)vis++; else hid++; });
    return { total:s.children.length, vis, hid, extras: (window.__hopperExtras||[]).length };
  });
  await page.evaluate(() => {
    ['.controls','.hud','.stats-panel','.ai-panel','.grade-chart','.ball-counter','.angle-readout','.sensor-status']
      .forEach(sel => document.querySelectorAll(sel).forEach(e => e.style.display='none'));
  });
  await page.waitForTimeout(300);
  await (await page.$('#viewer')).screenshot({ path: out });
  console.log('REPORT', JSON.stringify(rep));
  console.log('ERRORS', errs.slice(0,6).join(' || ') || 'none');
  await browser.close();
})();
