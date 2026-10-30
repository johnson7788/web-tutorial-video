# Web Tutorial Video Skill

一个用于制作网页操作教程视频的 Codex Skill。它可以根据现有教程文字，或先查看网页后整理出的步骤，自动录制真实网页操作，生成字幕和视频，并混入内置的纯音乐。教程不包含讲解人声。

## 功能

- 优先使用用户提供的文字教程；没有时先整理成编号步骤。
- 使用 Playwright 操作网页并录制真实浏览器画面。
- 根据操作节点记录字幕时间，输出独立的 UTF-8 `SRT` 文件。
- 自动为中文字幕换行并烧录到视频画面。
- 默认加入低音量纯音乐，也可以关闭音乐或换成用户提供的曲目。
- 输出兼容性较好的 H.264/AAC MP4。

## 目录结构

```text
web-tutorial-video/
├── README.md
└── web-tutorial-video/
    ├── SKILL.md
    ├── assets/
    │   └── music/
    │       ├── LICENSE.txt
    │       └── tutorial-loop.mp3
    ├── references/
    │   └── recording-plan.md
    └── scripts/
        ├── make-srt.py
        ├── record-browser.mjs
        └── render-video.py
```

仓库根目录是项目入口，`web-tutorial-video/` 是唯一需要安装或复制的完整技能目录。复制这个子目录即可，不会带上仓库的 `.git`。

## 安装

克隆仓库，然后只复制技能子目录到 Codex skills 目录：

```bash
git clone https://github.com/johnson7788/web-tutorial-video.git
cp -R web-tutorial-video/web-tutorial-video "${CODEX_HOME:-$HOME/.codex}/skills/"
```

安装后的目录应为：

```text
~/.codex/skills/web-tutorial-video/SKILL.md
```

也可以直接下载 GitHub 中的 `web-tutorial-video/` 文件夹，放到自己的 skills 目录。

## 环境要求

- Node.js
- Playwright 及 Chromium 或 Google Chrome
- Python 3
- Pillow
- FFmpeg 和 FFprobe

脚本会自动尝试从本地项目或全局 npm 模块中查找 Playwright。缺少 Playwright 时，可以安装：

```bash
npm install -g playwright
playwright install chromium
```

## 快速使用

### 1. 编写录屏计划

保存为 `plan.json`。详细字段见 `web-tutorial-video/references/recording-plan.md`。

```json
{
  "url": "https://example.com",
  "video": "raw/tutorial.webm",
  "metadata": "raw/tutorial.json",
  "viewport": { "width": 1280, "height": 720 },
  "locale": "zh-CN",
  "browser": {
    "channel": "chrome",
    "headless": false
  },
  "steps": [
    { "action": "caption", "text": "打开示例网页" },
    { "action": "wait", "ms": 2000 },
    { "action": "click", "selector": "text=下一步" },
    { "action": "caption", "text": "查看操作结果" },
    { "action": "wait", "ms": 2000 }
  ]
}
```

### 2. 录制网页

```bash
node web-tutorial-video/scripts/record-browser.mjs plan.json
```

### 3. 生成字幕

```bash
python3 web-tutorial-video/scripts/make-srt.py raw/tutorial.json tutorial.srt
```

### 4. 生成成片

```bash
python3 web-tutorial-video/scripts/render-video.py \
  --video raw/tutorial.webm \
  --srt tutorial.srt \
  --output tutorial.mp4
```

默认使用内置配乐。关闭音乐或使用其他曲目：

```bash
# 无背景音乐
python3 web-tutorial-video/scripts/render-video.py \
  --video raw/tutorial.webm \
  --srt tutorial.srt \
  --music none \
  --output tutorial-silent.mp4

# 使用自己的音乐
python3 web-tutorial-video/scripts/render-video.py \
  --video raw/tutorial.webm \
  --srt tutorial.srt \
  --music ./my-music.mp3 \
  --output tutorial-custom-music.mp4
```

## 默认交付

- `tutorial.mp4`：烧录字幕并混入纯音乐的视频。
- `tutorial.srt`：独立字幕文件。
- `tutorial.md`：最终教程文字。

## 背景音乐与署名

默认配乐为 Kevin MacLeod 的 **Meditation Impromptu 02**，使用 CC BY 4.0 授权。发布教程时请保留以下署名：

```text
Music: "Meditation Impromptu 02" by Kevin MacLeod (incompetech.com), licensed under CC BY 4.0.
```

完整来源与许可信息见 `web-tutorial-video/assets/music/LICENSE.txt`。

## 使用注意

- 需要登录、MFA 或 CAPTCHA 时，在可见浏览器中由用户完成，不要将密码或 Cookie 写入录屏文件。
- 避免录制客户数据、账号信息和内部敏感内容。
- 演示外部网站时，不要发送、发布、购买、删除或提交有实际影响的更改。
- 使用用户提供的音乐前，应确认其许可覆盖目标发布场景。

## 仓库说明

只复制 `web-tutorial-video/` 子目录即可安装技能。根目录的 `README.md` 仅用于 GitHub 展示，`.git` 也不需要复制到 Codex skills 目录。
