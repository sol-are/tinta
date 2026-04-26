# tinta

学術論文の PDF を [GLM-OCR](https://github.com/zai-org/GLM-OCR) で読み取り、整形された Markdown に変換する CLI ツールです。

## 特徴

- **バックエンドプリセット** — Ollama / vLLM / SGLang / MLX / llama.cpp / LM Studio / GLM-OCR 自前サーバー / MaaS をワンフラグで切替
- **バッチ処理 + resume** — ディレクトリやワイルドカードを直接渡せて、`--skip-existing` で完了済みをスキップ
- **Watchdog + Ollama キュー drain** — `--max-pdf-time` で 1 PDF あたりの上限。タイムアウト時は自動で Ollama のキューを drain
- **2 段階の出力** — 本文のみの `<stem>.md`（主成果物）と OCR 生テキスト `raw.md`（監査サイドカー）を同時生成
- **画像の自動抽出** — bbox 情報から `imgs/` に切り出し
- **品質チェック + メタデータ** — SHA-256, ページ数, degraded ページ数, 使用 backend/model を `meta.json` に記録

## 必要要件

- Python 3.12 以上
- [uv](https://docs.astral.sh/uv/) (推奨パッケージマネージャ)

## インストール

```bash
uv tool install git+https://github.com/sol-are/tinta
```

## 使い方

### 単発

```bash
tinta paper.pdf --backend ollama
```

### バッチ (ディレクトリ全体を再帰)

```bash
tinta papers/ --backend ollama --skip-existing --max-pdf-time 1800
```

### MaaS (Zhipu API)

```bash
tinta paper.pdf --backend maas -k $ZHIPU_API_KEY
```

### 設定の確認 (実行せずに dump)

```bash
tinta paper.pdf --backend ollama --print-config
```

## バックエンドプリセット

| `--backend` | エンドポイント | model 既定 | max_workers |
|---|---|---|---|
| `ollama` | `http://localhost:11434/api/generate` | `glm-ocr:latest` | 4 |
| `glm-ocr` | `http://localhost:8080/v1/chat/completions` | (config) | 32 |
| `vllm` | `http://localhost:8000/v1/chat/completions` | (config) | 32 |
| `sglang` | `http://localhost:30000/v1/chat/completions` | (config) | 32 |
| `mlx` | `http://localhost:8080/v1/chat/completions` | (config) | 2 |
| `llama-cpp` | `http://localhost:8080/v1/chat/completions` | (config) | 4 |
| `lmstudio` | `http://localhost:1234/v1/chat/completions` | (config) | 4 |
| `maas` | `https://open.bigmodel.cn/...` | `glm-ocr` | 8 |

個別フラグ (`--api-url`, `--model`, `--max-workers` など) はプリセットを上書きします。

## 主要オプション

| オプション | 説明 |
|---|---|
| `--out-dir`, `-o` | 出力先 (既定 `./out`) |
| `--backend` | バックエンドプリセット |
| `--skip-existing` | `<out>/<stem>/meta.json` (または `--no-artifacts` 時は `<stem>.md`) があればスキップ |
| `--max-pdf-time SECS` | 1 PDF あたりの watchdog。spawn サブプロセスで実行 |
| `--max-workers N` | OCR 並列数。`pipeline.max_workers` を上書き |
| `--request-timeout SECS` | OCR API リクエストタイムアウト |
| `--connect-timeout SECS` | OCR API 接続タイムアウト |
| `--retry-max-attempts N` | 失敗時のリトライ回数 |
| `--api-url`, `-u` | カスタム URL (プリセットを上書き) |
| `--api-key`, `-k` | API キー (MaaS モード切替) |
| `--model`, `-m` | モデル名 |
| `--no-artifacts` | 監査サイドカー (`raw.md`, `meta.json`) を出力しない (`<stem>.md` + `imgs/` のみ) |
| `--no-health-check` | 起動時の到達確認をスキップ |
| `--print-config` | 解決後の設定を表示して終了 |

## 環境変数

| 変数 | 同等フラグ |
|---|---|
| `TINTA_BACKEND` | `--backend` |
| `TINTA_API_URL` | `--api-url` |
| `TINTA_MODEL` | `--model` |
| `TINTA_MAX_WORKERS` | `--max-workers` |
| `TINTA_REQUEST_TIMEOUT` | `--request-timeout` |
| `TINTA_CONNECT_TIMEOUT` | `--connect-timeout` |
| `TINTA_RETRY_MAX_ATTEMPTS` | `--retry-max-attempts` |
| `GLMOCR_API_KEY` / `ZHIPU_API_KEY` | `--api-key` |

優先順位: **CLI フラグ > 環境変数 > プリセット > SDK 既定**

## 出力構成

```
out/<論文名>/
├── <論文名>.md     # 本文 (focused) — 主成果物
├── imgs/           # 抽出された図表画像
│   ├── figure_0.png
│   └── ...
├── raw.md          # OCR 生テキスト (--no-artifacts 時は省略)
└── meta.json       # メタデータ (--no-artifacts 時は省略)
```

`raw.md` / `meta.json` は監査用サイドカー — 削除しても `<論文名>.md` + `imgs/` は完全に機能します（画像参照は `imgs/figure_x.png` の同階層相対パス）．

### meta.json の内容

| フィールド | 説明 |
|---|---|
| `source_pdf` | 入力 PDF の絶対パス |
| `raw_md_sha256` / `focused_md_sha256` | SHA-256 ハッシュ |
| `raw_bytes` / `focused_bytes` | バイト数 |
| `pages_processed` | 処理ページ数 |
| `degraded_pages` | OCR が空文字を返したページ数 (タイムアウト等) |
| `backend` | 使用したプリセット名 |
| `model` | 使用したモデル名 |
| `suspicious` / `suspicion_reasons` | 品質警告 |

## Python API

```python
from pathlib import Path
from tinta.core import run_one
from tinta.settings import Settings

settings = Settings.resolve(backend="ollama")
run_one(Path("paper.pdf"), Path("./out"), no_artifacts=False, settings=settings)
```

バッチで使う場合:

```python
from tinta.batch import expand_inputs, run_batch

pdfs = expand_inputs([Path("./papers")])
result = run_batch(pdfs, Path("./out"), no_artifacts=False,
                   settings=settings, skip_existing=True, max_pdf_time=1800)
print(result)
```

## トラブルシューティング

- **`[preflight] Cannot reach ...`** — バックエンドが起動していません。Ollama なら `ollama serve`、vLLM なら `vllm serve <model>` を実行
- **`[preflight] Model 'X' not in advertised list`** — モデル名が違う or alias を使ったとき。**警告のみで処理は継続**します。`vllm --served-model-name` 等を使っている場合は無視可
- **Ollama batch でタイムアウトが連発する** — `--max-pdf-time 1800` (またはより短い値) を必ず指定。`max_workers` は preset の `4` 既定を維持推奨
- **複数 PDF を渡したのに hint が出る** — `--max-pdf-time` を付けて再実行
