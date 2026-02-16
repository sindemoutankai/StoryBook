import base64
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

PLAN_PATH = Path("work/book_plan.json")
OUT_DIR = Path("output/pages")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 画像サイズは縦長が絵本向き（必要なら変えてOK）
IMAGE_SIZE = "1024x1024"  # 他: "1024x1024", "1536x1024" など
MODEL = "gpt-image-1"

def _to_filename(page_num: int) -> Path:
    return OUT_DIR / f"{page_num:02d}.png"

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY が見つかりません。.env を確認してください。")

    if not PLAN_PATH.exists():
        raise FileNotFoundError(f"{PLAN_PATH} が見つかりません。")

    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    pages = plan.get("pages", [])
    if not pages:
        raise RuntimeError("book_plan.json に pages がありません。")

    client = OpenAI(api_key=api_key)

    # タイトルやスタイルを少し補強（任意）
    style_bible = plan.get("style_bible", "")
    title = plan.get("title", "storybook")

    print(f"📘 Generating images for: {title}")
    print(f"pages: {len(pages)} | model: {MODEL} | size: {IMAGE_SIZE}\n")

    for p in pages:
        page_num = int(p["page"])
        out_path = _to_filename(page_num)

        # 既に生成済みならスキップ（再実行に強い）
        if out_path.exists():
            print(f"skip page {page_num:02d} (already exists)")
            continue

        prompt = p.get("image_prompt_api", "").strip()
        if not prompt:
            raise RuntimeError(f"page {page_num} に image_prompt_api がありません。")

        # スタイルを全ページで統一したい場合、ここで足す
        full_prompt = f"{style_bible}\n\n{prompt}".strip()

        print(f"→ generating page {page_num:02d} ...")

        result = client.images.generate(
            model=MODEL,
            size=IMAGE_SIZE,
            prompt=full_prompt,
        )

        # gpt-image-1 は base64 で返る
        b64 = result.data[0].b64_json
        img_bytes = base64.b64decode(b64)

        out_path.write_bytes(img_bytes)
        print(f"   saved: {out_path}")

    print("\n✅ Done! Images saved to output/pages/")

if __name__ == "__main__":
    main()

