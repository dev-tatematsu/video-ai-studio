"""
Step 4: FFmpeg + Hyperframes で最終動画を合成
Apple Silicon VideoToolbox 最適化エンコード
"""

import os
import subprocess
import json
from pathlib import Path


HYPERFRAMES_CLI = str(Path(__file__).parent.parent / "hyperframes" / "packages" / "cli" / "dist" / "cli.js")
VENV_NODE = "node"


def add_subtitles(
    video_path: str,
    srt_path: str,
    output_path: str,
    font_size: int = 24,
    font_color: str = "white",
    bg_alpha: float = 0.6,
) -> str:
    """字幕を動画に焼き込む"""
    os.makedirs(Path(output_path).parent, exist_ok=True)

    # ASS 字幕形式に変換 (スタイリング対応)
    ass_path = srt_path.replace(".srt", ".ass")
    subprocess.run([
        "ffmpeg", "-y", "-i", srt_path, ass_path
    ], check=True, capture_output=True)

    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"ass={ass_path}",
        "-c:v", "h264_videotoolbox",  # Apple Silicon GPU エンコード
        "-c:a", "copy",
        "-b:v", "4M",
        output_path
    ], check=True)

    print(f"✅ 字幕付き動画: {output_path}")
    return output_path


def create_side_by_side(
    original_video: str,
    avatar_video: str,
    output_path: str,
    layout: str = "side",    # "side" or "pip" (picture-in-picture)
    pip_position: str = "br",  # br=右下, bl=左下, tr=右上, tl=左上
) -> str:
    """
    オリジナル動画とアバター動画を並べる/重ねる

    Args:
        layout: "side"=横並び, "pip"=ピクチャインピクチャ
    """
    os.makedirs(Path(output_path).parent, exist_ok=True)

    if layout == "side":
        # 横並び (等幅にリサイズ)
        filter_complex = (
            "[0:v]scale=960:540,setsar=1[left];"
            "[1:v]scale=960:540,setsar=1[right];"
            "[left][right]hstack=inputs=2[out]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", original_video,
            "-i", avatar_video,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-map", "1:a",
            "-c:v", "h264_videotoolbox",
            "-c:a", "aac",
            "-b:v", "6M",
            output_path
        ]
    else:
        # PIP (アバターをオリジナルの上に重ねる)
        positions = {
            "br": "W-w-20:H-h-20",
            "bl": "20:H-h-20",
            "tr": "W-w-20:20",
            "tl": "20:20",
        }
        pos = positions.get(pip_position, positions["br"])
        filter_complex = (
            "[1:v]scale=320:180[pip];"
            f"[0:v][pip]overlay={pos}[out]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", original_video,
            "-i", avatar_video,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-map", "1:a",
            "-c:v", "h264_videotoolbox",
            "-c:a", "aac",
            "-b:v", "4M",
            output_path
        ]

    subprocess.run(cmd, check=True)
    print(f"✅ 合成動画: {output_path}")
    return output_path


def create_title_card_html(
    title: str,
    subtitle: str = "",
    duration_sec: float = 3.0,
    output_dir: str = "tmp",
    theme: str = "dark",
) -> str:
    """
    Hyperframes 用 HTML タイトルカードを生成

    Returns:
        HTML ファイルパス
    """
    os.makedirs(output_dir, exist_ok=True)

    bg_color = "#0f0f0f" if theme == "dark" else "#ffffff"
    text_color = "#ffffff" if theme == "dark" else "#0f0f0f"
    accent_color = "#4f9cf9"

    runtime_js_path = (Path(__file__).parent.parent /
                       "hyperframes/packages/cli/dist/hyperframe.runtime.iife.js")
    runtime_js_inline = ""
    if runtime_js_path.exists():
        runtime_js_inline = runtime_js_path.read_text(encoding="utf-8")

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <script>{runtime_js_inline}</script>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      width: 1920px; height: 1080px;
      background: {bg_color};
      display: flex; flex-direction: column;
      justify-content: center; align-items: center;
      font-family: 'Helvetica Neue', sans-serif;
    }}
    .title {{
      font-size: 72px; font-weight: 700;
      color: {text_color};
      text-align: center;
      animation: fadeIn 0.8s ease-out;
      line-height: 1.2;
    }}
    .subtitle {{
      font-size: 36px; font-weight: 300;
      color: {accent_color};
      margin-top: 24px;
      animation: fadeIn 1.2s ease-out;
    }}
    .line {{
      width: 120px; height: 4px;
      background: {accent_color};
      margin: 32px auto;
      animation: expand 0.6s ease-out 0.3s both;
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(20px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes expand {{
      from {{ width: 0; }}
      to {{ width: 120px; }}
    }}
  </style>
</head>
<body data-duration="{duration_sec}">
  <div class="title">{title}</div>
  <div class="line"></div>
  {f'<div class="subtitle">{subtitle}</div>' if subtitle else ''}
</body>
</html>"""

    # Hyperframes は DIR/index.html 形式のプロジェクトを期待する
    project_dir = Path(output_dir) / "title_card_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    html_path = str(project_dir / "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    return html_path


def render_title_card(
    title: str,
    subtitle: str = "",
    output_path: str = "output/video/title.mp4",
    duration: float = 3.0,
) -> str:
    """Hyperframes で HTML タイトルカードを MP4 にレンダリング"""
    os.makedirs(Path(output_path).parent, exist_ok=True)

    html_path = create_title_card_html(title, subtitle, duration)
    project_dir = str(Path(html_path).parent)  # DIR を渡す

    print(f"[Hyperframes] タイトルカード生成中: {title}")

    result = subprocess.run(
        ["node", HYPERFRAMES_CLI, "render", project_dir,
         "--output", os.path.abspath(output_path),
         "--fps", "30", "--quiet"],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        # WARN レベルのメッセージは無視してフォールバックへ
        if result.stderr and "[WARN]" in result.stderr:
            print("  [Hyperframes] screenshot モードで生成中...")
        else:
            print(f"  [Hyperframes] フォールバック ({result.stderr[:100].strip()})")
        return _render_title_ffmpeg(title, subtitle, output_path, duration)

    print(f"✅ タイトルカード: {output_path}")
    return output_path


def _render_title_ffmpeg(title, subtitle, output_path, duration):
    """Pillow で画像生成 → FFmpeg で動画化 (日本語テキスト対応)"""
    from PIL import Image, ImageDraw, ImageFont
    import tempfile

    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), color=(15, 15, 15))
    draw = ImageDraw.Draw(img)

    # システムフォント (日本語対応)
    font_candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/Arial Unicode MS.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    font_title = ImageFont.load_default(size=72)
    font_sub = ImageFont.load_default(size=36)
    for fp in font_candidates:
        if os.path.exists(fp):
            try:
                font_title = ImageFont.truetype(fp, 72)
                font_sub = ImageFont.truetype(fp, 36)
                break
            except Exception:
                continue

    # タイトルを中央に描画
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    ty = H // 2 - th // 2 - (30 if subtitle else 0)
    draw.text(((W - tw) // 2, ty), title, fill=(255, 255, 255), font=font_title)

    # アクセントライン
    lx = (W - 120) // 2
    draw.rectangle([lx, ty + th + 20, lx + 120, ty + th + 24], fill=(79, 156, 249))

    # サブタイトル
    if subtitle:
        sbbox = draw.textbbox((0, 0), subtitle, font=font_sub)
        sw = sbbox[2] - sbbox[0]
        draw.text(((W - sw) // 2, ty + th + 40), subtitle, fill=(79, 156, 249), font=font_sub)

    # 一時 PNG → FFmpeg で動画化
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_png = tmp.name
    img.save(tmp_png)

    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1",       "-i", tmp_png,
        "-f", "lavfi",      "-i", "anullsrc=r=48000:cl=stereo",  # 無音トラック
        "-c:v", "h264_videotoolbox",
        "-c:a", "aac",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-vf", f"fade=in:0:15,fade=out:st={max(0, duration-0.5):.2f}:d=0.5",
        "-shortest",
        output_path
    ], check=True, capture_output=True)

    os.remove(tmp_png)
    return output_path


def _has_audio(video_path: str) -> bool:
    """動画に音声ストリームがあるか確認"""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True
    )
    return "audio" in result.stdout


def concatenate_videos(video_paths: list, output_path: str) -> str:
    """複数の動画を結合 (フォーマット正規化 → concat デマクサー)"""
    os.makedirs(Path(output_path).parent, exist_ok=True)
    os.makedirs("tmp", exist_ok=True)

    # Step 1: 全動画を共通フォーマットに正規化 (libx264 + aac 44100Hz stereo 30fps)
    normalized = []
    for i, p in enumerate(video_paths):
        norm = str(Path("tmp") / f"norm_{i}.mp4")
        cmd = ["ffmpeg", "-y", "-i", os.path.abspath(p)]
        if not _has_audio(p):
            cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        cmd += [
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac", "-ar", "44100", "-ac", "2",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-shortest", norm,
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        normalized.append(norm)

    # Step 2: concat デマクサーで結合 → VideoToolbox で再エンコード
    concat_file = str(Path("tmp") / "concat_list.txt")
    with open(concat_file, "w") as f:
        for p in normalized:
            f.write(f"file '{os.path.abspath(p)}'\n")

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-c:v", "h264_videotoolbox",
        "-c:a", "aac", "-ar", "44100", "-ac", "2",
        output_path,
    ], check=True, capture_output=True)

    print(f"✅ 結合動画: {output_path}")
    return output_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("使用方法:")
        print("  タイトルカード: python compose_video.py title 'タイトル' output.mp4")
        print("  横並び合成: python compose_video.py side original.mp4 avatar.mp4 output.mp4")
        print("  PIP合成: python compose_video.py pip original.mp4 avatar.mp4 output.mp4")
        sys.exit(1)

    mode = sys.argv[1]
    if mode == "title":
        render_title_card(sys.argv[2], output_path=sys.argv[3] if len(sys.argv) > 3 else "output/video/title.mp4")
    elif mode == "side":
        create_side_by_side(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "output/video/side_by_side.mp4")
    elif mode == "pip":
        create_side_by_side(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "output/video/pip.mp4", layout="pip")
