#!/bin/bash
# video-ai-studio の仮想環境を有効化するスクリプト
# 使用方法: source activate.sh

STUDIO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV="$STUDIO_DIR/venv"
BUN="$HOME/.bun/bin"
NODE_PATH="$(which node)"

export PATH="$BUN:$PATH"
export PYTHONPATH="$STUDIO_DIR/workflow:$STUDIO_DIR/MuseTalk:$PYTHONPATH"
export PYTORCH_ENABLE_MPS_FALLBACK=1   # MPS 未対応オペレーションを CPU にフォールバック
export TOKENIZERS_PARALLELISM=false     # 並列処理の警告を抑制

source "$VENV/bin/activate"

echo "✅ video-ai-studio 環境が有効化されました"
echo ""
echo "利用可能なコマンド:"
echo "  python pipeline.py <動画.mp4> --avatar <アバター.jpg>  # メインパイプライン"
echo "  python workflow/transcribe.py <動画.mp4>               # 文字起こしのみ"
echo "  python workflow/generate_audio.py 'テキスト'           # 音声生成のみ"
echo "  python workflow/create_avatar.py <画像> <音声.wav>     # アバター生成のみ"
echo "  node hyperframes/packages/cli/dist/cli.js --help       # Hyperframes"
echo ""
if [ -n "$HF_TOKEN" ]; then
    echo "🎵 TTS: Qwen3-TTS MLX (HF_TOKEN 設定済)"
else
    echo "🎵 TTS: macOS TTS (Kyoko/Eddy 等)"
    echo "   Qwen3-TTS MLX を使うには HF_TOKEN を設定: bash setup/03_hf_token.sh"
fi
echo ""
echo "📁 プロジェクトディレクトリ: $STUDIO_DIR"
