import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SUPPORTED_EXTENSIONS = {".mov", ".mp4", ".avi", ".mkv", ".m4v", ".mts", ".ts"}


def ensure_ffmpeg():
    """ffmpegがPATHに無ければwingetで自動インストールする"""
    if shutil.which("ffmpeg") is not None:
        return

    print("ffmpeg が見つかりません。winget でインストールを試みます...")

    if shutil.which("winget") is None:
        print("エラー: winget が見つかりません。")
        print("手動でインストールしてください: https://ffmpeg.org/download.html")
        sys.exit(1)

    install_cmd = [
        "winget", "install",
        "--id", "Gyan.FFmpeg",
        "-e",
        "--accept-source-agreements",
        "--accept-package-agreements",
    ]

    result = subprocess.run(install_cmd)

    if result.returncode != 0:
        print("エラー: winget によるインストールに失敗しました。")
        print("手動でインストールしてください: winget install ffmpeg")
        sys.exit(1)

    print("\nインストール完了。")
    print("注意: 新しいPowerShellウィンドウで再実行する必要がある場合があります")
    print("（PATHの反映に再起動が必要なため）。\n")

    if shutil.which("ffmpeg") is None:
        print("インストールされましたが、現在のセッションではまだ認識されません。")
        print("PowerShellを開き直してから再実行してください。")
        sys.exit(1)


def extract_frames(
    input_path: str,
    output_dir: str,
    fps: float = None,
    start_time: float = None,
    end_time: float = None,
    quality: int = 2,
    prefix: str = "frame",
    width: int = None,
    height: int = None,
):
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        print(f"エラー: ファイルが見つかりません: {input_path}")
        sys.exit(1)

    ext = input_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        print(f"エラー: 非対応のフォーマットです: {ext}")
        print(f"対応フォーマット: {supported}")
        sys.exit(1)

    cmd = ["ffmpeg", "-y"]

    if start_time is not None:
        cmd += ["-ss", str(start_time)]

    cmd += ["-i", str(input_path)]

    if end_time is not None:
        if start_time:
            cmd += ["-t", str(end_time - start_time)]
        else:
            cmd += ["-to", str(end_time)]

    filters = []
    if fps is not None:
        filters.append(f"fps={fps}")
    if width or height:
        w = str(width) if width else "-1"
        h = str(height) if height else "-1"
        filters.append(f"scale={w}:{h}")

    if filters:
        cmd += ["-vf", ",".join(filters)]

    cmd += [
        "-q:v", str(quality),
        str(output_dir / f"{prefix}_%05d.jpg"),
    ]

    print(f"入力: {input_path.name} ({ext})")
    print(f"出力: {output_dir}")
    print(f"実行: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        print("ffmpeg エラー:")
        print(result.stderr)
        sys.exit(1)

    frames = list(output_dir.glob(f"{prefix}_*.jpg"))
    print(f"\n完了: {len(frames)} 枚を保存しました")
    return frames


def main():
    exts = " / ".join(sorted(SUPPORTED_EXTENSIONS))
    p = argparse.ArgumentParser(
        description=f"動画から JPEG フレームを切り出す ({exts})"
    )
    p.add_argument("input",           help="入力動画ファイル")
    p.add_argument("output_dir",      help="出力ディレクトリ")
    p.add_argument("--fps",           type=float, help="フレームレート (例: 20 = 50ms間隔)")
    p.add_argument("--start",         type=float, help="開始秒")
    p.add_argument("--end",           type=float, help="終了秒")
    p.add_argument("--quality", "-q", type=int, default=2,
                   help="JPEG品質 1(最高)～31(最低) [デフォルト: 2]")
    p.add_argument("--prefix",        default="frame", help="ファイル名プレフィックス")
    p.add_argument("--width",  "-W",  type=int, help="リサイズ幅 (px)")
    p.add_argument("--height", "-H",  type=int, help="リサイズ高さ (px)")
    args = p.parse_args()

    ensure_ffmpeg()

    extract_frames(
        input_path=args.input,
        output_dir=args.output_dir,
        fps=args.fps,
        start_time=args.start,
        end_time=args.end,
        quality=args.quality,
        prefix=args.prefix,
        width=args.width,
        height=args.height,
    )

if __name__ == "__main__":
    main()