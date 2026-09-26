#!/bin/bash
# B站短剧AI剪辑工具 - 命令行启动脚本
# 纯本地运行，模型与抖音项目共享

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SHARED_VENV="$SCRIPT_DIR/.venv"

PYTHON="$SHARED_VENV/bin/python3"
if [ ! -f "$PYTHON" ]; then
    PYTHON="python3"
    echo "⚠️ 使用系统 Python (共享 venv 不可用)"
else
    echo "✅ 使用共享 venv: $SHARED_VENV"
fi

export PYTHONPATH="$SCRIPT_DIR:$SHARED_VENV/lib/python3.11/site-packages"

cd "$SCRIPT_DIR"
exec "$PYTHON" "$SCRIPT_DIR/ai_short_video_cutter_bili.py" "$@"
