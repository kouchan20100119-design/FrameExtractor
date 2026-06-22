# Frame Extractor

ffmpeg を使って動画からフレーム画像を切り出すための Python ツールです。

## 使い方

### 1. ffmpeg をインストールする
PowerShell を開き、次を実行します。

```powershell
winget install ffmpeg
```

> すでに ffmpeg が入っている場合は、この手順は不要です。

### 2. 動画ファイルを用意する
切り出したい動画ファイルをこのフォルダに置きます。

### 3. スクリプトを実行する
次のように実行します。

```powershell
python extractor.py movie.mov ./output --fps 20
```

この例では、`movie.mov` を元にして、1 秒あたり 20 枚の画像を出力します。
出力先は `./output` です。

## 実行例

```powershell
python extractor.py input.mp4 ./output --fps 15 --start 5 --end 10
```

- `--fps` : 1 秒あたりの出力枚数
- `--start` : 開始秒
- `--end` : 終了秒
- `--quality`, `-q` : JPEG 品質（1〜31、デフォルト: 2）
- `--prefix` : 出力ファイル名の接頭辞
- `--width`, `-W` : リサイズ後の幅（px）
- `--height`, `-H` : リサイズ後の高さ（px）

## 実行オプション

```text
-h, --help            ヘルプを表示
--fps FPS             フレームレート（例: 20）
--start START         開始秒
--end END             終了秒
--quality, -q QUALITY JPEG品質 1(最高)～31(最低) [デフォルト: 2]
--prefix PREFIX       ファイル名プレフィックス
--width, -W WIDTH     リサイズ幅 (px)
--height, -H HEIGHT   リサイズ高さ (px)
```