const { chromium } = require('playwright');
const fs = require('fs'); const path = require('path');
const out = process.argv[2];
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const seen = [];
  page.on('response', async (res) => {
    const u = res.url();
    if (/huemen|\.glb|\.usdz|\.gltf/i.test(u)) {
      seen.push(`${res.status()} ${u}`);
      if (/\.(glb|gltf|usdz)(\?|$)/i.test(u) || /\/skus\//.test(u)) {
        try { const b = await res.body(); const name = path.basename(new URL(u).pathname) || 'sku.json';
              fs.writeFileSync(path.join(out, name), b); seen.push(`   saved ${name} (${b.length} bytes)`); } catch (e) { seen.push('   save failed ' + e.message); }
      }
    }
  });
  await page.goto('https://ca.jbl.com/en_CA/ENDURANCE-PEAK-3.html', { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(8000);
  const thumb = await page.$('.js-3d-thumb-icon');
  if (thumb) { await thumb.click().catch(()=>{}); seen.push('clicked 3D thumb'); }
  await page.waitForTimeout(20000);
  console.log(seen.join('\n'));
  await browser.close();
})();
