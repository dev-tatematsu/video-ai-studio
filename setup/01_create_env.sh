#!/bin/bash
# Step 1: Python 3.12 仮想環境の作成
set -e

PYTHON=/opt/homebrew/bin/python3.12
VENV_DIR="$HOME/video-ai-studio/venv"

echo "=== Python 3.12 仮想環境を作成 ==="
$PYTHON -m venv "$VENV_DIR"

echo "=== pip をアップグレード ==="
"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel

echo "✅ 仮想環境作成完了: $VENV_DIR"
echo "   有効化: source $VENV_DIR/bin/activate"
