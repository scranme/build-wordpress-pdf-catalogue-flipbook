/* Real WordPress edge-case regression suite. See browser-smoke.cjs for environment setup. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.WPCF_PLAYWRIGHT || 'playwright');
const base = process.env.WPCF_TEST_URL || 'http://127.0.0.1:8937';
const out = path.resolve(process.env.WPCF_EDGE_SCREENSHOTS || 'dist/browser-edge-cases');
fs.mkdirSync(out, { recursive: true });
const checks = [];
const failures = [];
const errors = [];
const skips = [];
const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));
function check(name, condition = true) {
  assert.ok(condition, name);
  checks.push(name);
  console.log('PASS:', name);
}
async function loaded(page) {
  const panel = page.locator('.wpcf-reader:visible');
  await panel.locator('.wpcf-book .wpcf-page').first().waitFor({ state: 'attached' });
  await page.waitForFunction(() => {
    const panel = document.querySelector('.wpcf-reader[open]');
    return panel && panel.dataset.page && panel.querySelector('.wpcf-status').hidden;
  });
  await wait(250);
  return panel;
}
async function open(page) {
  await page.locator('[data-wpcf-open]').click();
  return loaded(page);
}
async function run() {
  const browser = await chromium.launch({ headless: true, ...(process.env.WPCF_BROWSER ? { executablePath: process.env.WPCF_BROWSER } : {}) });
  async function scenario(name, options, action) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, ...options });
    const page = await context.newPage();
    page.on('pageerror', error => errors.push({ scenario: name, message: error.message }));
    try {
      await page.goto(base + '/catalogue-demo/');
      assert.equal(new URL(page.url()).pathname, '/catalogue-demo/');
      assert.match(await page.title(), /Catalogue/i);
      await page.locator('[data-wpcf-open]').waitFor();
      await action(page, context);
    } catch (error) {
      failures.push({ scenario: name, message: error.message });
      console.error('FAIL:', name, error.message);
      await page.screenshot({ path: path.join(out, name + '-failure.png'), fullPage: true }).catch(() => {});
    } finally { await context.close(); }
  }
  try {
    await scenario('keyboard-focus', {}, async page => {
      const panel = await open(page);
      check('Native modal dialog opens', await panel.evaluate(node => node.tagName === 'DIALOG' && node.matches(':modal')));
      check('Reader initially focuses Back to cover', await panel.getByRole('button', { name: 'Back to cover' }).evaluate(node => node === document.activeElement));
      await page.locator('[data-wpcf-open]').evaluate(node => node.focus());
      check('Native modal prevents outside focus', await panel.evaluate(node => node.contains(document.activeElement)));
      for (let i = 0; i < 16; i++) {
        await page.keyboard.press('Tab');
        assert.ok(await panel.evaluate(node => node.contains(document.activeElement) || document.activeElement === document.body), 'Tab must not focus page content outside the modal.');
      }
      check('Tab traversal never reaches background page controls');
      await panel.getByRole('button', { name: 'Back to cover' }).focus();
      await page.keyboard.press('ArrowRight');
      await page.waitForFunction(() => document.querySelector('.wpcf-reader[open]').dataset.page === '2');
      await wait(650);
      check('ArrowRight turns the book');
      await page.keyboard.press('ArrowLeft');
      await page.waitForFunction(() => document.querySelector('.wpcf-reader[open]').dataset.page === '1');
      await wait(650);
      check('ArrowLeft returns to the cover page');
      await panel.getByRole('searchbox').focus();
      await page.keyboard.press('ArrowRight');
      await wait(100);
      check('Arrow keys inside search do not turn pages', await panel.getAttribute('data-page') === '1');
      await page.screenshot({ path: path.join(out, 'keyboard-dialog.png') });
      await page.keyboard.press('Escape');
      check('Escape closes dialog and restores trigger focus', !(await panel.isVisible()) && await page.locator('[data-wpcf-open]').evaluate(node => node === document.activeElement));
    });

    await scenario('fullscreen', {}, async page => {
      const panel = await open(page);
      const available = await page.evaluate(() => document.fullscreenEnabled);
      if (!available || !(await panel.getByRole('button', { name: 'Fullscreen', exact: true }).isVisible())) {
        skips.push('Fullscreen API unavailable in this browser environment');
        return;
      }
      await panel.getByRole('button', { name: 'Fullscreen', exact: true }).click();
      await page.waitForFunction(() => Boolean(document.fullscreenElement), null, { timeout: 5000 });
      check('Fullscreen enters successfully when API is supported');
      await wait(300);
      await page.screenshot({ path: path.join(out, 'fullscreen.png') });
      await panel.getByRole('button', { name: 'Exit fullscreen', exact: true }).click();
      await page.waitForFunction(() => !document.fullscreenElement);
      check('Fullscreen exits without closing the reader', await panel.isVisible());
    });

    await scenario('reduced-motion', { reducedMotion: 'reduce' }, async page => {
      await page.evaluate(() => {
        const Original = window.St.PageFlip;
        window.St.PageFlip = class extends Original {
          constructor(element, settings) { super(element, settings); window.__wpcfTestSettings = settings; }
        };
      });
      const panel = await open(page);
      check('Reduced-motion preference selects minimal turn duration', await page.evaluate(() => window.__wpcfTestSettings.flippingTime === 1));
      await panel.getByRole('button', { name: 'Next →', exact: true }).click();
      await page.waitForFunction(() => document.querySelector('.wpcf-reader[open]').dataset.page === '2');
      check('Reduced-motion reader remains interactive');
    });

    await scenario('touch-swipe', { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true }, async (page, context) => {
      const panel = await open(page);
      const box = await panel.locator('.wpcf-book-host').boundingBox();
      const session = await context.newCDPSession(page);
      const point = (fraction) => ({ x: box.x + box.width * fraction, y: box.y + box.height * .5, radiusX: 2, radiusY: 2, force: 1, id: 1 });
      await session.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [point(.85)] });
      for (const fraction of [.7, .55, .4, .2]) {
        await wait(20);
        await session.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [point(fraction)] });
      }
      await session.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
      await page.waitForFunction(() => document.querySelector('.wpcf-reader[open]').dataset.page === '2');
      await wait(650);
      check('Real CDP touch swipe turns a mobile page');
      await page.screenshot({ path: path.join(out, 'touch-swipe.png') });
      await session.detach();
    });

    await scenario('odd-page-last-spread', {}, async page => {
      await page.route(/\/manifest\.json(?:\?|$)/, async route => {
        const response = await route.fetch();
        const data = await response.json();
        data.pages = data.pages.slice(0, 5);
        await route.fulfill({ response, json: data });
      });
      const panel = await open(page);
      const jump = panel.getByRole('spinbutton', { name: 'Page number' });
      await jump.fill('5'); await jump.press('Enter');
      check('Odd-page catalogue reaches final right-hand page', await panel.getAttribute('data-page') === '5');
      check('Next is disabled on last odd-page spread', await panel.getByRole('button', { name: 'Next →', exact: true }).isDisabled());
      await page.screenshot({ path: path.join(out, 'odd-page-last-spread.png') });
    });

    await scenario('close-reopen-fetch-race', {}, async page => {
      let requestCount = 0;
      let releaseFirst;
      let firstSeen;
      const delayed = new Promise(resolve => { releaseFirst = resolve; });
      const seen = new Promise(resolve => { firstSeen = resolve; });
      await page.route(/\/manifest\.json(?:\?|$)/, async route => {
        requestCount++;
        if (requestCount === 1) {
          firstSeen();
          await delayed;
          await route.fulfill({ status: 503, body: 'Deliberately stale first request' }).catch(() => {});
        } else await route.continue();
      });
      await page.locator('[data-wpcf-open]').click();
      await seen;
      await page.getByRole('button', { name: 'Back to cover' }).click();
      const panel = await open(page);
      check('Close and reopen starts a fresh manifest request', requestCount === 2);
      releaseFirst();
      await wait(500);
      check('Stale failed request does not replace successful reader', await panel.locator('.wpcf-status').isHidden() && await panel.getByRole('button', { name: 'Retry', exact: true }).count() === 0);
      await panel.getByRole('button', { name: 'Next →', exact: true }).click();
      await page.waitForFunction(() => document.querySelector('.wpcf-reader[open]').dataset.page === '2');
      check('Reader turns after a close/reopen loading race');
    });

    await scenario('missing-image', {}, async page => {
      await page.route(/\/manifest\.json(?:\?|$)/, async route => {
        const response = await route.fetch();
        const data = await response.json();
        data.pages[0].src = 'pages/missing-for-test.webp';
        data.pages[0].src2x = 'pages/missing-for-test.webp';
        await route.fulfill({ response, json: data });
      });
      await page.route(/\/missing-for-test\.webp(?:\?|$)/, route => route.fulfill({ status: 404, body: 'Not found' }));
      const panel = await open(page);
      await panel.locator('.wpcf-image-error .wpcf-image-message').waitFor();
      check('Missing image has a visible explanatory fallback');
      await page.screenshot({ path: path.join(out, 'missing-image.png') });
      await panel.getByRole('button', { name: 'Next →', exact: true }).click();
      await page.waitForFunction(() => document.querySelector('.wpcf-reader[open]').dataset.page === '2');
      check('One missing image does not block later pages');
    });

    await scenario('no-javascript', { javaScriptEnabled: false }, async page => {
      check('No-JavaScript visitors see useful instructions', await page.locator('noscript').innerText().then(text => text.includes('Enable JavaScript')));
      await page.getByText('Browse individual page images', { exact: true }).click();
      const links = page.locator('.wpcf-fallback li a');
      check('No-JavaScript visitors can browse all page links', await links.count() >= 5 && await links.first().isVisible());
      const response = await page.request.get(await links.first().getAttribute('href'));
      check('Fallback image link resolves successfully', response.ok() && /^image\//.test(response.headers()['content-type']));
      await page.screenshot({ path: path.join(out, 'no-javascript.png'), fullPage: true });
    });
    check('No uncaught browser errors in edge scenarios', errors.length === 0);
  } finally {
    fs.writeFileSync(path.join(out, 'results.json'), JSON.stringify({ checks, failures, errors, skips }, null, 2));
    await browser.close();
  }
  if (failures.length) throw new Error(failures.length + ' edge-case scenario(s) failed; see results.json.');
}
run().catch(error => { console.error(error); process.exitCode = 1; });
