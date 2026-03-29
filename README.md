# StoryBook - AI絵本自動生成システム

ユーザーとのAIチャットや音声録音を入口に、絵本のプランニング・画像生成・PDF作成・Web公開までを一括で行うパイプラインです。

---

## 必要なもの

- Python 3.11+
- OpenAI APIキー（チャット・文字起こし・画像生成に使用）
- ComfyUI（`--engine comfy` を使う場合のみ）

### インストール

```bash
pip install -r requirements.txt
```

### `.env` ファイルを作る（プロジェクトルートに置く）

```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx

# ComfyUIを使う場合（省略可、デフォルトは http://127.0.0.1:8188）
COMFY_BASE_URL=http://127.0.0.1:8188
```

---

## 基本的な使い方

すべて `pipeline.py` 1本で実行できます。

### パターン1: AIチャットで悩みを話して絵本を作る（一番よく使う）

```bash
python pipeline.py --chat
```

AIカウンセラーが対話形式で話を引き出し、その内容を絵本にします。
チャット中に `/end` または `/save` で終了すると次のステップへ進みます。

### パターン2: 音声ファイルを文字起こしして絵本を作る

```bash
python pipeline.py --input-audio input/test01.wav
```

### パターン3: その場でマイク録音して絵本を作る

```bash
python pipeline.py --record
```

### パターン4: 画像生成にComfyUI（FLUX）を使う

```bash
python pipeline.py --chat --engine comfy
```

---

## パイプラインのステップ

```
1. transcript生成  → work/transcript.txt
2. book_plan生成   → work/book_plan.json  （GPT-4.1-mini）
3. 画像生成        → output/pages/01.png, 02.png ...
4. PDF作成         → output/book.pdf
5. 公開            → docs/books/タイムスタンプ/
6. 本棚更新        → docs/index.html
```

---

## よく使うオプション

### 特定ステップをスキップする

既にtranscriptが手元にある場合など、途中から再実行できます。

```bash
# 文字起こしをスキップして book_plan から再実行
python pipeline.py --skip-transcribe

# 画像もスキップしてPDFだけ作り直す
python pipeline.py --skip-transcribe --skip-plan --skip-images

# PDF・公開・本棚だけスキップ
python pipeline.py --skip-pdf --skip-publish --skip-shelf
```

### 画像を特定ページだけ再生成する

```bash
# 3ページ目だけ再生成（既存ファイルを上書き）
python pipeline.py --skip-transcribe --skip-plan --start-page 3 --end-page 3 --force

# 5〜7ページを再生成
python pipeline.py --skip-transcribe --skip-plan --start-page 5 --end-page 7 --force
```

### ComfyUI（FLUX）の画像パラメータを変える

```bash
python pipeline.py --engine comfy --seed 999 --width 1024 --height 1536 --steps 30 --guidance 3.0
```

| オプション | デフォルト | 説明 |
|---|---|---|
| `--seed` | 12345 | 乱数シード |
| `--width` | 1024 | 画像の幅 |
| `--height` | 1024 | 画像の高さ |
| `--steps` | 35 | サンプリングステップ数 |
| `--guidance` | 2.5 | CFGスケール（高いほどプロンプトに忠実） |
| `--lora-model-strength` | 0.7 | LoRAの適用強度 |

---

## カスタマイズしたい場合

### 絵本のページ数・対象年齢・言語を変える

`book_plan.py` の上部を直接編集します。

```python
PAGE_COUNT = 10    # ← ページ数
TARGET_AGE = "10"  # ← 対象年齢
LANGUAGE = "ja"    # ← 言語（"ja" / "en" など）
```

### 絵本プランのプロンプトを変える

`work/prompt.txt` を作成して書き換えます（存在すればこちらが優先されます）。
ファイルがない場合は `book_plan.py` 内の `DEFAULT_PROMPT` が使われます。

テンプレート変数として以下が使えます：

```
{TARGET_AGE}        対象年齢
{PAGE_COUNT}        ページ数
{STYLE_BIBLE}       画風の基本方針
{LANGUAGE}          言語
{transcript}        チャット/音声の文字起こし
{CHARACTER_ANCHOR}  キャラクター固定情報（work/character_anchor.json）
```

### 画像のスタイルを変える（OpenAI）

`book_plan.py` の `STYLE_BIBLE` を変更します。

```python
STYLE_BIBLE = (
    "温かい絵本の挿絵。やわらかい水彩、やさしいパステル、"
    "クリーンな輪郭線、安心感のある光、子ども向け、過度に写実的にしない。"
)
```

### ComfyUIのノード設定を変える

`config_flux.json` を編集します。
ノードIDは ComfyUI の API形式ワークフロー（`work/picturebook_api_flux.json`）のキーと対応しています。

```json
{
  "nodes": {
    "prompt": "6",    ← CLIPTextEncodeノードのID
    "scheduler": "17",
    "noise": "25",
    ...
  }
}
```

### キャラクターの外見を固定する（全ページ一貫させる）

`work/character_anchor.json` を作成します。例：

```json
{
  "main_character": "a small brown rabbit wearing a red scarf, round eyes, fluffy tail"
}
```

---

## ディレクトリ構成

```
Storybook/
├── pipeline.py              # パイプライン統括（ここを実行）
├── ai_counselor_chat.py     # AIカウンセラーチャット
├── record_audio.py          # マイク録音
├── transcribe.py            # 音声→テキスト（Whisper）
├── book_plan.py             # 絵本プラン生成（GPT-4.1-mini）
├── generate_images.py       # 画像生成（OpenAI）
├── generate_images_flux.py  # 画像生成（ComfyUI/FLUX）
├── generate_images_sd.py    # 画像生成（ComfyUI/SD）
├── make_pdf.py              # PDF作成
├── publish_book.py          # docs/books/ に公開
├── build_shelf.py           # docs/index.html（本棚）更新
├── config_flux.json         # ComfyUI/FLUX設定
├── .env                     # APIキーなど（要作成）
├── input/                   # 音声ファイルの置き場所
├── work/                    # 中間ファイル（transcript, book_plan など）
├── output/
│   ├── pages/               # 生成画像（01.png, 02.png ...）
│   └── book.pdf             # 生成PDF
└── docs/
    ├── index.html           # 本棚ページ（GitHub Pages で公開可）
    └── books/
        └── YYYYMMDD_HHMMSS/ # 書籍ごとのディレクトリ
            ├── viewer.html  # ページめくりビューア
            ├── details.html # プロンプト・transcriptの確認
            ├── book.pdf
            ├── book_plan.json
            └── pages/
```

---

## トラブルシューティング

| エラー | 対処 |
|---|---|
| `OPENAI_API_KEY が見つかりません` | `.env` にキーを記載したか確認 |
| `transcript.txt が見つかりません` | `--skip-transcribe` を外すか、`work/transcript.txt` を手動で用意 |
| `book_plan.json に pages がありません` | `work/book_plan.json` を確認。LLMの出力が想定と違う場合は `work/prompt.txt` を調整 |
| 画像が生成されない（ComfyUI） | ComfyUI が起動しているか、`config_flux.json` の `comfy_base_url` とノードIDを確認 |
| PDFの日本語が文字化けする | `reportlab` の `HeiseiKakuGo-W5` フォントが使えるか確認 |
