ffmpegを使用してフレームの切り出しを簡単に行うPythonツールです。

[使い方]
①Powershellを起動しそこに「winget install ffmpeg」と入力し実行する。
②フレームを切り出したい動画をこのディレクトリ内に配置し、Powershellでextractor.pyを実行する。

例：　python extractor.py movie.mov ./output --fps 20

この場合はmovie.movという動画ファイルを1秒の動画あたり20枚の画像を切り出されることになる。
また切り出した画像は同じディレクトリ内の/outputに出力される。

[実行オプション]
-h, --help            show this help message and exit
--fps FPS             フレームレート (例: 20 = 50ms間隔)
--start START         開始秒
--end END             終了秒
--quality, -q QUALITY JPEG品質 1(最高)～31(最低) [デフォルト: 2]
--prefix PREFIX       ファイル名プレフィックス
--width, -W WIDTH     リサイズ幅 (px)
--height, -H HEIGHT   リサイズ高さ (px)