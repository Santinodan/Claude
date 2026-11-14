const { chromium } = require('playwright');
(async () => {
  const [,, file, out, width] = process.argv;
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: +width, height: 900 }, deviceScaleFactor: 2, colorScheme: 'dark' });
  const errs = []; p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); }); p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + file); await p.waitForTimeout(800);
  await p.screenshot({ path: out, fullPage: true });
  console.log(out, errs.slice(0, 5));
  await b.close();
})();
