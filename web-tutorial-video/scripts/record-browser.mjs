#!/usr/bin/env node
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';

const require = createRequire(import.meta.url);
const playwrightCandidates = [
  process.env.PLAYWRIGHT_MODULE,
  'playwright',
].filter(Boolean);
try {
  const npmRoot = execFileSync('npm', ['root', '-g'], { encoding: 'utf8' }).trim();
  playwrightCandidates.push(path.join(npmRoot, 'playwright'));
} catch {
  // npm 不存在时继续尝试本地模块。
}

let playwright;
let lastError;
for (const candidate of playwrightCandidates) {
  try {
    playwright = require(candidate);
    break;
  } catch (error) {
    lastError = error;
  }
}
if (!playwright) throw lastError ?? new Error('找不到 Playwright，请先安装。');

const planPath = process.argv[2];
if (!planPath) {
  console.error('用法: node record-browser.mjs <plan.json>');
  process.exit(2);
}

const plan = JSON.parse(await fs.readFile(planPath, 'utf8'));
if (!plan.video) throw new Error('plan.video 必填。');
if (!Array.isArray(plan.steps)) throw new Error('plan.steps 必须是数组。');

const outputVideo = path.resolve(path.dirname(planPath), plan.video);
const metadataPath = path.resolve(path.dirname(planPath), plan.metadata ?? `${plan.video}.json`);
await fs.mkdir(path.dirname(outputVideo), { recursive: true });
await fs.mkdir(path.dirname(metadataPath), { recursive: true });

const viewport = plan.viewport ?? { width: 1280, height: 720 };
const browserConfig = plan.browser ?? {};
const browser = await playwright.chromium.launch({
  channel: browserConfig.channel,
  headless: browserConfig.headless ?? false,
  args: browserConfig.args ?? [],
});
const context = await browser.newContext({
  viewport,
  deviceScaleFactor: plan.deviceScaleFactor ?? 1,
  locale: plan.locale ?? 'zh-CN',
  recordVideo: { dir: path.dirname(outputVideo), size: viewport },
});
const page = await context.newPage();
const video = page.video();
if (!video) throw new Error('当前浏览器上下文没有启用录屏。');

const startedAt = Date.now();
const elapsed = () => (Date.now() - startedAt) / 1000;
const captions = [];
let currentCaption = null;

function beginCaption(text) {
  if (currentCaption) currentCaption.end = elapsed();
  currentCaption = { start: elapsed(), end: null, text: String(text) };
  captions.push(currentCaption);
}

async function resolveLocator(page, selector) {
  const locator = page.locator(selector).first();
  await locator.waitFor({ state: 'visible', timeout: plan.defaultTimeoutMs ?? 20000 });
  return locator;
}

try {
  page.setDefaultTimeout(plan.defaultTimeoutMs ?? 20000);
  if (plan.url) await page.goto(plan.url, { waitUntil: plan.waitUntil ?? 'domcontentloaded' });

  for (const [index, step] of plan.steps.entries()) {
    const action = step.action;
    if (action === 'caption') {
      beginCaption(step.text);
    } else if (action === 'wait') {
      await page.waitForTimeout(step.ms ?? 1000);
    } else if (action === 'goto') {
      await page.goto(step.url, { waitUntil: step.waitUntil ?? 'domcontentloaded' });
    } else if (action === 'click') {
      const locator = await resolveLocator(page, step.selector);
      if (step.removeTarget) await locator.evaluate((el) => el.removeAttribute('target'));
      await locator.click(step.options);
    } else if (action === 'dblclick') {
      const locator = await resolveLocator(page, step.selector);
      await locator.dblclick(step.options);
    } else if (action === 'fill') {
      const locator = await resolveLocator(page, step.selector);
      await locator.fill(String(step.value ?? ''));
    } else if (action === 'press') {
      const locator = await resolveLocator(page, step.selector);
      await locator.press(step.key);
    } else if (action === 'waitFor') {
      const locator = page.locator(step.selector).first();
      await locator.waitFor({ state: step.state ?? 'visible', timeout: step.timeoutMs ?? 30000 });
    } else if (action === 'waitForUrl') {
      await page.waitForURL(step.url ?? step.pattern, { timeout: step.timeoutMs ?? 30000 });
    } else if (action === 'scrollTo') {
      await page.evaluate(({ x = 0, y = 0 }) => window.scrollTo(x, y), step);
    } else if (action === 'scrollIntoView') {
      const locator = await resolveLocator(page, step.selector);
      await locator.scrollIntoViewIfNeeded();
    } else {
      throw new Error(`第 ${index + 1} 步的操作未知: ${action}`);
    }
    if (step.waitMs) await page.waitForTimeout(step.waitMs);
  }

  if (currentCaption) currentCaption.end = elapsed();
} finally {
  await context.close();
  await browser.close();
}

const rawPath = await video.path();
await fs.copyFile(rawPath, outputVideo);
const metadata = {
  video: outputVideo,
  duration: elapsed(),
  captions,
  pageUrl: page.url(),
  title: plan.title ?? null,
};
await fs.writeFile(metadataPath, JSON.stringify(metadata, null, 2), 'utf8');
console.log(JSON.stringify({ video: outputVideo, metadata: metadataPath, duration: metadata.duration }, null, 2));
