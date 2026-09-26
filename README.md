# B站短剧解说自动剪辑工具

> 纯本地运行 · B站社区规范合规 · 批量处理 · 可视化 Web 界面

抖音短剧剪辑工具的 **B站适配版**：同样的全本地流水线（识别→解说→选片→混音→合规），
但默认输出 **16:9 横屏**、时长更长（1–10 分钟），并改用 **B站社区规范** 的合规与敏感词体系。

---

## 与抖音仓库的关系（共享模块已内置）

本仓库在**根目录内置了抖音项目的共享源码副本**，因此可**独立运行**，无需克隆抖音仓库：

- `ai_short_video_cutter_pro.py`（抖音主流程，B站入口直接 `import` 它）
- `compliance_checker.py`、`tts_chattts_wrapper.py`、`asr_whisper_cpp_wrapper.py`、
  `config_merger.py`、`jellyfish_studio.py`、`_lowbiz_detector.py`（共享 helper）

这些文件与抖音仓库保持一致（由本仓库维护副本）。其余重资源（本地大模型、BGM、虚拟环境）仍由本地自备。

> 若你同时维护抖音仓库，可定期把上述文件从抖音仓库同步到本仓库以保持一致。

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
| `run.sh` / `run_gui.sh` | 命令行 / Web 界面启动脚本（自动定位本目录 `.venv`） |

> 共享模块（`ai_short_video_cutter_pro.py` 及 helper）已作为副本**内置本仓库**，无需依赖抖音目录；
> `.venv/`、`models/`、`bgm/`、`music.db` 等重资源仍不入库，需本地自备（可与抖音项目共用同一份）。

---

## 目录结构

```
.
├── ai_short_drama_engine.py         # B站专属剪辑引擎（16:9 / 1920×1080 / 60–600s）
├── ai_short_video_cutter_bili.py    # 命令行入口
├── bilibili_compliance_checker.py   # B站社区规范合规
├── server_bili.py                   # Web 工作站（端口 8766）
├── bilibili_patch.py                # B站适配补丁
├── bilibili_gui.html                 # Web 前端
├── run.sh / run_gui.sh              # 启动脚本
├── # ── 以下为从抖音仓库内置的共享模块（副本，保持一致即可）──
├── ai_short_video_cutter_pro.py     # 抖音主流程
├── compliance_checker.py
├── tts_chattts_wrapper.py
├── asr_whisper_cpp_wrapper.py
├── config_merger.py
├── jellyfish_studio.py
├── _lowbiz_detector.py
├── raw_videos/  bgm/  output_videos/  narration/  subtitles/  # 占位目录
├── assets/  fonts/  logs/  drama_memory/  tmp_frames/          # 占位目录
```

带「占位」的目录仅保留结构（内含 `.gitkeep`），目录内实际文件不入库。

## 环境依赖

与抖音仓库一致（Python 3.11+ / FFmpeg / 本地大模型 ChatTTS、whisper.cpp、faster-whisper）：

- Python 3.11+（本仓库自己的 `.venv`）
- FFmpeg
- 本地大模型：`ChatTTS`、`whisper.cpp` + GGML `medium`、`faster-whisper`（均来自抖音项目）
- 第三方包：`Pillow`、`pydub`、`moviepy`、`numpy`、`opencv-python`、`edge-tts`、`torch` 等

---

## 安装

本仓库已内置抖音共享模块，**克隆本仓库即可独立运行**（无需克隆抖音仓库）：

```bash
# 1. 克隆本仓库
git clone https://github.com/richard3153/bilibili-short-drama-cutter.git
cd bilibili-short-drama-cutter

# 2. 准备本地虚拟环境与模型（与抖音仓库一致）
uv venv .venv
uv pip install pillow pydub moviepy numpy opencv-python edge-tts torch
#    ChatTTS / whisper.cpp(GGML medium) / faster-whisper 模型放到 models/

# 3. 准备素材目录（占位目录已随仓库创建，也可手动建）
mkdir -p raw_videos bgm output_videos narration subtitles
```

> 注：`.venv/`、`models/`、`bgm/` 等重资源不入库，需本地自备（与抖音仓库相同）。

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
PYTHONPATH=. .venv/bin/python ai_short_video_cutter_bili.py
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

## Ollama 本地大模型集成

解说脚本由本地部署的 **Ollama** 负责生成（不调用任何云端付费 LLM API）。B站引擎 `ai_short_drama_engine.py`
与抖音主流程 `ai_short_video_cutter_pro.py` 共用同一套 Ollama 调用逻辑。

### 安装与启动

```bash
# 1. 安装 Ollama（https://ollama.com），确保本地服务已启动（默认监听 11434）
ollama serve          # 若未随系统自启

# 2. 拉取解说所用模型（当前默认 qwen3.5:4b）
ollama pull qwen3.5:4b
```

### 集成方式（代码层面）

- 统一调用函数 `_call_ollama_retry(prompt, agent_name, timeout=90, retries=2)`，向
  `http://localhost:11434/api/generate` 发送 POST 请求，请求体示例：

  ```json
  {
    "model": "qwen3.5:4b",
    "prompt": "<清洗后的提示词>",
    "stream": false,
    "think": false,
    "options": { "temperature": 0.5, "num_predict": 2000 }
  }
  ```

- **多 Agent 分工**：通过 `agent_name` 区分任务，例如 `narration_viral`（爆款解说生成）、
  `highlight_detection`（高光片段检测）、`bgm_selection`（BGM 匹配）、`narration_filler`（结尾填充语）等。
- **结构化输出**：需要 JSON 的场景（如高光检测、反同质化）使用 `"format": "json"` 引导生成。
- **重试与退避**：调用失败按指数退避重试（等待 3s / 6s），全部失败后返回 `None` 走兜底逻辑。
- **冷启动预热**：`server_bili.py` 启动时调用 `warmup_ollama()`，先发一个极小请求把模型加载进显存，
  消除首次调用的冷启动延迟。

### 切换模型 / 调参

- 切换模型：修改 `_call_ollama_retry` 与 `warmup_ollama` 中的 `"model"` 字段
  （如 `qwen3.5:4b` → 其他已 `ollama pull` 的模型）。
- 调参：各 Agent 的 `temperature` / `num_predict` 由 `_get_llm_params(agent_name)` 控制，
  可按任务在源码中调整。

### 常见问题

- Ollama 未启动或 `11434` 不可达 → 解说生成失败，流水线会停止并提示，请先 `ollama serve`。
- 首次调用慢属正常（模型加载），服务启动后的预热可显著缓解。

## 许可证

与抖音仓库一致：仅供学习与个人创作使用，素材/BGM/字体须有授权，生成内容须遵守平台规范。
