#!/usr/bin/env node
/**
 * Generate project thumbnail screenshots using Playwright.
 *
 * Usage:
 *   node scripts/generate-thumbnails.js [--base-url URL]
 *
 * Defaults to http://localhost:5173 (local studio dev server).
 * Pass --base-url https://studio.qubic.quest for production.
 */

const { chromium } = require('playwright');
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const PROJECTS = [
  'fasteners', 'gear-reducer', 'gears', 'gridfinity', 'julia-vase',
  'keyv2', 'maze', 'motor-mount', 'multiboard', 'polydice',
  'portacosas', 'relief', 'spiral-planter', 'stemfie', 'superformula',
  'tablaco', 'torus-knot', 'ultimate-box', 'voronoi', 'yapp-box',
];

const OUT_DIR = path.resolve(__dirname, '../apps/landing/public/projects');

async function main() {
  const baseUrl = process.argv.includes('--base-url')
    ? process.argv[process.argv.indexOf('--base-url') + 1]
    : 'http://localhost:5173';

  console.log(`Generating thumbnails from ${baseUrl}`);
  console.log(`Output: ${OUT_DIR}\n`);

  fs.mkdirSync(OUT_DIR, { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 1,
  });

  let hasCwebp = false;
  try {
    execSync('which cwebp', { stdio: 'ignore' });
    hasCwebp = true;
  } catch {}

  const succeeded = [];
  const failed = [];

  for (const slug of PROJECTS) {
    const page = await context.newPage();
    const url = `${baseUrl}?embed=true#/${slug}`;
    const pngPath = path.join(OUT_DIR, `${slug}.png`);
    const webpPath = path.join(OUT_DIR, `${slug}.webp`);
    process.stdout.write(`  ${slug}...`);

    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: 45000 });
      // Wait for Three.js canvas to appear
      await page.waitForSelector('canvas', { timeout: 20000 });
      // Allow 3D scene to finish rendering
      await page.waitForTimeout(3000);

      await page.screenshot({ path: pngPath, type: 'png' });

      if (hasCwebp) {
        execSync(`cwebp -q 80 "${pngPath}" -o "${webpPath}"`, { stdio: 'ignore' });
        fs.unlinkSync(pngPath);
      } else {
        fs.renameSync(pngPath, webpPath);
      }

      console.log(' ok');
      succeeded.push(slug);
    } catch (err) {
      console.log(` FAILED: ${err.message.split('\n')[0]}`);
      failed.push(slug);
    }

    await page.close();
  }

  await browser.close();

  console.log(`\nDone: ${succeeded.length} succeeded, ${failed.length} failed`);
  if (failed.length) console.log(`Failed: ${failed.join(', ')}`);
}

main().catch(console.error);
