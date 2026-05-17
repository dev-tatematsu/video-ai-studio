#!/bin/bash
# Qwen3-TTS MLX を使うための HuggingFace トークン設定
# ※ macOS TTS を使う場合はこのステップは不要

echo "=== HuggingFace トークン設定 ==="
echo ""
echo "Qwen3-TTS MLX モデルを使用するには:"
echo "1. https://huggingface.co/ でアカウント作成 (無料)"
echo "2. https://huggingface.co/settings/tokens でトークン生成"
echo "   Type: Read (読み取り専用で十分)"
echo "3. 以下を ~/.zshrc に追加:"
echo ""
echo "   export HF_TOKEN='your_token_here'"
echo ""
echo "4. source ~/.zshrc を実行"
echo ""

if [ -n "$HF_TOKEN" ]; then
    echo "✅ HF_TOKEN は設定済みです"
    echo "   Qwen3-TTS MLX が利用可能です"

    # モデルアクセスを確認
    python3 -c "
from huggingface_hub import HfApi
api = HfApi()
try:
    info = api.model_info('mlx-community/Qwen3-TTS-MLX-4bit')
    print(f'✅ Qwen3-TTS MLX-4bit アクセス確認: {info.id}')
except Exception as e:
    print(f'⚠️  アクセスエラー: {e}')
    print('   モデルへのアクセス許可が必要な場合があります')
    print('   https://huggingface.co/mlx-community/Qwen3-TTS-MLX-4bit でリクエスト')
" 2>/dev/null
else
    echo "⚠️  HF_TOKEN が未設定です"
    echo "   現在は macOS TTS (Kyoko/Eddy等) を使用します"
    echo ""
    echo "   macOS TTS を使うなら: export TTS_BACKEND=macos"
fi
