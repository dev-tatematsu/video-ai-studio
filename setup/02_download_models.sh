#!/bin/bash
# Step 2: MuseTalk モデルのダウンロード
set -e

STUDIO_DIR="$HOME/video-ai-studio"
MODELS_DIR="$STUDIO_DIR/MuseTalk/models"
VENV="$STUDIO_DIR/venv/bin/python"

mkdir -p "$MODELS_DIR"

echo "=== MuseTalk モデルのダウンロード開始 ==="
echo "※ 約5GB のダウンロードが必要です"

# Hugging Face CLI でダウンロード
$VENV -c "
from huggingface_hub import snapshot_download, hf_hub_download
import os

models_dir = '$MODELS_DIR'

# 1. MuseTalk V1.5 (UNet + config)
print('[1/5] MuseTalk V1.5 モデル...')
snapshot_download(
    repo_id='TMElyralab/MuseTalk',
    local_dir=os.path.join(models_dir, 'musetalkV15'),
    ignore_patterns=['*.bin', 'optimizer*'],
    local_dir_use_symlinks=False
)

# 2. SD-VAE (Stable Diffusion VAE)
print('[2/5] SD-VAE モデル...')
snapshot_download(
    repo_id='stabilityai/sd-vae-ft-mse',
    local_dir=os.path.join(models_dir, 'sd-vae-ft-mse'),
    local_dir_use_symlinks=False
)

# 3. DWPose (ポーズ検出)
print('[3/5] DWPose モデル...')
os.makedirs(os.path.join(models_dir, 'dwpose'), exist_ok=True)
hf_hub_download(
    repo_id='yzd-v/DWPose',
    filename='dw-ll_ucoco_384.pth',
    local_dir=os.path.join(models_dir, 'dwpose')
)

# 4. Face Parsing (BiSeNet)
print('[4/5] Face Parsing モデル...')
os.makedirs(os.path.join(models_dir, 'face-parse-bisent'), exist_ok=True)
hf_hub_download(
    repo_id='TMElyralab/MuseTalk',
    filename='face-parse-bisent/79999_iter.pth',
    local_dir=models_dir
)

# 5. ResNet (Face Parsing バックボーン)
print('[5/5] ResNet バックボーン...')
import urllib.request
resnet_url = 'https://download.pytorch.org/models/resnet18-5c106cde.pth'
resnet_path = os.path.join(models_dir, 'face-parse-bisent', 'resnet18-5c106cde.pth')
if not os.path.exists(resnet_path):
    urllib.request.urlretrieve(resnet_url, resnet_path)
    print(f'  ResNet 保存完了: {resnet_path}')

print('✅ 全モデルのダウンロード完了')
"

echo ""
echo "✅ models/ ディレクトリ構造:"
ls "$MODELS_DIR"
