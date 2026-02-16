import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

TRANSCRIPT_PATH = Path("work/transcript.txt")
OUT_PATH = Path("work/book_plan.json")

PAGE_COUNT = 8  # まずは固定でOK（8ページ）
TARGET_AGE = "5-8"
LANGUAGE = "ja"

STYLE_BIBLE = (
    "温かい絵本の挿絵。やわらかい水彩、やさしいパステル、"
    "クリーンな輪郭線、安心感のある光、子ども向け、過度に写実的にしない。"
)

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY が見つかりません。.env を確認してください。")

    if not TRANSCRIPT_PATH.exists():
        raise FileNotFoundError(f"{TRANSCRIPT_PATH} が見つかりません。transcribeの出力を確認してください。")

    transcript = TRANSCRIPT_PATH.read_text(encoding="utf-8").strip()
    if len(transcript) < 50:
        raise RuntimeError("transcriptが短すぎます。音声が正しく文字起こしできているか確認してください。")

    client = OpenAI(api_key=api_key)

    prompt = f"""
あなたは優秀な児童向け絵本編集者です。
以下の会話ログ（相談内容）から、{TARGET_AGE}向けの絵本を{PAGE_COUNT}ページで作るための設計JSONを作ってください。

要件:
- 言語: {LANGUAGE}
- 本文は短め（1ページ 1〜3文）
- ネガティブすぎない。最後は前向きな余韻。
- 会話由来の具体要素（悩み/好きなもの/登場人物/場所など）を最低3つ以上入れる
- 各ページに挿絵指示を作る（画像生成用）
- 出力は「JSONのみ」。余計な文章は禁止。

出力JSONスキーマ（厳守）:
{{
  "title": "string",
  "target_age": "{TARGET_AGE}",
  "page_count": {PAGE_COUNT},
  "style_bible": "{STYLE_BIBLE}",
  "characters": [
    {{"name":"string","description":"string"}}
  ],
  "pages": [
    {{
      "page": 1,
      "text": "string",
      "scene_summary": "string",
      "must_have": ["string","string"],
      "camera": "string",
      "image_prompt_api": "string",
      "image_prompt_sd": "string",
      "negative_prompt_sd": "string"
    }}
  ]
}}

会話ログ:
\"\"\"{transcript}\"\"\"
""".strip()

    # Responses API相当の使い方（openai python SDKは内部で対応）
    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )

    # SDKの戻りからテキスト抽出（簡易）
    text_out = resp.output_text

    # JSONとして保存（整形）
    data = json.loads(text_out)
    OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("✅ book_plan saved:", OUT_PATH)
    print("title:", data.get("title"))
    print("pages:", len(data.get("pages", [])))

if __name__ == "__main__":
    main()
