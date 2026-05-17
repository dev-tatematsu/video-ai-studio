"""
Step 1: MLX-Whisper で動画/音声を文字起こし
M1 Mac の Neural Engine を活用した高速文字起こし
"""

import mlx_whisper
import json
import os
import subprocess
from pathlib import Path


def extract_audio(video_path: str, audio_path: str) -> str:
    """動画から音声を抽出 (VideoToolbox 最適化)"""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",                    # 映像なし
        "-acodec", "pcm_s16le",  # WAV 16bit
        "-ar", "16000",           # Whisper 推奨サンプルレート
        "-ac", "1",               # モノラル
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"音声抽出失敗: {result.stderr}")
    return audio_path


def transcribe(
    input_path: str,
    output_dir: str = "output/transcripts",
    model: str = "mlx-community/whisper-large-v3-turbo",
    language: str = "ja",
) -> dict:
    """
    動画または音声ファイルを文字起こし

    Args:
        input_path: 動画(.mp4/.mov)または音声(.wav/.mp3)ファイル
        output_dir: 出力ディレクトリ
        model: Whisper モデル (MLX 量子化版)
        language: 言語コード ("ja"=日本語, "en"=英語)

    Returns:
        文字起こし結果 (text, segments, language)
    """
    os.makedirs(output_dir, exist_ok=True)
    input_path = Path(input_path)

    # 動画の場合は音声を抽出
    audio_path = str(input_path)
    if input_path.suffix.lower() in [".mp4", ".mov", ".avi", ".mkv"]:
        audio_path = str(Path(output_dir) / f"{input_path.stem}_audio.wav")
        print(f"[1/2] 音声抽出中: {input_path.name} → {Path(audio_path).name}")
        extract_audio(str(input_path), audio_path)

    print(f"[2/2] 文字起こし中 (モデル: {model.split('/')[-1]})...")
    print("      M1 Neural Engine で処理中...")

    result = mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo=model,
        language=language,
        word_timestamps=True,     # 単語レベルのタイムスタンプ
        verbose=False,
    )

    # 結果を保存
    stem = input_path.stem

    # JSON (フル詳細)
    json_path = Path(output_dir) / f"{stem}_transcript.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # テキスト (読みやすい形式)
    txt_path = Path(output_dir) / f"{stem}_transcript.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        for seg in result["segments"]:
            start = seg["start"]
            end = seg["end"]
            text = seg["text"].strip()
            f.write(f"[{start:.1f}s - {end:.1f}s] {text}\n")

    # SRT 字幕
    srt_path = Path(output_dir) / f"{stem}.srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result["segments"], 1):
            start = _seconds_to_srt_time(seg["start"])
            end = _seconds_to_srt_time(seg["end"])
            text = seg["text"].strip()
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

    print(f"\n✅ 文字起こし完了")
    print(f"   JSON : {json_path}")
    print(f"   テキスト: {txt_path}")
    print(f"   SRT  : {srt_path}")
    print(f"\n--- 文字起こし結果 (先頭500文字) ---")
    print(result["text"][:500])

    return result


def _seconds_to_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("使用方法: python transcribe.py <動画ファイル> [言語コード]")
        print("例: python transcribe.py seminar.mp4 ja")
        sys.exit(1)

    lang = sys.argv[2] if len(sys.argv) > 2 else "ja"
    transcribe(sys.argv[1], language=lang)
