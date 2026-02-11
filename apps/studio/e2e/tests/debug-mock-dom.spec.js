
import { test } from '../fixtures/app.fixture.js';
import fs from 'fs';

test('debug mock dom', async ({ page }) => {
    await page.goto('/#/test');
    await page.waitForTimeout(5000); // Wait for render

    const title = await page.locator('header h1').textContent();
    console.log('PAGE TITLE:', title);

    // Dump DOM
    const html = await page.content();
    fs.writeFileSync('mock-dom-dump.html', html);

    // Log all labels
    const labels = await page.locator('label').allTextContents();
    console.log('LABELS:', labels);

    // Check specifically for width label
    const widthLabel = await page.locator('#param-label-width').count();
    console.log('Width Label Count:', widthLabel);
});
