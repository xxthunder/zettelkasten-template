// structurizr-export.js <url> <outDir>
// Runs inside Puppeteer's container image, driven by structurizr-export.sh.
// Does what Structurizr's own export-diagrams.js (structurizr/puppeteer) does, cut to cropped
// SVGs without metadata in Structurizr's dark mode: one <outDir>/<view key>.svg per view of
// the viewer at <url>.
const puppeteer = require('puppeteer');
const fs = require('fs');

(async () => {
  const [url, outDir] = process.argv.slice(2);
  // Chrome's sandbox needs privileges the container does not grant.
  const browser = await puppeteer.launch({ args: ['--no-sandbox'] });
  try {
    const page = await browser.newPage();
    // Structurizr draws its dark mode when the browser prefers dark, as the viewer does on a dark desktop.
    await page.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: 'dark' }]);
    await page.goto(url, { waitUntil: 'networkidle2' });
    const rendered = 'structurizr.scripting && structurizr.scripting.isDiagramRendered() === true';
    await page.waitForFunction(rendered);
    const views = await page.evaluate(() => structurizr.scripting.getViews());
    for (const view of views) {
      await page.evaluate((key) => structurizr.scripting.changeView(key), view.key);
      await page.waitForFunction(rendered);
      const svg = await page.evaluate(() =>
        structurizr.scripting.exportCurrentDiagramToSVG({ includeMetadata: false, crop: true }));
      fs.writeFileSync(`${outDir}/${view.key}.svg`, svg);
      console.log(`exported ${view.key}`);
    }
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
