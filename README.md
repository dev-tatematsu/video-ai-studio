# Video AI Studio — M1 Mac セットアップ

セミナー切り抜き → アバター再演ワークフロー  
**M1 iMac 16GB 最適化 | MLX + MPS + VideoToolbox**

---

## アーキテクチャ

```
セミナー動画
    ↓
[MLX-Whisper]  ─── Neural Engine ─── 文字起こし (.json / .srt)
    ↓
[Qwen3-TTS]    ─── MLX GPU ────────── アバター音声 (.wav)
  (フォールバック: macOS say コマンド)
    ↓
[MuseTalk]     ─── MPS (Metal) ────── リップシンク動画 (.mp4)
    ↓
[FFmpeg]       ─── VideoToolbox ───── 最終動画合成
[Hyperframes]  ─── Node.js ────────── タイトルカード・字幕
```

---

## クイックスタート

```bash
# 環境を有効化
source activate.sh

# フルパイプライン実行
python pipeline.py seminar.mp4 \
  --avatar avatar.jpg \
  --title "セミナーハイライト" \
  --subtitles \
  --compare
```

### 個別ステップ

```bash
# 1. 文字起こしのみ
python workflow/transcribe.py seminar.mp4 ja

# 2. 音声生成 (macOS TTS)
python workflow/generate_audio.py 'テキスト' output.wav kyoko

# 2. 音声生成 (Qwen3-TTS ※HF_TOKEN必要)
HF_TOKEN=xxx python workflow/generate_audio.py 'テキスト' output.wav Chelsie

# 3. アバター動画 (MuseTalk モデルダウンロード後)
python workflow/create_avatar.py avatar.jpg audio.wav output.mp4

# 4. 動画合成
python workflow/compose_video.py side original.mp4 avatar.mp4 output.mp4
```

---

## セットアップ状況

| コンポーネント | バージョン | 状態 |
|---|---|---|
| MLX | 0.31.2 | ✅ Neural Engine |
| mlx-whisper | 0.4.3 | ✅ 日本語対応 |
| Qwen3-TTS (mlx-audio) | 0.4.3 | ⚠️ HF_TOKEN 必要 |
| macOS TTS | ビルトイン | ✅ 日本語9音声 |
| PyTorch | 2.12.0 | ✅ MPS バックエンド |
| MuseTalk | v1.5 | 🔄 モデル要ダウンロード |
| FFmpeg | 7.1.1 | ✅ VideoToolbox |
| Hyperframes | 0.6.11 | ✅ ビルド済み |

---

## MuseTalk モデルのダウンロード (約5GB)

```bash
# MuseTalk の本格動作に必要 (任意)
bash setup/02_download_models.sh
```

ダウンロードしない場合: アバター静止画 + 音声で動画を生成 (フォールバック)

---

## Qwen3-TTS MLX の有効化 (任意)

```bash
# HuggingFace トークン設定手順
bash setup/03_hf_token.sh

# 設定後にテスト
HF_TOKEN=your_token python workflow/generate_audio.py \
  'こんにちは' output/test.wav Chelsie
```

利用可能な Qwen3-TTS 音声: `Chelsie`, `Ethan`, `Vivian`, `River`, `Aaliyah`, `Cole`

---

## macOS 日本語音声一覧

| キー | 音声名 | 特徴 |
|---|---|---|
| `kyoko` | Kyoko | 女性・ニュートラル (デフォルト) |
| `eddy` | Eddy | 男性 |
| `flo` | Flo | 女性 |
| `reed` | Reed | 男性 |
| `rocko` | Rocko | 男性 |
| `sandy` | Sandy | 女性 |
| `shelley` | Shelley | 女性 |

---

## M1 16GB メモリ最適化設定

| 設定 | 値 | 理由 |
|---|---|---|
| `--batch-size` | 4 | 安全 (8まで可能) |
| `--whisper-model` | large-v3-turbo | 精度と速度のバランス |
| MuseTalk `use_float16` | False | M1での安定性 |
| `PYTORCH_ENABLE_MPS_FALLBACK` | 1 | MPS未対応オペ対策 |

---

## ディレクトリ構成

```
video-ai-studio/
├── pipeline.py           # メインパイプライン
├── activate.sh           # 環境有効化
├── workflow/
│   ├── transcribe.py     # MLX-Whisper
│   ├── generate_audio.py # Qwen3-TTS / macOS TTS
│   ├── create_avatar.py  # MuseTalk
│   └── compose_video.py  # FFmpeg + Hyperframes
├── MuseTalk/             # リップシンクエンジン (MPS対応済)
├── hyperframes/          # HTML動画レンダリング (ビルド済)
├── venv/                 # Python 3.12 仮想環境
├── models/               # AIモデル格納場所
├── output/
│   ├── transcripts/      # 文字起こし (.json/.txt/.srt)
│   ├── audio/            # 生成音声 (.wav)
│   └── video/            # 出力動画 (.mp4)
└── setup/
    ├── 01_create_env.sh
    ├── 02_download_models.sh  # MuseTalkモデル
    └── 03_hf_token.sh         # Qwen3-TTS設定
```
