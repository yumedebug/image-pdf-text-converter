# 📂 File Format Converter

様々なファイル形式を相互変換できる Python 製デスクトップアプリです。
CustomTkinter によるモダンな GUI で、ドラッグ＆ドロップにも対応しています。

---

## ✨ 対応している変換

| 変換内容 | 入力 | 出力 |
|---|---|---|
| 画像変換 | JPG / PNG / WebP | JPG / PNG / WebP |
| PDF を画像化 | PDF | PNG / WebP（ページごとに1ファイル） |
| 画像を PDF に結合 | JPG / PNG（複数可） | PDF（1ファイルに結合） |
| テキストを PDF に変換 | TXT | PDF（日本語対応） |

---

## 🖥 画面の使い方

1. **変換タイプ** をドロップダウンで選択する
2. ファイルをウィンドウに **ドラッグ＆ドロップ** または **「＋ ファイルを選択」** ボタンで追加する
3. **出力ファイル名** を入力する（ファイルを追加すると自動で入力される）
4. **保存先フォルダ** を確認・変更する（デフォルトは Downloads フォルダ）
5. **「⚡ 変換開始」** ボタンをクリックする
6. プログレスバーが進み、完了するとポップアップで通知される

### 出力ファイル名のルール

| 変換タイプ | ファイルが1つ | ファイルが複数 |
|---|---|---|
| 画像変換 | `output.jpg` | `output_001.jpg`, `output_002.jpg`, … |
| PDF → 画像 | `output_p001.png`, `output_p002.png`, … | `output_001_p001.png`, … |
| 画像 → PDF | `output.pdf` | （常に1ファイルに結合） |
| TXT → PDF | `output.pdf` | `output_001.pdf`, `output_002.pdf`, … |

---

## 🛠 セットアップ手順

### 動作環境

- Python 3.9 以上
- Windows 10 / 11（推奨）
- macOS / Linux（D&D と日本語 PDF フォントは一部制限あり）

### 1. 仮想環境の作成（推奨）

```bash
python -m venv venv
```

```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. ライブラリのインストール

```bash
pip install -r requirements.txt
```

または個別にインストールする場合：

```bash
pip install customtkinter Pillow PyMuPDF reportlab tkinterdnd2
```

### 3. 起動

```bash
python converter.py
```

---

## 📦 exe ファイルへのパッケージ化（Windows）

### PyInstaller のインストール

```bash
pip install pyinstaller
```

### ビルド（spec ファイルを使用・推奨）

```bash
pyinstaller converter.spec
```

ビルド完了後、`dist/FileConverter.exe` が生成されます。

### ビルド（コマンド一発・簡易版）

```bash
pyinstaller --onefile --windowed ^
    --name FileConverter ^
    --collect-all customtkinter ^
    --collect-all tkinterdnd2 ^
    --collect-data reportlab ^
    --hidden-import PIL._tkinter_finder ^
    --hidden-import fitz ^
    converter.py
```

---

## 📁 ファイル構成

```
.
├── converter.py       # メインアプリケーション
├── converter.spec     # PyInstaller ビルド設定
├── requirements.txt   # 依存ライブラリ一覧
└── README.md          # このファイル
```

---

## 📚 使用ライブラリ

| ライブラリ | バージョン | 役割 |
|---|---|---|
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | 5.2.0 以上 | モダンな GUI フレームワーク |
| [Pillow](https://pillow.readthedocs.io/) | 10.0.0 以上 | 画像の読み書き・変換 |
| [PyMuPDF](https://pymupdf.readthedocs.io/) | 1.23.0 以上 | PDF の読み取り・生成（poppler 不要） |
| [ReportLab](https://www.reportlab.com/) | 4.0.0 以上 | TXT → PDF 生成・日本語フォント対応 |
| [tkinterdnd2](https://github.com/pmgagne/tkinterdnd2) | 0.3.0 以上 | ドラッグ＆ドロップ対応（任意） |

> **補足:** `tkinterdnd2` はインストールしなくても動作します。その場合はドラッグ＆ドロップが無効になり、ボタン選択のみでファイルを追加できます。

---

## 🔤 日本語フォントについて（TXT → PDF）

TXT を PDF に変換する際のフォントは以下の優先順位で自動選択されます。

1. **MS ゴシック** — `C:/Windows/Fonts/msgothic.ttc`（Windows 標準）
2. MS 明朝 / 游ゴシック / メイリオ（Windows の他フォント）
3. HeiseiKakuGo-W5（ReportLab 内蔵 CID フォント・macOS / Linux 向け）
4. Helvetica（最終手段・ASCII のみ）

Windows 環境であれば MS ゴシックが自動的に使用されます。

---

## ❓ トラブルシューティング

**`ModuleNotFoundError` が出る**
仮想環境が有効化されていない可能性があります。`venv\Scripts\activate` を実行してから再度インストールしてください。

```bash
python -m pip install customtkinter Pillow PyMuPDF reportlab tkinterdnd2
```

**exe の初回起動が遅い**
`--onefile` 指定時は起動のたびに一時フォルダに展開するため、初回に数秒かかります。速度を優先する場合は `--onedir` に変更してフォルダ配布にしてください。

**Windows Defender にブロックされる**
署名なしの exe ファイルのため警告が表示されることがあります。「詳細情報」→「実行」をクリックすると起動できます。

**PDF → 画像 の変換が遅い**
`converter.py` 内の `_PDF_DPI = 150` の値を下げると処理が速くなります（画質は低下します）。

**ドラッグ＆ドロップが動かない**
`tkinterdnd2` がインストールされているか確認してください。インストール済みの場合、仮想環境が有効化された状態でインストールされているか確認してください。

---

## 📝 ライセンス

このソフトウェアは MIT ライセンスのもとで配布されています。
