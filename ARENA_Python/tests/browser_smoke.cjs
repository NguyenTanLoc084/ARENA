/* Optional browser verification. Requires Node.js and Playwright; app runtime does not. */
const { chromium } = require('playwright');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'arena-ui-'));
  const root = path.resolve(__dirname, '..');
  const port = process.env.TEST_PORT || '5012';
  const base = `http://127.0.0.1:${port}`;
  const source = `import os\nfrom app import create_app\nfrom app.seed import seed_demo\na=create_app({'DATABASE':os.environ['TEST_DATABASE'],'SECRET_KEY':'browser-test-only'})\nwith a.app_context():seed_demo()\na.run(port=int(os.environ['TEST_PORT']),debug=False)`;
  const server = spawn(process.env.PYTHON || 'python', ['-c', source], {
    cwd: root,
    env: { ...process.env, TEST_DATABASE: path.join(temporary, 'test.sqlite3'), TEST_PORT: port },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let serverLog = '';
  server.stderr.on('data', chunk => { serverLog += chunk; });
  server.on('error', error => { serverLog += error.message; });
  let browser;
  try {
    let ready = false;
    for (let i = 0; i < 200; i++) {
      try { const response = await fetch(base); if (response.ok) { ready = true; break; } } catch {}
      if (server.exitCode !== null) break;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    assert(ready, 'Server failed to start: ' + serverLog);
    browser = await chromium.launch({
      headless: true,
      ...(process.env.BROWSER_EXECUTABLE ? { executablePath: process.env.BROWSER_EXECUTABLE } : {}),
      args: process.env.BROWSER_ARGS ? JSON.parse(process.env.BROWSER_ARGS) : [],
    });
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('dialog', dialog => dialog.accept());
    async function go(route) {
      const response = await page.goto(base + route);
      assert.equal(response.status(), 200, route);
    }
    async function signIn(name) {
      await go('/login');
      await page.locator('[name=username]').fill(name);
      await page.locator('[name=password]').fill('Arena@2026');
      await page.locator('form button').last().click();
      await page.waitForURL(base + '/');
    }
    await go('/');
    await page.locator('#event-search').fill('Campus');
    assert.equal(await page.locator('[data-event-name]:visible').count(), 1);
    await signIn('doitruong1');
    await go('/events/3/register');
    await page.locator('[name=starters][value="1"]').check();
    await page.locator('[name=reserves][value="1"]').check();
    assert.equal(await page.locator('[name=starters][value="1"]').isChecked(), false);
    for (let id = 1; id <= 5; id++) await page.locator(`[name=starters][value="${id}"]`).check();
    await page.getByRole('button', { name: 'Gửi hồ sơ đến BTC' }).click();
    await page.waitForURL(base + '/my-team');
    assert((await page.locator('main').innerText()).includes('Chờ duyệt'));
    await signIn('btc');
    await go('/events/3');
    await page.getByRole('button', { name: 'Duyệt hồ sơ', exact: true }).click();
    await page.waitForLoadState('networkidle');
    assert((await page.locator('main').innerText()).includes('Đã cập nhật trạng thái hồ sơ'));
    await go('/matches/1');
    await page.locator('[name=winner]').selectOption({ index: 1 });
    await page.getByRole('button', { name: 'Lưu kết quả ván', exact: true }).click();
    await page.waitForLoadState('networkidle');
    assert((await page.locator('main').innerText()).includes('Đã lưu ván'));
    assert.equal(await page.locator('#kda-form').count(), 0); // Second victory finishes the Bo3.
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 900 });
      for (const route of ['/', '/events/1', '/events/2', '/matches/1', '/events/2/report', '/password']) {
        await go(route);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, `${width}px ${route}`);
      }
    }
    await page.locator('#menu-toggle').click();
    assert.equal(await page.locator('#menu-toggle').getAttribute('aria-expanded'), 'true');
    await go('/events/2');
    await page.waitForFunction(() => document.querySelector('#live-status').textContent.includes('Đã đồng bộ'));
    assert.deepEqual(errors, []);
    console.log('PASS: login, search, roster selection, submit/review, save game, desktop/mobile, menu, polling; no JS errors.');
  } finally {
    if (browser) await browser.close();
    server.kill();
    await new Promise(resolve => server.exitCode !== null ? resolve() : server.once('exit', resolve));
    fs.rmSync(temporary, { recursive: true, force: true });
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
