# video-ai-studio セットアップガイド

M1 Mac (Apple Silicon) でセミナー動画をアバター再演動画に変換するパイプラインの再現手順。

---

## システム要件

| 項目 | 要件 |
|------|------|
| チップ | Apple M1 以上 (M2/M3/M4 でも動作) |
| RAM | 16GB 以上推奨 |
| ストレージ | 20GB 以上の空き |
| macOS | 13 Ventura 以上 |
| Python | 3.12 (Homebrew) |
| Homebrew | インストール済み |
| ffmpeg | Homebrew でインストール |

---

## ディレクトリ構成

```
~/video-ai-studio/
├── pipeline.py                    # メインパイプライン
├── activate.sh                    # 環境有効化スクリプト
├── workflow/
│   ├── transcribe.py              # STEP1: MLX-Whisper 文字起こし
│   ├── generate_audio.py          # STEP2: Qwen3-TTS / macOS TTS 音声生成
│   ├── create_avatar.py           # STEP3: MuseTalk リップシンク生成
│   └── compose_video.py           # STEP4: FFmpeg 動画合成
├── MuseTalk/                      # MuseTalk リポジトリ (git clone)
│   ├── models/
│   │   ├── musetalkV15/           # MuseTalk V1.5 UNet モデル
│   │   │   ├── musetalk.json
│   │   │   ├── unet.pth
│   │   │   └── musetalkV15/
│   │   │       ├── musetalk.json
│   │   │       └── unet.pth
│   │   ├── sd-vae/                # SD-VAE (MuseTalk 用)
│   │   ├── sd-vae-ft-mse/         # SD-VAE ft-mse (Stability AI)
│   │   ├── dwpose/
│   │   │   └── dw-ll_ucoco_384.pth
│   │   ├── face-parse-bisent/
│   │   │   ├── 79999_iter.pth
│   │   │   └── resnet18-5c106cde.pth
│   │   └── whisper/
│   │       ├── config.json
│   │       ├── preprocessor_config.json
│   │       └── pytorch_model.bin
│   └── scripts/
│       └── inference.py
├── hyperframes/                   # Hyperframes (git clone, 動画合成フレームワーク)
├── venv/                          # Python 3.12 仮想環境
├── output/
│   ├── audio/                     # 生成音声 WAV
│   ├── transcripts/               # 文字起こし JSON/SRT
│   └── video/                     # 生成動画
└── setup/
    ├── 01_create_env.sh
    ├── 02_download_models.sh
    └── 03_hf_token.sh
```

---

## 再構築手順

### 0. 事前準備

```bash
# Homebrew インストール (未インストールの場合)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 必要ツールのインストール
brew install python@3.12 ffmpeg git

# ffprobe の確認 (ffmpeg に同梱)
ffprobe -version
```

### 1. プロジェクトディレクトリ作成

```bash
mkdir -p ~/video-ai-studio
cd ~/video-ai-studio
```

### 2. MuseTalk リポジトリの取得

```bash
cd ~/video-ai-studio
git clone https://github.com/TMElyralab/MuseTalk.git
```

### 3. Hyperframes の取得

```bash
cd ~/video-ai-studio
git clone https://github.com/hyperframes/hyperframes.git
cd hyperframes && bun install
```

### 4. Python 仮想環境の作成

```bash
cd ~/video-ai-studio
/opt/homebrew/bin/python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
```

### 5. Python パッケージのインストール

#### 5-1. MLX 系 (Apple Silicon 必須)

```bash
pip install mlx mlx-lm mlx-audio mlx-whisper mlx-metal
```

#### 5-2. PyTorch (MPS バックエンド)

```bash
# PyTorch 2.12.0 + MPS
pip install torch==2.12.0 torchvision==0.27.0
```

#### 5-3. MuseTalk 依存パッケージ

```bash
pip install diffusers==0.30.2 accelerate==1.13.0 transformers==5.8.1 \
    huggingface_hub==1.15.0 safetensors omegaconf einops \
    mediapipe opencv-contrib-python==4.13.0.92 \
    imageio[ffmpeg] ffmpeg-python moviepy \
    librosa soundfile sounddevice \
    mmengine yapf addict
```

#### 5-4. その他ユーティリティ

```bash
pip install numpy pillow scipy scikit-learn \
    pyyaml requests tqdm rich \
    playwright tiktoken sentencepiece
```

### 6. MuseTalk モデルのダウンロード (約5GB)

HuggingFace からモデルを取得する。`HF_TOKEN` 設定後に実行。

```bash
cd ~/video-ai-studio
source venv/bin/activate
python setup/02_download_models.sh
```

または手動で:

```python
from huggingface_hub import snapshot_download, hf_hub_download
import urllib.request, os

MODELS = "MuseTalk/models"

# 1. MuseTalk V1.5
snapshot_download("TMElyralab/MuseTalk",
    local_dir=f"{MODELS}/musetalkV15",
    ignore_patterns=["*.bin", "optimizer*"],
    local_dir_use_symlinks=False)

# 2. SD-VAE (MuseTalk 内蔵版)
snapshot_download("TMElyralab/MuseTalk",
    local_dir=f"{MODELS}/sd-vae",
    local_dir_use_symlinks=False)

# 3. SD-VAE ft-mse (Stability AI)
snapshot_download("stabilityai/sd-vae-ft-mse",
    local_dir=f"{MODELS}/sd-vae-ft-mse",
    local_dir_use_symlinks=False)

# 4. DWPose
hf_hub_download("yzd-v/DWPose", "dw-ll_ucoco_384.pth",
    local_dir=f"{MODELS}/dwpose")

# 5. Face Parsing
hf_hub_download("TMElyralab/MuseTalk", "face-parse-bisent/79999_iter.pth",
    local_dir=MODELS)

# 6. ResNet バックボーン
urllib.request.urlretrieve(
    "https://download.pytorch.org/models/resnet18-5c106cde.pth",
    f"{MODELS}/face-parse-bisent/resnet18-5c106cde.pth")
```

**Whisper モデル** (`MuseTalk/models/whisper/`) は MuseTalk が初回実行時に自動ダウンロードするが、事前に置いておく場合は `openai/whisper-tiny` の変換済み PyTorch ウェイト (`pytorch_model.bin`, `config.json`, `preprocessor_config.json`) を配置する。

### 7. 環境変数の設定

`~/.zshrc` に追記:

```bash
# Qwen3-TTS MLX (任意: HuggingFace アカウントのトークン)
export HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxxxxxxxx"

# MPS フォールバック (MPS 未対応オペレーションを CPU へ)
export PYTORCH_ENABLE_MPS_FALLBACK=1

# tokenizers の並列処理警告を抑制
export TOKENIZERS_PARALLELISM=false
```

```bash
source ~/.zshrc
```

HF_TOKEN の取得: https://huggingface.co/settings/tokens (Read 権限で十分)

### 8. activate.sh の配置

`~/video-ai-studio/activate.sh` として以下を保存:

```bash
#!/bin/bash
STUDIO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV="$STUDIO_DIR/venv"
BUN="$HOME/.bun/bin"

export PATH="$BUN:$PATH"
export PYTHONPATH="$STUDIO_DIR/workflow:$STUDIO_DIR/MuseTalk:$PYTHONPATH"
export PYTORCH_ENABLE_MPS_FALLBACK=1
export TOKENIZERS_PARALLELISM=false

source "$VENV/bin/activate"
```

使用方法: `source activate.sh`

---

## 使用方法

### 環境の有効化

```bash
cd ~/video-ai-studio
source activate.sh
```

### メインパイプライン

```bash
# 基本実行
python pipeline.py input.mp4 --avatar avatar.jpg

# オプション付き (タイトルカード・字幕・比較動画)
python pipeline.py input.mp4 \
  --avatar avatar.jpg \
  --title "セミナーハイライト" \
  --subtitles \
  --compare

# 声クローン使用
python pipeline.py input.mp4 \
  --avatar avatar.jpg \
  --voice-clone reference_voice.wav
```

### 各ステップ単独実行

```bash
# STEP1: 文字起こしのみ
python workflow/transcribe.py input.mp4

# STEP2: 音声生成のみ
python workflow/generate_audio.py 'テキスト内容'

# STEP3: アバター生成のみ
python workflow/create_avatar.py avatar.jpg output/audio/merged_audio.wav

# STEP4: 動画合成のみ (compose_video.py を直接呼び出し)
python -c "from compose_video import *; ..."
```

### パイプラインのオプション一覧

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--avatar` | 必須 | アバター画像(.jpg)または動画(.mp4) |
| `--output-dir` | `output` | 出力ディレクトリ |
| `--lang` | `ja` | 言語コード |
| `--voice` | `Chelsie` | TTS 音声名 |
| `--voice-clone` | なし | 声クローン参照音声(.wav) |
| `--whisper-model` | `mlx-community/whisper-large-v3-turbo` | Whisper モデル |
| `--title` | なし | タイトルカードテキスト |
| `--subtitles` | off | 字幕を動画に焼き込む |
| `--compare` | off | オリジナルとの比較動画を生成 |
| `--bbox-shift` | `0` | 口元バウンディングボックス調整(-10〜10) |
| `--batch-size` | `4` | 処理バッチサイズ(M1 16GB では 4〜8 推奨) |

---

## パイプライン詳細

### STEP 1: MLX-Whisper 文字起こし

- モデル: `mlx-community/whisper-large-v3-turbo`
- M1 Neural Engine で高速処理
- 出力: `output/transcripts/<stem>_transcript.json` / `.srt`

### STEP 2: 音声生成

TTS バックエンドの優先順位:

1. **Qwen3-TTS MLX** (`HF_TOKEN` 設定時): 高品質 AI 音声
   - モデル: `mlx-community/Qwen3-TTS-MLX-4bit`
   - 声: Chelsie / Ethan / Vivian / River / Aaliyah / Cole
2. **macOS TTS** (フォールバック): 常に利用可能
   - 日本語音声: Kyoko / Eddy / Flo / Reed / Rocko / Sandy / Shelley

### STEP 3: MuseTalk リップシンク生成

- モデル: MuseTalk V1.5 (MPS バックエンド)
- `PYTORCH_ENABLE_MPS_FALLBACK=1` で MPS 未対応演算を CPU にフォールバック
- `float32` 使用 (M1 では float16 より安定)
- フォールバック: モデル未配置時は ffmpeg で静止画+音声合成

### STEP 4: 動画合成 (FFmpeg)

- タイトルカード生成 → アバター動画 → 字幕焼き込み → 結合
- VideoToolbox (`h264_videotoolbox`) で GPU エンコード
- オプション: オリジナルとのサイドバイサイド比較動画

---

## 既知の問題と対処

### MuseTalk が対話プロンプトで止まる

**症状:**
```
Enter command: <target>|all <time>|-1 <command>[ <argument>]
```

**原因:** `inference.py` がフレーム生成後に対話ループへ入り、stdin を待ち続ける。

**修正済み** (`workflow/create_avatar.py` line 91):
```python
# 修正前
result = subprocess.run(cmd, cwd=MUSETALK_DIR, env=env, text=True)

# 修正後
result = subprocess.run(cmd, cwd=MUSETALK_DIR, env=env, text=True, stdin=subprocess.DEVNULL)
```

### MPS エラー: 一部演算が MPS 非対応

**対処:** `PYTORCH_ENABLE_MPS_FALLBACK=1` を環境変数に設定済み (activate.sh に含む)。

### Qwen3-TTS が失敗する

**対処:** `HF_TOKEN` が未設定か期限切れの可能性。自動的に macOS TTS にフォールバックするので処理は続行される。

### torch バージョン競合

MuseTalk の `requirements.txt` は古いバージョンを要求するが、`torch==2.12.0` + MPS で動作確認済み。インストール時に MuseTalk の requirements.txt を直接使わず、本ドキュメントの手順に従うこと。

---

## 依存関係バージョン (動作確認済み)

```
mlx==0.31.2
mlx-audio==0.4.3
mlx-lm==0.31.3
mlx-metal==0.31.2
mlx-whisper==0.4.3
torch==2.12.0
torchvision==0.27.0
diffusers==0.30.2
accelerate==1.13.0
transformers==5.8.1
huggingface_hub==1.15.0
mediapipe==0.10.35
opencv-python==4.13.0.92
opencv-contrib-python==4.13.0.92
librosa==0.11.0
soundfile==0.13.1
moviepy==2.2.1
ffmpeg-python==0.2.0
omegaconf==2.3.0
einops==0.8.2
mmengine==0.10.7
numpy==2.4.5
pillow==11.3.0
```

---

## ファイル出力マップ

```
output/
├── transcripts/
│   ├── <stem>_transcript.json   # 文字起こし全文 + セグメント
│   ├── <stem>_transcript.txt    # テキストのみ
│   └── <stem>.srt               # 字幕ファイル
├── audio/
│   ├── seg_XXXX.wav             # セグメント別音声
│   └── merged_audio.wav         # 結合音声
└── video/
    ├── <stem>_avatar.mp4        # リップシンクアバター動画
    ├── <stem>_subtitled.mp4     # 字幕付き動画
    ├── <stem>_final.mp4         # 最終動画 (タイトル+本編)
    └── <stem>_compare.mp4       # 比較動画 (--compare 指定時)
```
