# 录屏计划格式

`scripts/record-browser.mjs` 接收一个 JSON 文件。所有相对路径均以该 JSON 文件所在目录为基准。

## 基本示例

```json
{
  "url": "https://example.com",
  "video": "raw/tutorial.webm",
  "metadata": "raw/tutorial.json",
  "viewport": { "width": 1280, "height": 720 },
  "locale": "zh-CN",
  "browser": {
    "channel": "chrome",
    "headless": false,
    "args": ["--no-first-run"]
  },
  "steps": [
    { "action": "caption", "text": "打开设置页面" },
    { "action": "wait", "ms": 2000 },
    { "action": "click", "selector": "text=设置" },
    { "action": "caption", "text": "选择需要修改的选项" },
    { "action": "wait", "ms": 2500 }
  ]
}
```

## 支持的操作

- `caption`：开始一条字幕，`text` 必填。下一条 `caption` 或录制结束会自动闭合上一条字幕。
- `wait`：等待 `ms` 毫秒。
- `goto`：打开 `url`，可设置 `waitUntil`。
- `click` / `dblclick`：按 CSS 或 Playwright `text=` 选择器点击；可设 `removeTarget: true`。
- `fill`：向选择器填写 `value`。
- `press`：在 `selector` 上按 `key`。
- `waitFor`：等待 `selector` 达到 `state`，可设 `timeoutMs`。
- `waitForUrl`：等待 URL 包含指定 `pattern`，也可用 `url`。
- `scrollTo`：滚动窗口至 `x`、`y`。
- `scrollIntoView`：滚动到 `selector` 元素。

每一步都可加 `waitMs`，在该操作完成后额外等待。

## 录后处理

```bash
node scripts/record-browser.mjs plan.json
python3 scripts/make-srt.py raw/tutorial.json tutorial.srt
python3 scripts/render-video.py --video raw/tutorial.webm --srt tutorial.srt --output tutorial.mp4
```

`render-video.py` 默认使用技能内置配乐，并让最后 1.2 秒缓慢淡到全黑；需要静音时传 `--music none`，使用其他曲目时传 `--music 路径`，调整结尾时长时传 `--fade-out 秒数`。

如果网页在本机浏览器中能打开、但 Playwright 报 `ERR_CONNECTION_CLOSED`，在 `browser.args` 中加入 `--no-proxy-server`、`--disable-http2` 和 `--disable-quic` 后重试。
