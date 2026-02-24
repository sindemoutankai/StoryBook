import os
import argparse
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="input/test01.wav")
    args = parser.parse_args()

    audio_path = Path(args.input)
    out_dir = Path("work")
    out_dir.mkdir(parents=True, exist_ok=True)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY が見つかりません。.env を確認してください。")

    if not audio_path.exists():
        raise FileNotFoundError(f"音声ファイルがありません: {audio_path}")

    client = OpenAI(api_key=api_key)

    # 文字起こし
    with audio_path.open("rb") as f:
        result = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=f,
        )

    # 出力
    text = result.text
    out_path = out_dir / "transcript.txt"
    out_path.write_text(text, encoding="utf-8")

    print("✅ transcript saved:", out_path)
    print(f"🎧 input: {audio_path}")
    print("\n--- transcript preview ---\n")
    print(text[:800])


if __name__ == "__main__":
    main()