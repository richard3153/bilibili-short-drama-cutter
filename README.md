# B站短剧解说自动剪辑工具

> 纯本地运行 · 完全自包含（无需抖音仓库）· B站社区规范合规 · 批量处理 · 可视化 Web 界面

基于抖音短剧剪辑引擎的 **B站适配版**：同样的全本地流水线（语音识别 → 剧情解说 → 智能选片 → 混音 → 合规），
但默认输出 **16:9 横屏**、时长更长（1–10 分钟），并改用 **B站社区规范** 的合规与敏感词体系。

**本仓库已完全自包含**：抖音项目的共享源码（`ai_short_video_cutter_pro.py` 及 helper）已作为副本内置在根目录，
克隆本仓库即可独立运行，不再依赖抖音仓库或任何外部目录。

---

## 特性

- 全本地流水线，ASR / TTS / LLM 解说均本地推理，不调用任何云端付费 API。
- **16:9 横屏**输出，成片时长 **60 ~ 600 秒**（1–10 分钟）。
- **B站专属合规**：`bilibili_compliance_checker.py` 按 B站社区规范做内容安全 / 敏感词 / AI 标识检测。
- 弹幕互动引导、创作声明等 B站投稿友好特性。
- 可视化 Web 工作站（端口 `8766`，标准库 `http.server`，零额外依赖）。

---

## 系统架构

```
原始视频 (raw_videos/)
   │
   ├─[引擎]  ai_short_drama_engine.py        ← B站专属剪辑引擎（16:9 / 长时长）
   ├─[入口]  ai_short_video_cutter_bili.py   ← 复用内置的抖音主流程 ai_short_video_cutter_pro
   ├─[合规]  bilibili_compliance_checker.py  ← B站社区规范
   ├─[适配]  bilibili_patch.py               ← 画幅 / 字幕边距 / 时长 / 敏感词补丁
   └─[服务]  server_bili.py                  ← Web 工作站（端口 8766）
```

---

## 目录结构与核心文件

```
.
├── ai_short_drama_engine.py         # B站专属剪辑引擎（16:9 / 1920×1080 / 60–600s）
├── ai_short_video_cutter_bili.py    # 命令行入口（import 内置的抖音主流程 + 应用 B站补丁）
├── bilibili_compliance_checker.py   # B站社区规范合规
├── bilibili_patch.py                # B站适配补丁
├── server_bili.py                   # Web 工作站（端口 8766）
├── bilibili_gui.html                # Web 可视化前端
├── run.sh / run_gui.sh              # 启动脚本（自动定位本目录 .venv）
│
├── # ── 内置的共享模块（抖音主流程副本，本仓库维护）──
├── ai_short_video_cutter_pro.py     # 抖音主流程（解说 / 选片 / 混音核心）
├── compliance_checker.py            # 通用合规检测 helper
├── tts_chattts_wrapper.py           # ChatTTS 解说封装（兜底 edge-tts / gTTS）
├── asr_whisper_cpp_wrapper.py       # whisper.cpp 识别封装（兜底 faster-whisper）
├── config_merger.py                 # 三层配置合并（用户 > 智能 > 默认）
├── jellyfish_studio.py              # 视觉 / 特效 helper
├── _lowbiz_detector.py              # 低俗内容检测
│
├── config.json / user_config.json   # 配置（已内置，可改）
├── raw_videos/ bgm/ output_videos/ narration/ subtitles/  # 占位目录（.gitkeep）
└── assets/ fonts/ logs/ drama_memory/ tmp_frames/          # 占位目录（.gitkeep）
```

> `.venv/`、`models/`、`bgm/`、`music.db`、`whisper.cpp/` 等重资源**不入库**，需本地自备。
> 内置的共享模块（`ai_short_video_cutter_pro.py` 及 helper）与抖音仓库同源，若同时维护抖音仓库可定期同步以保持一致。

---

## 环境依赖

- Python 3.11+（本仓库自己的 `.venv`）
- FFmpeg
- 本地大模型：
  - `ChatTTS`（解说语音，兜底 `edge-tts` / `gTTS`）
  - `whisper.cpp` + GGML `medium` 模型（语音识别，兜底 `faster-whisper`）
  - `Ollama` + `qwen3.5:4b`（解说脚本生成，详见下方「Ollama 集成」）
- 第三方包：`Pillow`、`pydub`、`moviepy`、`numpy`、`opencv-python`、`edge-tts`、`torch` 等

---

## 安装

```bash
# 1. 克隆本仓库
git clone https://github.com/richard3153/bilibili-short-drama-cutter.git
cd bilibili-short-drama-cutter

# 2. 创建本地虚拟环境并安装依赖
uv venv .venv
uv pip install pillow pydub moviepy numpy opencv-python edge-tts torch

# 3. 准备本地大模型
#    - ChatTTS：按 ChatTTS 官方说明下载模型到 models/
#    - whisper.cpp：编译 whisper.cpp，并把 GGML medium 模型放到 models/
#    - Ollama：见下方「Ollama 集成」章节（ollama pull qwen3.5:4b）

# 4. 素材目录（占位目录已随仓库创建，也可手动建）
mkdir -p raw_videos bgm output_videos narration subtitles
```

> 重资源（`models/`、`bgm/`、`music.db`、`whisper.cpp/`）不入库；若本机已跑抖音仓库，可直接复用同一份（软链或复制均可）。

---

## 使用方法

### 方式一：可视化界面（推荐）

```bash
bash run_gui.sh
```

浏览器打开 **http://localhost:8766**，上传 `raw_videos/` 中的视频即可批量处理，成片输出到 `output_videos/`。

### 方式二：命令行

```bash
bash run.sh
# 或显式指定解释器
PYTHONPATH=. .venv/bin/python ai_short_video_cutter_bili.py
```

---

## 输出规格（默认）

| 参数 | 值 |
|------|------|
| 画幅 | 16:9 横屏（1920×1080） |
| 时长 | 60 ~ 600 秒（1–10 分钟） |
| 帧率 | 30 fps |
| 音频 | AAC；解说音量 2.50 / 原声 0.10 / BGM 0.15 |
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

## 配置

配置为三层优先级：**用户配置 > 智能检测 > 默认配置**（`config_merger.py` 负责合并）。

- `user_config.json`：用户自定义参数（最高优先级），覆盖默认与智能值。
- `smart_config.json`：（可选）智能检测结果，不存在则跳过。
- `config.json`：基础配置（已内置）。
- 代码内 `CONFIG`（`ai_short_drama_engine.py` / `ai_short_video_cutter_bili.py`）：引擎默认参数。

常用可调参数示例：

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

## Ollama 本地大模型集成

解说脚本由本地部署的 **Ollama** 负责生成（不调用任何云端付费 LLM API）。

### 安装与启动

```bash
ollama serve            # 确保本地服务已启动（默认监听 11434）
ollama pull qwen3.5:4b  # 拉取解说所用模型
```

### 集成方式（代码层面）

- 统一调用函数 `_call_ollama_retry(prompt, agent_name, timeout=90, retries=2)`，向
  `http://localhost:11434/api/generate` 发送 POST 请求（`stream:false`、`think:false`、
  `options` 由 `_get_llm_params(agent_name)` 返回 `{temperature, num_predict}`）。
- **多 Agent 分工**：`narration_viral`（爆款解说）、`highlight_detection`（高光检测）、
  `bgm_selection`（BGM 匹配）、`narration_filler`（结尾填充）等。
- **结构化输出**：需 JSON 的场景用 `"format":"json"` 引导。
- **重试与退避**：失败按指数退避重试（3s / 6s），全失败返回 `None` 走兜底。
- **冷启动预热**：`server_bili.py` 启动时 `warmup_ollama()` 先发极小请求加载模型，消除首次延迟。

### 切换模型 / 调参

- 切换模型：改 `_call_ollama_retry` 与 `warmup_ollama` 中的 `"model"` 字段。
- 调参：各 Agent 的 `temperature` / `num_predict` 由 `_get_llm_params(agent_name)` 控制。

### 常见问题

- Ollama 未启动或 `11434` 不可达 → 解说生成失败，流水线停止并提示，请先 `ollama serve`。
- 首次调用慢属正常（模型加载），服务启动后的预热可显著缓解。

---

## 许可证

仅供学习与个人创作使用；素材 / BGM / 字体须有授权；生成内容须遵守 B站社区规范。
