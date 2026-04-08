# tinta

学術論文の PDF を [GLM-OCR](https://github.com/GLM-Opensource/glmocr) で読み取り、整形された Markdown に変換する CLI ツールです。

## 特徴

- **2 つの動作モード** — セルフホスト (`selfhosted`) と MaaS API (`maas`) を切り替え可能
- **2 段階の出力** — OCR そのままの `raw.md` と、参考文献・ヘッダ/フッタを除去した `focused.md` を同時に生成
- **画像の自動抽出** — PDF 内の図表を bbox 情報から切り出し、`imgs/` ディレクトリに保存
- **品質チェック** — focused テキストが極端に短い・raw に対する比率が低い場合に警告を出力
- **メタデータ記録** — SHA-256 ハッシュ、バイト数、ページ数などを `meta.json` に保存

## 必要要件

- Python 3.12 以上
- [uv](https://docs.astral.sh/uv/) (推奨パッケージマネージャ)

## インストール

```bash
uv tool install git+https://github.com/sol-are/tinta
```

## 使い方

### MaaS (API) モード

GLM-OCR のクラウド API を利用するモードです。

```bash
tinta maas paper.pdf
```

| オプション | 説明 |
|---|---|
| `--out-dir`, `-o` | 出力ディレクトリ (デフォルト: `./out`) |
| `--md-only` | Markdown のみ出力 (`meta.json` をスキップ) |
| `--api-key` | API キー (環境変数 `GLMOCR_API_KEY` でも設定可) |

### セルフホストモード

ローカルまたは自前サーバで GLM-OCR を動かすモードです。

```bash
tinta selfhosted paper.pdf --api-url http://localhost:8000
```

| オプション | 説明 |
|---|---|
| `--out-dir`, `-o` | 出力ディレクトリ (デフォルト: `./out`) |
| `--md-only` | Markdown のみ出力 (`meta.json` をスキップ) |
| `--api-url` | セルフホストサーバの API URL |
| `--model` | 使用するモデル名 |

### Python API

CLI を介さず、Python から直接呼び出すこともできます。

```python
from tinta.core import run

run(
    pdf=Path("paper.pdf"),
    out_dir=Path("./out"),
    md_only=False,
    mode="maas",
    api_key="sk-...",
)
```

個別のステップを使う場合:

```python
from tinta.core import convert_pdf, build_focused, check_quality

raw_md, pages = convert_pdf(Path("paper.pdf"), mode="maas")
focused_md = build_focused(raw_md)
suspicious, reasons = check_quality(raw_md, focused_md)
```

## 出力構成

```
out/<論文名>/
├── raw.md          # OCR 生テキスト
├── focused.md      # 本文のみ (参考文献等を除去)
├── meta.json       # メタデータ (--md-only 時は省略)
└── imgs/           # 抽出された図表画像
    ├── figure_0.png
    ├── figure_1.png
    └── ...
```

### meta.json の内容

| フィールド | 説明 |
|---|---|
| `source_pdf` | 入力 PDF の絶対パス |
| `raw_md_sha256` | `raw.md` の SHA-256 ハッシュ |
| `focused_md_sha256` | `focused.md` の SHA-256 ハッシュ |
| `raw_bytes` | `raw.md` のバイト数 |
| `focused_bytes` | `focused.md` のバイト数 |
| `suspicious` | 品質チェックで警告があるか |
| `suspicion_reasons` | 警告の理由リスト |
| `pages_processed` | 処理されたページ数 |
