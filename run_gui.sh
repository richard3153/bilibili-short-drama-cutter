#!/bin/bash
# B站短剧AI剪辑工具 - Web可视化界面启动脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SHARED_VENV="$SCRIPT_DIR/../douyin-short-drama-cutter/.venv"

PYTHON="$SHARED_VENV/bin/python3"
if [ ! -f "$PYTHON" ]; then
    PYTHON="python3"
    echo "⚠️ 使用系统 Python"
fi

export PYTHONPATH="$SCRIPT_DIR:$SHARED_VENV/lib/python3.11/site-packages"

cd "$SCRIPT_DIR"
echo "🎬 正在启动B站短剧剪辑工作站..."
echo "📐 画幅: 16:9 (1920×1080)"
echo "🛡️ 合规: B站社区规范"
echo "🔗 模型: 共享抖音项目"
echo ""
exec "$PYTHON" "$SCRIPT_DIR/server_bili.py"
