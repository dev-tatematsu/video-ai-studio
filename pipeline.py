"""
セミナー切り抜き → アバター再演 パイプライン
M1 Mac (16GB) 最適化

ワークフロー:
  1. MLX-Whisper   → セミナー動画を文字起こし
  2. Qwen3-TTS MLX → アバター音声を生成
  3. MuseTalk MPS  → リップシンクアバター動画
  4. FFmpeg/Hyperframes → 最終動画合成

使用方法:
  python pipeline.py <セミナー動画.mp4> --avatar <アバター画像.jpg> [オプション]

例:
  python pipeline.py seminar.mp4 --avatar avatar.jpg
  python pipeline.py seminar.mp4 --avatar avatar.jpg --voice-clone speaker.wav --lang ja
"""

import argparse
import os
import sys
import time
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "workflow"))
sys.path.insert(0, str(PROJECT_ROOT / "MuseTalk"))


def run_pipeline(args):
    start_time = time.time()

    print("=" * 60)
    print("  セミナー切り抜き → アバター再演 パイプライン")
    print("  M1 Mac (MLX + MPS + VideoToolbox)")
    print("=" * 60)

    input_video = Path(args.input)
    stem = input_video.stem
    output_dir = Path(args.output_dir)

    # 出力ディレクトリ準備
    transcript_dir = output_dir / "transcripts"
    audio_dir = output_dir / "audio"
    video_dir = output_dir / "video"
    for d in [transcript_dir, audio_dir, video_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────
    # STEP 1: 文字起こし (MLX-Whisper)
    # ──────────────────────────────────────────
    print("\n" + "─" * 50)
    print("STEP 1/4: MLX-Whisper で文字起こし")
    print("─" * 50)

    from transcribe import transcribe
    transcript = transcribe(
        input_path=str(input_video),
        output_dir=str(transcript_dir),
        language=args.lang,
        model=args.whisper_model,
    )

    transcript_json = transcript_dir / f"{stem}_transcript.json"
    srt_path = transcript_dir / f"{stem}.srt"
    step1_time = time.time()
    print(f"  完了 ({step1_time - start_time:.1f}秒)")

    # ──────────────────────────────────────────
    # STEP 2: 音声生成 (Qwen3-TTS MLX)
    # ──────────────────────────────────────────
    print("\n" + "─" * 50)
    print("STEP 2/4: Qwen3-TTS で音声生成")
    print("─" * 50)

    from generate_audio import generate_from_transcript, generate_audio

    if args.text:
        # 指定テキストで音声生成
        audio_path = str(audio_dir / f"{stem}_audio.wav")
        generate_audio(
            text=args.text,
            output_path=audio_path,
            voice=args.voice,
            reference_audio=args.voice_clone,
        )
    else:
        # 文字起こし結果から生成
        segments = generate_from_transcript(
            transcript_path=str(transcript_json),
            output_dir=str(audio_dir),
            voice=args.voice,
            reference_audio=args.voice_clone,
            merge=True,
        )
        audio_path = str(audio_dir / "merged_audio.wav")

    step2_time = time.time()
    print(f"  完了 ({step2_time - step1_time:.1f}秒)")

    # ──────────────────────────────────────────
    # STEP 3: アバター動画生成 (MuseTalk MPS)
    # ──────────────────────────────────────────
    print("\n" + "─" * 50)
    print("STEP 3/4: MuseTalk でリップシンク生成")
    print("─" * 50)

    from create_avatar import create_lipsync_video
    avatar_video = str(video_dir / f"{stem}_avatar.mp4")

    create_lipsync_video(
        avatar_source=args.avatar,
        audio_path=audio_path,
        output_path=avatar_video,
        bbox_shift=args.bbox_shift,
        batch_size=args.batch_size,
    )

    step3_time = time.time()
    print(f"  完了 ({step3_time - step2_time:.1f}秒)")

    # ──────────────────────────────────────────
    # STEP 4: 最終動画合成 (FFmpeg + Hyperframes)
    # ──────────────────────────────────────────
    print("\n" + "─" * 50)
    print("STEP 4/4: 最終動画合成")
    print("─" * 50)

    from compose_video import (
        render_title_card, create_side_by_side,
        add_subtitles, concatenate_videos
    )

    parts = []

    # タイトルカード
    if args.title:
        title_video = str(video_dir / "title.mp4")
        render_title_card(
            title=args.title,
            subtitle=args.subtitle or "",
            output_path=title_video,
        )
        parts.append(title_video)

    # アバター動画に字幕追加
    if srt_path.exists() and args.subtitles:
        subtitled_video = str(video_dir / f"{stem}_subtitled.mp4")
        add_subtitles(avatar_video, str(srt_path), subtitled_video)
        parts.append(subtitled_video)
    else:
        parts.append(avatar_video)

    # 最終結合
    if len(parts) > 1:
        final_video = str(video_dir / f"{stem}_final.mp4")
        concatenate_videos(parts, final_video)
    else:
        final_video = parts[0]

    # オプション: オリジナルとの比較動画
    if args.compare:
        compare_video = str(video_dir / f"{stem}_compare.mp4")
        create_side_by_side(str(input_video), avatar_video, compare_video)
        print(f"\n比較動画: {compare_video}")

    step4_time = time.time()
    total_time = step4_time - start_time

    print("\n" + "=" * 60)
    print("✅ パイプライン完了!")
    print(f"   最終動画: {final_video}")
    print(f"   処理時間: {total_time:.1f}秒 ({total_time/60:.1f}分)")
    print("=" * 60)

    return final_video


def main():
    parser = argparse.ArgumentParser(
        description="セミナー切り抜き → アバター再演パイプライン (M1 Mac最適化)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", help="入力セミナー動画 (.mp4/.mov)")
    parser.add_argument("--avatar", required=True, help="アバター画像(.jpg)または動画(.mp4)")
    parser.add_argument("--output-dir", default="output", help="出力ディレクトリ (default: output)")
    parser.add_argument("--lang", default="ja", help="言語コード (default: ja)")
    parser.add_argument("--text", help="文字起こしの代わりに使うテキスト")
    parser.add_argument("--voice", default="Chelsie", help="TTS 音声名 (default: Chelsie)")
    parser.add_argument("--voice-clone", help="声クローン用参照音声 (.wav, 5秒以上推奨)")
    parser.add_argument("--whisper-model", default="mlx-community/whisper-large-v3-turbo",
                        help="Whisper モデル (default: large-v3-turbo)")
    parser.add_argument("--title", help="タイトルカードのテキスト")
    parser.add_argument("--subtitle", help="タイトルカードのサブタイトル")
    parser.add_argument("--subtitles", action="store_true", help="字幕を動画に焼き込む")
    parser.add_argument("--compare", action="store_true", help="オリジナルとの比較動画を生成")
    parser.add_argument("--bbox-shift", type=int, default=0, help="口元調整 (-10〜10, default: 0)")
    parser.add_argument("--batch-size", type=int, default=4,
                        help="処理バッチサイズ (M1 16GB: 4-8推奨, default: 4)")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"エラー: 入力ファイルが見つかりません: {args.input}")
        sys.exit(1)
    if not os.path.exists(args.avatar):
        print(f"エラー: アバターファイルが見つかりません: {args.avatar}")
        sys.exit(1)

    run_pipeline(args)


if __name__ == "__main__":
    main()
