#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Format Converter  v1.0
────────────────────────────────────────────────────────────────
対応変換:
  jpg / png / webp 相互変換
  PDF → PNG / WebP（各ページを画像化）
  JPG / PNG → PDF（複数画像を 1 つの PDF に結合）
  TXT → PDF（MS ゴシック / 日本語対応）
────────────────────────────────────────────────────────────────
依存ライブラリ:
  customtkinter, Pillow, PyMuPDF, reportlab, tkinterdnd2
"""
from __future__ import annotations

import os
import threading
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable
import tkinter as tk

import customtkinter as ctk
from PIL import Image
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont

# ── オプション: ドラッグ＆ドロップ ──────────────────────────────────
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False


# ══════════════════════════════════════════════════════════════════
# 定数
# ══════════════════════════════════════════════════════════════════

_A4_W, _A4_H = 595.0, 842.0  # A4 in points (72 dpi 基準)
_PDF_DPI = 150                 # PDF → 画像 変換解像度

CONVERSION_MODES: list[tuple[str, str, str]] = [
    # (表示ラベル,                          カテゴリ,   出力拡張子)
    ("🖼  画像変換 → JPG",                    "image",    ".jpg"),
    ("🖼  画像変換 → PNG",                    "image",    ".png"),
    ("🖼  画像変換 → WebP",                   "image",    ".webp"),
    ("📄 PDF → PNG（各ページを画像化）",      "pdf2img",  ".png"),
    ("📄 PDF → WebP（各ページを画像化）",     "pdf2img",  ".webp"),
    ("🗂  画像群 → PDF（複数画像を結合）",    "imgs2pdf", ""),
    ("📝 TXT → PDF（日本語対応）",            "txt2pdf",  ""),
]

_FILE_FILTERS: dict[str, list[tuple[str, str]]] = {
    "image":    [("画像ファイル", "*.jpg *.jpeg *.png *.webp"), ("すべて", "*.*")],
    "pdf2img":  [("PDF ファイル", "*.pdf"),                     ("すべて", "*.*")],
    "imgs2pdf": [("画像ファイル", "*.jpg *.jpeg *.png"),         ("すべて", "*.*")],
    "txt2pdf":  [("テキストファイル", "*.txt"),                  ("すべて", "*.*")],
}


# ══════════════════════════════════════════════════════════════════
# 変換処理
# ══════════════════════════════════════════════════════════════════

def convert_image(
    files: list[str],
    out_dir: Path,
    target_ext: str,
    progress: Callable[[float], None],
) -> list[Path]:
    """jpg / png / webp 相互変換"""
    results: list[Path] = []
    n = len(files)

    for i, src_str in enumerate(files):
        src = Path(src_str)
        img = Image.open(src)

        if target_ext in (".jpg", ".jpeg"):
            # JPEG は透過非対応 → RGB に変換
            img = img.convert("RGB")
            dst = out_dir / (src.stem + target_ext)
            img.save(dst, quality=92)

        elif target_ext == ".png":
            if img.mode not in ("RGB", "RGBA", "L", "LA", "P"):
                img = img.convert("RGBA")
            dst = out_dir / (src.stem + ".png")
            img.save(dst)

        else:  # .webp
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            dst = out_dir / (src.stem + ".webp")
            img.save(dst, quality=90, method=6)

        results.append(dst)
        progress((i + 1) / n)

    return results


def pdf_to_images(
    files: list[str],
    out_dir: Path,
    target_ext: str,
    progress: Callable[[float], None],
    dpi: int = _PDF_DPI,
) -> list[Path]:
    """PDF 各ページを画像ファイルとして書き出す"""
    results: list[Path] = []

    # 先に全ドキュメントを開いて総ページ数を取得
    docs: list[tuple[Path, fitz.Document]] = [
        (Path(f), fitz.open(str(f))) for f in files
    ]
    total = sum(doc.page_count for _, doc in docs)
    done = 0

    mat = fitz.Matrix(dpi / 72, dpi / 72)

    for src, doc in docs:
        for page_num in range(doc.page_count):
            pix = doc[page_num].get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

            dst = out_dir / f"{src.stem}_p{page_num + 1:03d}{target_ext}"
            save_kw: dict = {"quality": 90} if target_ext == ".webp" else {}
            img.save(dst, **save_kw)

            results.append(dst)
            done += 1
            progress(done / total)

        doc.close()

    return results


def images_to_pdf(
    files: list[str],
    out_dir: Path,
    output_name: str,
    progress: Callable[[float], None],
) -> list[Path]:
    """複数の画像を 1 つの PDF に結合（A4 に等比スケーリング・中央配置）"""
    dst = out_dir / (output_name + ".pdf")
    doc = fitz.open()
    n = len(files)

    for i, f_str in enumerate(files):
        f = Path(f_str)
        with Image.open(str(f)) as img:
            w_px, h_px = img.size

        # A4 に収まるよう等比スケーリング
        scale = min(_A4_W / w_px, _A4_H / h_px)
        w_pt = w_px * scale
        h_pt = h_px * scale

        page = doc.new_page(width=_A4_W, height=_A4_H)
        x0 = (_A4_W - w_pt) / 2
        y0 = (_A4_H - h_pt) / 2
        page.insert_image(
            fitz.Rect(x0, y0, x0 + w_pt, y0 + h_pt),
            filename=str(f),
        )
        progress((i + 1) / n)

    doc.save(str(dst))
    doc.close()
    return [dst]


def txt_to_pdf(
    files: list[str],
    out_dir: Path,
    progress: Callable[[float], None],
) -> list[Path]:
    """テキストファイルを PDF に変換（MS ゴシック優先・日本語対応）"""
    # ── フォント登録（優先順位順に試行）────────────────────────────
    # 1. MS ゴシック（Windows 標準 TTC）
    # 2. その他 Windows 日本語 TTC フォント
    # 3. CID フォント fallback（Mac / Linux 向け）
    # 4. Helvetica（ASCII のみ・最終手段）
    font_name = "Helvetica"

    candidates_ttc = [
        # (登録名,       TTCファイルパス,                         subfontIndex)
        ("MSGothic",  "C:/Windows/Fonts/msgothic.ttc",   0),  # MS ゴシック
        ("MSMincho",  "C:/Windows/Fonts/msmincho.ttc",   0),  # MS 明朝
        ("YuGothic",  "C:/Windows/Fonts/YuGothR.ttc",    0),  # 游ゴシック
        ("MeiryoR",   "C:/Windows/Fonts/meiryo.ttc",     0),  # メイリオ
    ]
    for reg_name, ttc_path, idx in candidates_ttc:
        if Path(ttc_path).exists():
            try:
                pdfmetrics.registerFont(
                    TTFont(reg_name, ttc_path, subfontIndex=idx)
                )
                font_name = reg_name
                break
            except Exception:
                continue

    # Windows フォントが見つからない場合は CID フォント（Mac/Linux）を試みる
    if font_name == "Helvetica":
        for candidate in ("HeiseiKakuGo-W5", "HeiseiMin-W3", "STSong-Light"):
            try:
                pdfmetrics.registerFont(UnicodeCIDFont(candidate))
                font_name = candidate
                break
            except Exception:
                continue

    results: list[Path] = []
    n = len(files)
    page_w, page_h = A4
    margin = 50.0
    font_size = 11
    leading = font_size * 1.6

    for i, f_str in enumerate(files):
        f = Path(f_str)
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        dst = out_dir / (f.stem + ".pdf")

        c = rl_canvas.Canvas(str(dst), pagesize=A4)
        c.setFont(font_name, font_size)
        y = page_h - margin - font_size

        for line in lines:
            if y < margin:
                c.showPage()
                c.setFont(font_name, font_size)
                y = page_h - margin - font_size
            c.drawString(margin, y, line or " ")
            y -= leading

        c.save()
        results.append(dst)
        progress((i + 1) / n)

    return results


# ══════════════════════════════════════════════════════════════════
# GUI
# ══════════════════════════════════════════════════════════════════

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

_MODE_LABELS = [m[0] for m in CONVERSION_MODES]


class ConverterApp:
    """メインアプリケーションクラス"""

    def __init__(self) -> None:
        # ── ルートウィンドウ ──────────────────────────────────────
        # tkinterdnd2 が使用可能な場合: TkinterDnD.Tk を基底に
        # それ以外: CTk を使用（DnD なし）
        if HAS_DND:
            self.root = TkinterDnD.Tk()
        else:
            self.root = ctk.CTk()

        self.root.title("File Format Converter")
        self.root.geometry("760x700")
        self.root.minsize(620, 580)

        # デフォルト保存先（Downloads がなければ ホーム）
        _dl = Path.home() / "Downloads"
        self._default_out = str(_dl if _dl.exists() else Path.home())

        self._files: list[str] = []
        self._build_ui()

    # ── UI 構築 ───────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ─ タイトル ─────────────────────────────────────────────
        ctk.CTkLabel(
            self.root,
            text="📂  File Format Converter",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(pady=(18, 4))

        # ─ 変換タイプ ────────────────────────────────────────────
        row_mode = ctk.CTkFrame(self.root, fg_color="transparent")
        row_mode.pack(fill="x", padx=24, pady=(6, 2))
        ctk.CTkLabel(row_mode, text="変換タイプ:", width=92, anchor="w").pack(side="left")
        self._mode_var = tk.StringVar(value=_MODE_LABELS[0])
        ctk.CTkComboBox(
            row_mode,
            values=_MODE_LABELS,
            variable=self._mode_var,
            width=450,
            command=self._on_mode_change,
        ).pack(side="left", padx=8)

        # ─ ファイルリスト ／ ドロップゾーン ──────────────────────
        drop_frame = ctk.CTkFrame(self.root)
        drop_frame.pack(fill="both", expand=True, padx=24, pady=10)

        hint = (
            "ここにファイルをドラッグ＆ドロップ  または  ボタンで選択"
            if HAS_DND
            else "下のボタンでファイルを選択してください（D&D は tkinterdnd2 が必要）"
        )
        ctk.CTkLabel(
            drop_frame, text=hint,
            font=ctk.CTkFont(size=12), text_color="gray",
        ).pack(pady=(10, 4))

        self._listbox = ctk.CTkTextbox(
            drop_frame, state="disabled", height=160,
            font=ctk.CTkFont(family="Courier", size=11),
        )
        self._listbox.pack(fill="both", expand=True, padx=12, pady=4)

        row_btn = ctk.CTkFrame(drop_frame, fg_color="transparent")
        row_btn.pack(fill="x", padx=12, pady=(4, 10))

        ctk.CTkButton(
            row_btn, text="＋ ファイルを選択", width=150,
            command=self._browse_files,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            row_btn, text="🗑 クリア", width=100,
            fg_color="gray40", hover_color="gray30",
            command=self._clear_files,
        ).pack(side="left", padx=6)

        self._count_lbl = ctk.CTkLabel(
            row_btn, text="", font=ctk.CTkFont(size=12),
        )
        self._count_lbl.pack(side="left", padx=10)

        # DnD 登録：ウィンドウ全体をドロップ対象に
        if HAS_DND:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>", self._on_drop)

        # ─ 出力 PDF ファイル名（imgs2pdf のみ表示）────────────────
        self._name_row = ctk.CTkFrame(self.root, fg_color="transparent")
        ctk.CTkLabel(
            self._name_row, text="出力ファイル名:", width=110, anchor="w",
        ).pack(side="left")
        self._name_var = tk.StringVar(value="output")
        ctk.CTkEntry(
            self._name_row, textvariable=self._name_var, width=230,
        ).pack(side="left", padx=8)
        ctk.CTkLabel(self._name_row, text=".pdf").pack(side="left")

        # ─ 保存先フォルダ ─────────────────────────────────────────
        self._out_row = ctk.CTkFrame(self.root, fg_color="transparent")
        self._out_row.pack(fill="x", padx=24, pady=(2, 8))
        ctk.CTkLabel(
            self._out_row, text="保存先フォルダ:", width=110, anchor="w",
        ).pack(side="left")
        self._out_var = tk.StringVar(value=self._default_out)
        ctk.CTkEntry(
            self._out_row, textvariable=self._out_var, width=410,
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            self._out_row, text="参照", width=70,
            command=self._browse_out,
        ).pack(side="left")

        # ─ 変換ボタン ─────────────────────────────────────────────
        self._cvt_btn = ctk.CTkButton(
            self.root,
            text="⚡  変換開始",
            height=46,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._start,
        )
        self._cvt_btn.pack(fill="x", padx=24, pady=(4, 6))

        # ─ プログレスバー & ステータス ──────────────────────────
        self._pbar = ctk.CTkProgressBar(self.root, height=14)
        self._pbar.set(0)
        self._pbar.pack(fill="x", padx=24, pady=4)

        self._status_lbl = ctk.CTkLabel(
            self.root,
            text="ファイルを選択して変換を開始してください",
            text_color="gray",
            font=ctk.CTkFont(size=12),
        )
        self._status_lbl.pack(pady=(4, 16))

        # 初期モード適用
        self._on_mode_change()

    # ── イベントハンドラ ──────────────────────────────────────────

    def _get_mode(self) -> tuple[str, str]:
        """現在選択中の (カテゴリ, 拡張子) を返す"""
        label = self._mode_var.get()
        for lbl, cat, ext in CONVERSION_MODES:
            if lbl == label:
                return cat, ext
        return CONVERSION_MODES[0][1], CONVERSION_MODES[0][2]

    def _on_mode_change(self, _: str = "") -> None:
        """変換タイプ変更時: imgs2pdf のみ出力ファイル名欄を表示"""
        cat, _ = self._get_mode()
        if cat == "imgs2pdf":
            self._name_row.pack(
                fill="x", padx=24, pady=(2, 6),
                before=self._out_row,
            )
        else:
            self._name_row.pack_forget()

    def _browse_files(self) -> None:
        cat, _ = self._get_mode()
        paths = filedialog.askopenfilenames(
            title="ファイルを選択",
            filetypes=_FILE_FILTERS.get(cat, [("すべて", "*.*")]),
            parent=self.root,
        )
        if paths:
            self._add_files(list(paths))

    def _browse_out(self) -> None:
        d = filedialog.askdirectory(
            initialdir=self._out_var.get(),
            title="保存先フォルダを選択",
            parent=self.root,
        )
        if d:
            self._out_var.set(d)

    def _on_drop(self, event) -> None:
        """D&D でファイルが投下された時のコールバック"""
        paths = self.root.tk.splitlist(event.data)
        self._add_files([p for p in paths if os.path.isfile(p)])

    def _add_files(self, paths: list[str]) -> None:
        for p in paths:
            if p not in self._files:
                self._files.append(p)
        self._refresh_list()

    def _clear_files(self) -> None:
        self._files.clear()
        self._refresh_list()
        self._pbar.set(0)
        self._set_status("ファイルリストをクリアしました")

    def _refresh_list(self) -> None:
        self._listbox.configure(state="normal")
        self._listbox.delete("0.0", "end")
        for p in self._files:
            self._listbox.insert("end", f"  {Path(p).name}\n")
        self._listbox.configure(state="disabled")
        n = len(self._files)
        self._count_lbl.configure(text=f"{n} ファイル選択中" if n else "")

    def _set_status(self, text: str) -> None:
        self._status_lbl.configure(text=text)

    # ── 変換処理 ──────────────────────────────────────────────────

    def _start(self) -> None:
        if not self._files:
            messagebox.showwarning("警告", "ファイルが選択されていません。", parent=self.root)
            return
        out_dir = Path(self._out_var.get())
        if not out_dir.is_dir():
            messagebox.showerror(
                "エラー",
                f"保存先フォルダが見つかりません:\n{out_dir}",
                parent=self.root,
            )
            return

        self._cvt_btn.configure(state="disabled", text="⏳  変換中…")
        self._pbar.set(0)
        self._set_status("変換を開始しています…")
        threading.Thread(target=self._run, args=(out_dir,), daemon=True).start()

    def _run(self, out_dir: Path) -> None:
        cat, ext = self._get_mode()
        files = self._files[:]

        def cb(ratio: float) -> None:
            v = float(ratio)
            self.root.after(0, lambda: self._on_progress(v))

        try:
            if cat == "image":
                results = convert_image(files, out_dir, ext, cb)
            elif cat == "pdf2img":
                results = pdf_to_images(files, out_dir, ext, cb)
            elif cat == "imgs2pdf":
                name = self._name_var.get().strip() or "output"
                results = images_to_pdf(files, out_dir, name, cb)
            else:  # txt2pdf
                results = txt_to_pdf(files, out_dir, cb)

            self.root.after(0, lambda r=results: self._on_done(r))

        except Exception:
            tb = traceback.format_exc()
            self.root.after(0, lambda t=tb: self._on_error(t))

    def _on_progress(self, ratio: float) -> None:
        self._pbar.set(ratio)
        self._set_status(f"変換中… {int(ratio * 100)}%")

    def _on_done(self, results: list[Path]) -> None:
        self._cvt_btn.configure(state="normal", text="⚡  変換開始")
        self._pbar.set(1.0)
        n = len(results)
        self._set_status(f"✅ 完了 ─ {n} ファイルを出力しました")
        messagebox.showinfo(
            "変換完了 ✅",
            f"{n} ファイルの変換が完了しました！\n\n保存先:\n{self._out_var.get()}",
            parent=self.root,
        )

    def _on_error(self, tb: str) -> None:
        self._cvt_btn.configure(state="normal", text="⚡  変換開始")
        self._set_status("❌ エラーが発生しました")
        messagebox.showerror(
            "変換エラー",
            f"変換中にエラーが発生しました:\n\n{tb[:1000]}",
            parent=self.root,
        )

    def run(self) -> None:
        self.root.mainloop()


# ══════════════════════════════════════════════════════════════════
# エントリーポイント
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = ConverterApp()
    app.run()