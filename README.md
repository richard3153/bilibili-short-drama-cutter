# 📺 B站短剧 AI 自动剪辑工具

> 纯本地运行 · B站社区规范合规 · 批量处理 · 可视化 Web 界面

抖音短剧剪辑工具的 **B站适配版**：同样的全本地流水线（识别→解说→选片→混音→合规），
但默认输出 **16:9 横屏**、时长更长（1–10 分钟），并改用 **B站社区规范** 的合规与敏感词体系。

---

## ⚠️ 与抖音仓库的关系（重要）

本仓库**不是完全独立的工程**，它复用抖音仓库的代码与重资源：

- `ai_short_video_cutter_bili.py`（入口）会 `import ai_short_video_cutter_pro`（抖音主流程）与共享 helper：
  `tts_chattts_wrapper.py`、`asr_whisper_cpp_wrapper.py`、`config_merger.py`、
  `jellyfish_studio.py`、`_lowbiz_detector.py`。
- 本地大模型（`ChatTTS` / `whisper.cpp` / `faster-whisper`）与 BGM、虚拟环境均来自抖音项目。

**推荐部署方式：把两个仓库克隆为同级兄弟目录**，B站启动脚本会自动在 `../douyin-short-drama-cutter/.venv` 找到共享 venv：

```bash
# 建议的目录结构
workspace/
├── douyin-short-drama-cutter/   # github.com/richard3153/douyin-short-drama-cutter
└── bilibili-short-drama-cutter/  # 本仓库
```

> 如果你只想单独运行 B站，请先按抖音仓库 README 准备好 `.venv`、`models/`、`bgm/` 等，
> 并将 `PYTHONPATH` 指向抖音仓库根目录（见下方「运行」）。

---

## 功能特性

- 与抖音版同源的全本地流水线（ASR/TTS 均本地推理，无需云端付费 API）。
- **16:9 横屏**输出，成片时长 **60 ~ 600 秒**（1–10 分钟）。
- **B站专属合规**：`bilibili_compliance_checker.py` 按 B站社区规范做内容安全 / 敏感词 / AI 标识检测。
- 支持**弹幕互动引导**、创作声明等 B站投稿友好特性。
- 可视化 Web 工作站（端口 `8766`，标准库 `http.server`）。

---

## 系统架构

B站版在抖音流水线基础上替换了「入口 + 引擎 + 合规」三层：

```
原始视频 (raw_videos/)
   │
   ├─[引擎] ai_short_drama_engine.py      ← B站专属剪辑引擎（16:9 / 长时长）
   ├─[入口] ai_short_video_cutter_bili.py ← 复用抖音主流程 ai_short_video_cutter_pro
   ├─[合规] bilibili_compliance_checker.py← B站社区规范
   └─[服务] server_bili.py                ← Web 工作站（端口 8766）
```

### 本仓库核心源码

| 文件 | 说明 |
|------|------|
| `ai_short_drama_engine.py` | B站专属剪辑引擎（16:9 / 1920×1080 / 60–600s） |
| `ai_short_video_cutter_bili.py` | 命令行入口，复用抖音主流程与共享 helper |
| `bilibili_compliance_checker.py` | B站社区规范合规检测 |
| `server_bili.py` | 标准库 `http.server` Web 工作站（端口 8766），服务 `bilibili_gui.html` |
| `bilibili_patch.py` | B站适配补丁（画幅 / 字幕边距 / 时长常量） |
| `bilibili_gui.html` | Web 可视化前端 |
| `run.sh` / `run_gui.sh` | 命令行 / Web 界面启动脚本（自动定位 `../douyin-short-drama-cutter/.venv`） |

> 共享依赖（`ai_short_video_cutter_pro.py` 及 helper、`.venv/`、`models/`、`bgm/`、`music.db`）
> 来自抖音仓库，不重复入库。

---

## 环境依赖

与抖音仓库一致，且需先准备好抖音仓库的 `.venv` / `models` / `bgm`：

- Python 3.11+（共享抖音的 `.venv`）
- FFmpeg
- 本地大模型：`ChatTTS`、`whisper.cpp` + GGML `medium`、`faster-whisper`（均来自抖音项目）
- 第三方包：`Pillow`、`pydub`、`moviepy`、`numpy`、`opencv-python`、`edge-tts`、`torch` 等

---

## 安装

```bash
# 1. 克隆为兄弟目录（推荐）
git clone https://github.com/richard3153/douyin-short-drama-cutter.git ../douyin-short-drama-cutter
git clone https://github.com/richard3153/bilibili-short-drama-cutter.git

# 2. 按抖音仓库 README 准备 .venv / models / bgm（本仓库直接复用）
#    （若已单独准备好，可跳过上一步，仅把 PYTHONPATH 指向抖音仓库根目录）

# 3. 准备素材目录
mkdir -p raw_videos bgm output_videos narration subtitles
```

---

## 使用方法

### 方式一：可视化界面（推荐）

```bash
bash run_gui.sh
```

浏览器自动打开 **http://localhost:8766**。

### 方式二：命令行

```bash
bash run.sh
# 或单独指定
PYTHONPATH=/path/to/douyin-short-drama-cutter .venv/bin/python ai_short_video_cutter_bili.py
```

---

## 输出规格（默认）

| 参数 | 值 |
|------|------|
| 画幅 | 16:9（横屏，1920×1080） |
| 时长 | 60 ~ 600 秒（1–10 分钟） |
| 帧率 | 30 fps |
| 音频 | AAC，解说音量 2.50 / BGM 0.15 |
| 字幕 | 白字黑边，底部居中（更宽边距） |
| AI 标识 | 片尾 AI 生成声明 + B站创作声明 |

---

## B站 vs 抖音 核心差异

| 维度 | B站 | 抖音 |
|------|------|------|
| 默认画幅 | 16:9 横屏 | 9:16 竖屏 |
| 时长范围 | 60–600 秒 | 60–180 秒 |
| 合规体系 | B站社区规范 | 抖音审核规则 |
| AI 标识 | 创作声明 + 来源标注 | 片尾 AI 生成标签 |
| 弹幕互动 | 支持弹幕引导 | 不支持 |

---

## 可调参数

编辑 `ai_short_drama_engine.py` / `ai_short_video_cutter_bili.py` 中的 `CONFIG`：

```python
CONFIG = {
    "aspect_ratio": "16:9",
    "width": 1920, "height": 1080,
    "min_duration": 60,        # 成片最短时长(秒)
    "max_duration": 600,       # 成片最长时长(秒)
    "bgm_volume": 0.15,
    "narration_volume": 2.50,
    "asr_model": "medium",
}
```

---

## 许可证

与抖音仓库一致：仅供学习与个人创作使用，素材/BGM/字体须有授权，生成内容须遵守平台规范。
