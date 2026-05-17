"""
Step 3: MuseTalk でリップシンクアバター動画を生成
M1 Mac MPS バックエンド対応
"""

import os
import sys
import subprocess
from pathlib import Path

MUSETALK_DIR = str(Path(__file__).parent.parent / "MuseTalk")


def create_lipsync_video(
    avatar_source: str,
    audio_path: str,
    output_path: str = "output/video/avatar_lipsync.mp4",
    bbox_shift: int = 0,
    batch_size: int = 4,          # 16GB RAM では 4-8 が安全
    use_float16: bool = False,    # M1 では float32 が安定
) -> str:
    """
    MuseTalk でリップシンク動画を生成

    Args:
        avatar_source: アバター画像(.jpg/.png)または動画(.mp4)
        audio_path: 生成した音声ファイル (.wav)
        output_path: 出力動画パス
        bbox_shift: 口元バウンディングボックスの調整 (-10〜10)
        batch_size: 処理バッチサイズ (メモリと速度のトレードオフ)
        use_float16: Float16 使用 (高速だが M1 では不安定な場合あり)

    Returns:
        生成された動画ファイルパス
    """
    os.makedirs(Path(output_path).parent, exist_ok=True)

    print("[Avatar] MuseTalk でリップシンク生成中...")
    print(f"  アバター: {avatar_source}")
    print(f"  音声    : {audio_path}")
    print(f"  バッチ  : {batch_size} (M1 16GB 最適化)")
    print("  デバイス: MPS (Apple Silicon)")

    return _run_musetalk_direct(
        avatar_source, audio_path, output_path, bbox_shift, batch_size, use_float16
    )


def _run_musetalk_direct(avatar_source, audio_path, output_path, bbox_shift, batch_size, use_float16):
    """MuseTalk scripts/inference.py をサブプロセスで実行"""
    import tempfile
    import yaml

    result_dir = str(Path(output_path).parent)
    os.makedirs(result_dir, exist_ok=True)

    # inference.py が期待する YAML config を一時ファイルとして生成
    task_cfg = {
        "task_0": {
            "video_path": os.path.abspath(avatar_source),
            "audio_path": os.path.abspath(audio_path),
            "result_name": Path(output_path).name,
        }
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, dir="/tmp"
    ) as f:
        yaml.dump(task_cfg, f)
        cfg_path = f.name

    # MuseTalk/scripts/inference.py を呼び出し
    inference_script = str(Path(MUSETALK_DIR) / "scripts" / "inference.py")
    cmd = [
        sys.executable, inference_script,
        "--vae_type",          "sd-vae",
        "--unet_config",       "./models/musetalkV15/musetalk.json",
        "--unet_model_path",   "./models/musetalkV15/unet.pth",
        "--whisper_dir",       "./models/whisper",
        "--inference_config",  cfg_path,
        "--result_dir",        os.path.abspath(result_dir),
        "--batch_size",        str(batch_size),
        "--version",           "v15",
    ]
    if use_float16:
        cmd.append("--use_float16")

    env = os.environ.copy()
    env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

    print(f"  [MuseTalk] 推論実行中 (batch={batch_size}) ...")
    result = subprocess.run(cmd, cwd=MUSETALK_DIR, env=env, text=True, stdin=subprocess.DEVNULL)

    os.unlink(cfg_path)

    if result.returncode != 0:
        print("⚠️  MuseTalk inference.py が失敗 → フォールバック")
        return _fallback_simple_composite(avatar_source, audio_path, output_path)

    # inference.py は result_dir/v15/<basename>_<audiobase>.mp4 に出力する
    # output_path へ移動
    avatar_base = Path(avatar_source).stem
    audio_base  = Path(audio_path).stem
    inferred = Path(result_dir) / "v15" / f"{avatar_base}_{audio_base}.mp4"

    # result_name を指定した場合
    named = Path(result_dir) / "v15" / Path(output_path).name
    if named.exists():
        if str(named) != output_path:
            named.rename(output_path)
    elif inferred.exists():
        if str(inferred) != output_path:
            inferred.rename(output_path)
    else:
        print(f"⚠️  出力ファイルが見つかりません: {inferred}")
        return _fallback_simple_composite(avatar_source, audio_path, output_path)

    print(f"✅ リップシンク動画: {output_path}")
    return output_path


def _fallback_simple_composite(avatar_source, audio_path, output_path):
    """
    MuseTalk モデル未ダウンロード時のフォールバック:
    アバター画像に音声を合成した静止画動画を生成
    """
    print("⚠️  フォールバック: アバター静止画 + 音声で動画生成")

    # 音声の長さを取得
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True
    )
    duration = float(result.stdout.strip()) if result.returncode == 0 else 10.0

    source = Path(avatar_source)
    os.makedirs(Path(output_path).parent, exist_ok=True)

    if source.suffix.lower() in [".jpg", ".jpeg", ".png"]:
        # 静止画 → 動画
        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", avatar_source,
            "-i", audio_path,
            "-c:v", "h264_videotoolbox",  # Apple Silicon GPU エンコード
            "-c:a", "aac",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-shortest",
            output_path
        ], check=True, capture_output=True)
    else:
        # 動画 + 音声
        subprocess.run([
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", avatar_source,
            "-i", audio_path,
            "-c:v", "h264_videotoolbox",
            "-c:a", "aac",
            "-t", str(duration),
            "-shortest",
            output_path
        ], check=True, capture_output=True)

    print(f"  フォールバック動画: {output_path}")
    print("  MuseTalk モデルをダウンロード後に再実行で本格的なリップシンクが利用可能")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("使用方法: python create_avatar.py <アバター画像/動画> <音声.wav> [出力.mp4]")
        print("例: python create_avatar.py avatar.jpg output/audio/merged.wav")
        sys.exit(1)

    avatar = sys.argv[1]
    audio = sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else "output/video/avatar_lipsync.mp4"
    create_lipsync_video(avatar, audio, out)
