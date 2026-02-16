import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

INPUT_PATH = Path("input/test01.mp3")  # もしmp3なら audio.mp3 に変更
OUT_DIR = Path("work")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY が見つかりません。.env を確認してください。")

    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"音声ファイルがありません: {INPUT_PATH}")

    client = OpenAI(api_key=api_key)

    # 文字起こし（最小構成）
    with INPUT_PATH.open("rb") as f:
        result = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=f,
        )

    # 出力
    text = result.text
    (OUT_DIR / "transcript.txt").write_text(text, encoding="utf-8")
    print("✅ transcript saved:", OUT_DIR / "transcript.txt")
    print("\n--- transcript preview ---\n")
    print(text[:800])

if __name__ == "__main__":
    main()
