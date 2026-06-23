import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import shutil
import sys
import threading
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

SUPPORTED_EXTENSIONS = {".mov", ".mp4", ".avi", ".mkv", ".m4v", ".mts", ".ts"}

# ── ffmpeg 自動インストール ──────────────────────────────────────────────────

def ensure_ffmpeg():
    if shutil.which("ffmpeg"):
        return True
    if not shutil.which("winget"):
        messagebox.showerror(
            "ffmpeg が見つかりません",
            "ffmpeg が見つからず、winget も利用できません。\n"
            "手動でインストールしてください: https://ffmpeg.org/download.html"
        )
        return False
    ok = messagebox.askyesno(
        "ffmpeg が見つかりません",
        "ffmpeg がインストールされていません。\nwinget で自動インストールしますか？"
    )
    if not ok:
        return False
    result = subprocess.run([
        "winget", "install", "--id", "Gyan.FFmpeg", "-e",
        "--accept-source-agreements", "--accept-package-agreements",
    ])
    if result.returncode != 0:
        messagebox.showerror("インストール失敗", "winget によるインストールに失敗しました。")
        return False
    if not shutil.which("ffmpeg"):
        messagebox.showwarning(
            "再起動が必要",
            "インストールされましたが、PATH に反映されていません。\n"
            "PowerShell を開き直してから再実行してください。"
        )
        return False
    return True

# ── フレーム抽出コア ─────────────────────────────────────────────────────────

def extract_frames(input_path, output_dir, fps=None, start_time=None,
                   end_time=None, quality=2, prefix="frame",
                   width=None, height=None):
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["ffmpeg", "-y"]
    if start_time:
        cmd += ["-ss", str(start_time)]
    cmd += ["-i", str(input_path)]
    if end_time:
        if start_time:
            cmd += ["-t", str(end_time - start_time)]
        else:
            cmd += ["-to", str(end_time)]

    filters = []
    if fps:
        filters.append(f"fps={fps}")
    if width or height:
        w = str(width) if width else "-1"
        h = str(height) if height else "-1"
        filters.append(f"scale={w}:{h}")
    if filters:
        cmd += ["-vf", ",".join(filters)]

    cmd += ["-q:v", str(quality), str(output_dir / f"{prefix}_%05d.jpg")]

    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return len(list(output_dir.glob(f"{prefix}_*.jpg")))

def process_one(args_tuple):
    input_path, output_dir, kwargs = args_tuple
    try:
        count = extract_frames(input_path, output_dir, **kwargs)
        return (input_path, output_dir, count, None)
    except Exception as e:
        return (input_path, output_dir, 0, str(e))

# ── GUI ─────────────────────────────────────────────────────────────────────

class FrameExtractorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Frame Extractor")
        self.resizable(False, False)
        self.configure(bg="#F5F5F3")

        self.files = []          # 入力ファイルリスト
        self.running = False

        self._build_ui()
        self._try_dnd()

    # ── ドラッグ&ドロップ（tkinterdnd2 があれば有効化） ──────────────────
    def _try_dnd(self):
        try:
            from tkinterdnd2 import DND_FILES
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind("<<Drop>>", self._on_drop)
            self.drop_label.config(text="ここにファイルをドロップ\nまたは「追加」ボタンで選択")
        except ImportError:
            self.drop_label.config(text="「追加」ボタンでファイルを選択\n（pip install tkinterdnd2 でDnD対応）")

    def _on_drop(self, event):
        # Windows の DnD は {} で囲まれたパスが来る場合がある
        raw = event.data.strip()
        paths = self.tk.splitlist(raw)
        for p in paths:
            self._add_file(p)

    # ── UI 構築 ──────────────────────────────────────────────────────────
    def _build_ui(self):
        PAD = 12
        BG = "#F5F5F3"
        CARD = "#FFFFFF"
        BORDER = "#DDDDD8"
        LABEL_FG = "#888780"
        FONT = ("Segoe UI", 10)
        FONT_SM = ("Segoe UI", 9)
        FONT_BOLD = ("Segoe UI", 10, "bold")

        def card(parent, **kw):
            f = tk.Frame(parent, bg=CARD, bd=0,
                         highlightbackground=BORDER, highlightthickness=1, **kw)
            return f

        def section(parent, text):
            tk.Label(parent, text=text, bg=CARD, fg=LABEL_FG,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(10, 2))

        def sep(parent):
            ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=12, pady=4)

        outer = tk.Frame(self, bg=BG, padx=PAD, pady=PAD)
        outer.pack(fill="both", expand=True)

        # ── タイトル ─────────────────────────────────────────────────────
        title_bar = tk.Frame(outer, bg=BG)
        title_bar.pack(fill="x", pady=(0, PAD))
        tk.Label(title_bar, text="Frame Extractor",
                 bg=BG, fg="#2C2C2A", font=("Segoe UI", 14, "bold")).pack(side="left")
        tk.Label(title_bar, text=".mov / .mp4 → JPEG",
                 bg=BG, fg=LABEL_FG, font=FONT_SM).pack(side="left", padx=(8, 0), pady=2)

        # ── 入力ファイル ─────────────────────────────────────────────────
        c1 = card(outer)
        c1.pack(fill="x", pady=(0, 8))
        section(c1, "入力ファイル")

        self.drop_frame = tk.Frame(c1, bg="#FAFAF8",
                                   highlightbackground=BORDER, highlightthickness=1)
        self.drop_frame.pack(fill="x", padx=12, pady=(0, 8))

        self.drop_label = tk.Label(self.drop_frame, text="",
                                   bg="#FAFAF8", fg=LABEL_FG, font=FONT_SM,
                                   pady=18)
        self.drop_label.pack()

        btn_row = tk.Frame(c1, bg=CARD)
        btn_row.pack(fill="x", padx=12, pady=(0, 8))
        tk.Button(btn_row, text="＋ ファイルを追加",
                  font=FONT_SM, bg=CARD, relief="solid", bd=1,
                  activebackground="#EFEFED",
                  command=self._browse_files).pack(side="left")
        tk.Button(btn_row, text="クリア",
                  font=FONT_SM, bg=CARD, relief="solid", bd=1,
                  activebackground="#EFEFED",
                  command=self._clear_files).pack(side="left", padx=(6, 0))

        # ファイルリスト表示
        list_frame = tk.Frame(c1, bg=CARD)
        list_frame.pack(fill="x", padx=12, pady=(0, 10))
        self.file_listbox = tk.Listbox(list_frame, font=FONT_SM, height=4,
                                       bg="#FAFAF8", bd=1, relief="solid",
                                       selectbackground="#E6E6E2",
                                       highlightthickness=0)
        self.file_listbox.pack(fill="x")

        # ── 設定 ─────────────────────────────────────────────────────────
        c2 = card(outer)
        c2.pack(fill="x", pady=(0, 8))
        section(c2, "設定")

        grid = tk.Frame(c2, bg=CARD)
        grid.pack(fill="x", padx=12, pady=(0, 4))
        grid.columnconfigure((0, 1, 2, 3), weight=1)

        def labeled_entry(parent, row, col, label, default, width=7):
            tk.Label(parent, text=label, bg=CARD, fg=LABEL_FG,
                     font=FONT_SM).grid(row=row*2, column=col, sticky="w", pady=(6, 1), padx=(0, 8))
            var = tk.StringVar(value=default)
            e = tk.Entry(parent, textvariable=var, width=width, font=FONT,
                         relief="solid", bd=1)
            e.grid(row=row*2+1, column=col, sticky="ew", pady=(0, 4), padx=(0, 8))
            return var

        self.var_interval = labeled_entry(grid, 0, 0, "インターバル (ms)", "50")
        self.var_quality  = labeled_entry(grid, 0, 1, "JPEG品質 (1〜31)", "2")
        self.var_start    = labeled_entry(grid, 0, 2, "開始 (秒, 省略可)", "")
        self.var_end      = labeled_entry(grid, 0, 3, "終了 (秒, 省略可)", "")

        sep(c2)

        resize_row = tk.Frame(c2, bg=CARD)
        resize_row.pack(fill="x", padx=12, pady=(0, 6))
        self.var_resize = tk.BooleanVar(value=False)
        tk.Checkbutton(resize_row, text="リサイズ",
                       variable=self.var_resize, bg=CARD, font=FONT,
                       command=self._toggle_resize).pack(side="left")
        self.var_width  = tk.StringVar(value="")
        self.var_height = tk.StringVar(value="")
        tk.Label(resize_row, text="幅", bg=CARD, fg=LABEL_FG, font=FONT_SM).pack(side="left", padx=(12, 4))
        self.entry_width = tk.Entry(resize_row, textvariable=self.var_width,
                                    width=6, font=FONT, relief="solid", bd=1, state="disabled")
        self.entry_width.pack(side="left")
        tk.Label(resize_row, text="高さ", bg=CARD, fg=LABEL_FG, font=FONT_SM).pack(side="left", padx=(8, 4))
        self.entry_height = tk.Entry(resize_row, textvariable=self.var_height,
                                     width=6, font=FONT, relief="solid", bd=1, state="disabled")
        self.entry_height.pack(side="left")
        tk.Label(resize_row, text="px（空白で自動）", bg=CARD, fg=LABEL_FG, font=FONT_SM).pack(side="left", padx=(4, 0))

        sep(c2)

        parallel_row = tk.Frame(c2, bg=CARD)
        parallel_row.pack(fill="x", padx=12, pady=(0, 10))
        tk.Label(parallel_row, text="並列数", bg=CARD, fg=LABEL_FG, font=FONT_SM).pack(side="left")
        self.var_workers = tk.IntVar(value=4)
        tk.Spinbox(parallel_row, from_=1, to=16, textvariable=self.var_workers,
                   width=4, font=FONT, relief="solid", bd=1).pack(side="left", padx=(6, 0))
        tk.Label(parallel_row, text="（ファイルが1本の場合は無効）",
                 bg=CARD, fg=LABEL_FG, font=FONT_SM).pack(side="left", padx=(8, 0))

        # ── 出力先 ───────────────────────────────────────────────────────
        c3 = card(outer)
        c3.pack(fill="x", pady=(0, 8))
        section(c3, "出力先フォルダ")

        out_row = tk.Frame(c3, bg=CARD)
        out_row.pack(fill="x", padx=12, pady=(0, 10))
        self.var_output = tk.StringVar(value=str(Path.home() / "Desktop" / "output"))
        tk.Entry(out_row, textvariable=self.var_output, font=("Segoe UI", 9),
                 relief="solid", bd=1).pack(side="left", fill="x", expand=True)
        tk.Button(out_row, text="参照...", font=FONT_SM, bg=CARD,
                  relief="solid", bd=1, activebackground="#EFEFED",
                  command=self._browse_output).pack(side="left", padx=(6, 0))

        # ── 進捗 ─────────────────────────────────────────────────────────
        c4 = card(outer)
        c4.pack(fill="x", pady=(0, 8))
        section(c4, "進捗")

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(c4, variable=self.progress_var,
                                             maximum=100, length=400)
        self.progress_bar.pack(fill="x", padx=12, pady=(0, 4))

        self.log_text = tk.Text(c4, height=5, font=("Consolas", 9),
                                bg="#FAFAF8", bd=1, relief="solid",
                                state="disabled", wrap="word")
        self.log_text.pack(fill="x", padx=12, pady=(0, 10))

        # ── 実行ボタン ────────────────────────────────────────────────────
        self.run_btn = tk.Button(outer, text="実行",
                                 font=("Segoe UI", 11, "bold"),
                                 bg="#2C2C2A", fg="white",
                                 activebackground="#444441", activeforeground="white",
                                 relief="flat", padx=20, pady=10,
                                 command=self._run)
        self.run_btn.pack(fill="x", pady=(0, 4))

    # ── ヘルパー ─────────────────────────────────────────────────────────
    def _toggle_resize(self):
        state = "normal" if self.var_resize.get() else "disabled"
        self.entry_width.config(state=state)
        self.entry_height.config(state=state)

    def _add_file(self, path):
        p = Path(path)
        if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
            self.log(f"スキップ: 非対応フォーマット → {p.name}")
            return
        if str(p) not in self.files:
            self.files.append(str(p))
            self.file_listbox.insert("end", p.name)

    def _browse_files(self):
        ext_str = " ".join(f"*{e}" for e in SUPPORTED_EXTENSIONS)
        paths = filedialog.askopenfilenames(
            title="動画ファイルを選択",
            filetypes=[("動画ファイル", ext_str), ("すべてのファイル", "*.*")]
        )
        for p in paths:
            self._add_file(p)

    def _clear_files(self):
        self.files.clear()
        self.file_listbox.delete(0, "end")

    def _browse_output(self):
        d = filedialog.askdirectory(title="出力先フォルダを選択")
        if d:
            self.var_output.set(d)

    def log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    # ── 実行 ─────────────────────────────────────────────────────────────
    def _run(self):
        if self.running:
            return
        if not self.files:
            messagebox.showwarning("ファイル未選択", "動画ファイルを追加してください。")
            return
        if not ensure_ffmpeg():
            return

        try:
            interval_ms = float(self.var_interval.get())
            fps = round(1000 / interval_ms, 4)
            quality = int(self.var_quality.get())
            assert 1 <= quality <= 31
        except Exception:
            messagebox.showerror("入力エラー", "インターバル・品質の値を確認してください。")
            return

        start = float(self.var_start.get()) if self.var_start.get().strip() else None
        end   = float(self.var_end.get())   if self.var_end.get().strip()   else None
        width  = int(self.var_width.get())  if self.var_resize.get() and self.var_width.get().strip()  else None
        height = int(self.var_height.get()) if self.var_resize.get() and self.var_height.get().strip() else None
        output_root = Path(self.var_output.get())
        workers = self.var_workers.get()

        kwargs = dict(fps=fps, start_time=start, end_time=end,
                      quality=quality, width=width, height=height)

        self.running = True
        self.run_btn.config(state="disabled", text="処理中...")
        self.progress_var.set(0)
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")
        self.log(f"{len(self.files)} 本の動画を処理します（{fps} fps）")

        threading.Thread(target=self._worker,
                         args=(self.files[:], output_root, workers, kwargs),
                         daemon=True).start()

    def _worker(self, files, output_root, workers, kwargs):
        total = len(files)
        done = 0

        if total == 1:
            inp = files[0]
            p = Path(inp)
            out_dir = output_root / p.stem
            try:
                count = extract_frames(inp, str(out_dir), **kwargs)
                self.after(0, self.log, f"[完了] {p.name} → {count} 枚")
            except Exception as e:
                self.after(0, self.log, f"[失敗] {p.name}: {e}")
            done = 1
            self.after(0, self.progress_var.set, 100)
        else:
            tasks = [(inp, str(output_root / Path(inp).stem), kwargs) for inp in files]
            with ProcessPoolExecutor(max_workers=workers) as ex:
                futures = {ex.submit(process_one, t): t for t in tasks}
                for future in as_completed(futures):
                    inp, out, count, err = future.result()
                    name = Path(inp).name
                    done += 1
                    pct = done / total * 100
                    if err:
                        self.after(0, self.log, f"[失敗] {name}: {err}")
                    else:
                        self.after(0, self.log, f"[完了] {name} → {count} 枚")
                    self.after(0, self.progress_var.set, pct)

        self.after(0, self._finish, done, total)

    def _finish(self, done, total):
        self.log(f"\n処理完了: {done} / {total} 本")
        self.running = False
        self.run_btn.config(state="normal", text="実行")
        messagebox.showinfo("完了", f"{done} 本の処理が完了しました。\n出力先: {self.var_output.get()}")


if __name__ == "__main__":
    app = FrameExtractorApp()
    app.mainloop()
