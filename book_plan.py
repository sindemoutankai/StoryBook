import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

PROMPT_PATH = Path("work/prompt.txt")
DEFAULT_PROMPT = """あなたは絵本編集者です。
（ここに保険のテンプレを書いておく。work/prompt.txt が無いときに使う）
会話ログ:
\"\"\"{transcript}\"\"\"
"""

load_dotenv()

TRANSCRIPT_PATH = Path("work/transcript.txt")
OUT_PATH = Path("work/book_plan.json")

PAGE_COUNT = 10
TARGET_AGE = "12-15"
LANGUAGE = "ja"

STYLE_BIBLE = (
    "温かい絵本の挿絵。やわらかい水彩、やさしいパステル、"
    "クリーンな輪郭線、安心感のある光、子ども向け、過度に写実的にしない。"
)

def load_prompt_template() -> str:
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return DEFAULT_PROMPT

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY が見つかりません。.env を確認してください。")

    if not TRANSCRIPT_PATH.exists():
        raise FileNotFoundError(f"{TRANSCRIPT_PATH} が見つかりません。")

    transcript = TRANSCRIPT_PATH.read_text(encoding="utf-8").strip()
    if len(transcript) < 50:
        raise RuntimeError("transcriptが短すぎます。")

    client = OpenAI(api_key=api_key)

    template = load_prompt_template()

    # prompt.txt 内の JSON の波括弧は {{ }} にしてある前提（あなたのテンプレはOK）
    prompt = template.format(
        TARGET_AGE=TARGET_AGE,
        PAGE_COUNT=PAGE_COUNT,
        STYLE_BIBLE=STYLE_BIBLE,
        LANGUAGE=LANGUAGE,
        transcript=transcript,
    )
    print("PROMPT_PATH:", PROMPT_PATH.resolve(), "exists:", PROMPT_PATH.exists())
    print("prompt length:", len(prompt))
    print("contains 'json'?:", "json" in prompt.lower())
    print("prompt head:", repr(prompt[:200]))

    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        # ★JSONを安定させたいなら（推奨）
        text={"format": {"type": "json_object"}},
    )

    text_out = resp.output_text
    print("---- output_text ----")
    print(repr(text_out))
    print("---- raw resp ----")
    print(resp)


    data = json.loads(text_out)
    OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("✅ book_plan saved:", OUT_PATH)
    print("title:", data.get("title"))
    print("pages:", len(data.get("pages", [])))

if __name__ == "__main__":
    main()
