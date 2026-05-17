"""
Step 2: 音声生成
優先順位:
  1. Qwen3-TTS MLX (HF_TOKEN 設定時)
  2. macOS say コマンド (常に利用可能、日本語9音声対応)
"""

import os
import json
import subprocess
from pathlib import Path

# 利用可能な日本語音声
MACOS_JA_VOICES = {
    "kyoko": "Kyoko",       # 女性 (ニュートラル)
    "eddy": "Eddy",         # 男性
    "flo": "Flo",           # 女性
    "reed": "Reed",         # 男性
    "rocko": "Rocko",       # 男性
    "sandy": "Sandy",       # 女性
    "shelley": "Shelley",   # 女性
    "grandma": "Grandma",
    "grandpa": "Grandpa",
}

# Qwen3-TTS MLX モデル (HF_TOKEN 必要)
QWEN3_TTS_MODELS = {
    "4bit": "mlx-community/Qwen3-TTS-MLX-4bit",
    "8bit": "mlx-community/Qwen3-TTS-MLX-8bit",
    "fp16": "mlx-community/Qwen3-TTS-MLX",
}

QWEN3_VOICES = ["Chelsie", "Ethan", "Vivian", "River", "Aaliyah", "Cole"]


def generate_audio(
    text: str,
    output_path: str,
    voice: str = "kyoko",
    reference_audio: str = None,
    speed: float = 1.0,
    backend: str = "auto",         # "auto", "qwen3", "macos"
    model_quant: str = "4bit",
) -> str:
    """
    テキストから音声を生成

    Args:
        text: 読み上げるテキスト
        output_path: 出力 WAV ファイルパス
        voice: 音声名 (macOS: "kyoko"/"eddy"/等, Qwen3: "Chelsie"/"Ethan"/等)
        reference_audio: 声クローン参照音声 (Qwen3-TTS のみ)
        speed: 読み上げ速度 (0.5-2.0)
        backend: "auto"=自動選択, "qwen3"=MLX強制, "macos"=macOS強制
        model_quant: "4bit", "8bit", "fp16"

    Returns:
        生成された音声ファイルパス
    """
    os.makedirs(Path(output_path).parent, exist_ok=True)

    if backend == "auto":
        backend = "qwen3" if os.environ.get("HF_TOKEN") else "macos"

    if backend == "qwen3":
        try:
            return _generate_qwen3(text, output_path, voice, reference_audio, speed, model_quant)
        except Exception as e:
            print(f"⚠️  Qwen3-TTS 失敗: {e}")
            print("   macOS TTS にフォールバック...")
            backend = "macos"

    return _generate_macos(text, output_path, voice, speed)


def _generate_qwen3(text, output_path, voice, reference_audio, speed, model_quant):
    """Qwen3-TTS via mlx-audio (HF_TOKEN 必要)"""
    from mlx_audio.tts.generate import generate_audio as mlx_gen
    import soundfile as sf
    import numpy as np

    model = QWEN3_TTS_MODELS.get(model_quant, QWEN3_TTS_MODELS["4bit"])

    # Qwen3 の音声名に変換 (macOS voice が渡された場合)
    qwen_voice = voice if voice in QWEN3_VOICES else "Chelsie"

    print(f"[Qwen3-TTS] モデル: {model.split('/')[-1]}")
    print(f"            音声: {qwen_voice}, 速度: {speed}x")

    kwargs = {
        "model": model,
        "text": text,
        "speed": speed,
        "verbose": False,
    }
    if reference_audio and os.path.exists(reference_audio):
        kwargs["ref_audio"] = reference_audio
        print(f"            声クローン: {Path(reference_audio).name}")
    else:
        kwargs["voice"] = qwen_voice

    audio, sr = mlx_gen(**kwargs)

    if audio is None:
        raise RuntimeError("Qwen3-TTS が None を返しました")
    if isinstance(audio, list):
        audio = np.concatenate(audio)

    sf.write(output_path, audio, sr)
    print(f"✅ Qwen3-TTS 完了: {output_path}")
    return output_path


def _generate_macos(text, output_path, voice, speed):
    """macOS say コマンドで音声生成"""
    # 音声名を正規化
    voice_name = MACOS_JA_VOICES.get(voice.lower(), "Kyoko")

    # 速度を say コマンドのレートに変換 (デフォルト: 175 words/min)
    rate = int(175 * speed)

    print(f"[macOS TTS] 音声: {voice_name}, 速度: {rate}wpm")
    print(f"            テキスト: {text[:60]}{'...' if len(text) > 60 else ''}")

    tmp_aiff = output_path.replace(".wav", "_tmp.aiff")

    subprocess.run([
        "say",
        "-v", voice_name,
        "-r", str(rate),
        "-o", tmp_aiff,
        text
    ], check=True)

    # AIFF → WAV (FFmpeg)
    subprocess.run([
        "ffmpeg", "-y",
        "-i", tmp_aiff,
        "-ar", "24000",
        "-ac", "1",
        "-sample_fmt", "s16",
        output_path
    ], check=True, capture_output=True)

    os.remove(tmp_aiff)
    print(f"✅ macOS TTS 完了: {output_path}")
    return output_path


def generate_from_transcript(
    transcript_path: str,
    output_dir: str = "output/audio",
    voice: str = "kyoko",
    reference_audio: str = None,
    speed: float = 1.0,
    backend: str = "auto",
    merge: bool = True,
) -> list:
    """
    文字起こし JSON からセグメントごとに音声を生成

    Returns:
        {"path": ..., "start": ..., "end": ..., "text": ...} のリスト
    """
    os.makedirs(output_dir, exist_ok=True)

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    segments = transcript.get("segments", [])
    generated = []

    print(f"[TTS] {len(segments)} セグメントを処理 (backend: {backend})...")

    for i, seg in enumerate(segments):
        text = seg["text"].strip()
        if not text:
            continue

        seg_path = str(Path(output_dir) / f"seg_{i:04d}.wav")
        print(f"\n[{i+1}/{len(segments)}] {seg['start']:.1f}s: {text[:50]}")

        generate_audio(
            text=text,
            output_path=seg_path,
            voice=voice,
            reference_audio=reference_audio,
            speed=speed,
            backend=backend,
        )
        generated.append({
            "path": seg_path,
            "start": seg["start"],
            "end": seg["end"],
            "text": text,
        })

    if merge and generated:
        merged_path = str(Path(output_dir) / "merged_audio.wav")
        _merge_segments(generated, merged_path)
        print(f"\n✅ 結合音声: {merged_path}")

    return generated


def _merge_segments(segments: list, output_path: str):
    """セグメント音声を結合 (タイムスタンプに基づく配置)"""
    import soundfile as sf
    import numpy as np

    sample_rate = 24000
    max_end = max(s["end"] for s in segments)
    total_samples = int(max_end * sample_rate) + sample_rate
    merged = np.zeros(total_samples, dtype=np.float32)

    for seg in segments:
        if not os.path.exists(seg["path"]):
            continue
        audio, sr = sf.read(seg["path"], dtype="float32")
        if sr != sample_rate:
            from scipy.signal import resample
            audio = resample(audio, int(len(audio) * sample_rate / sr))
        start = int(seg["start"] * sample_rate)
        end = start + len(audio)
        if end > len(merged):
            merged = np.pad(merged, (0, end - len(merged)))
        merged[start:end] += audio

    sf.write(output_path, np.clip(merged, -1.0, 1.0), sample_rate)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python generate_audio.py '読み上げるテキスト' [出力.wav] [音声名]")
        print("  python generate_audio.py transcript [JSON] [出力ディレクトリ]")
        print(f"\n利用可能な macOS 日本語音声: {', '.join(MACOS_JA_VOICES.keys())}")
        print(f"利用可能な Qwen3-TTS 音声: {', '.join(QWEN3_VOICES)}")
        sys.exit(1)

    if sys.argv[1] == "transcript":
        generate_from_transcript(
            transcript_path=sys.argv[2] if len(sys.argv) > 2 else "output/transcripts/transcript.json",
            output_dir=sys.argv[3] if len(sys.argv) > 3 else "output/audio",
        )
    else:
        out = sys.argv[2] if len(sys.argv) > 2 else "output/audio/output.wav"
        voice = sys.argv[3] if len(sys.argv) > 3 else "kyoko"
        generate_audio(sys.argv[1], out, voice=voice)
