import argparse
import subprocess
import sys
from pathlib import Path


def run_step(cmd: list[str], name: str):
    print(f"\n=== {name} ===")
    print(">", " ".join(str(c) for c in cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"{name} failed (exit={result.returncode})")


def pycmd(script: str, *args: str) -> list[str]:
    # 常に今のvenvのPythonを使う
    return [sys.executable, script, *args]


def main():
    parser = argparse.ArgumentParser(description="StoryBook pipeline runner")

    # 実行エンジン
    parser.add_argument("--engine", choices=["openai", "comfy"], default="openai", help="画像生成エンジン")

    # 録音 / 文字起こし
    parser.add_argument("--record", action="store_true", help="マイク録音してから transcribe")
    parser.add_argument("--audio-input", type=str, default=None, help="transcribe.py に渡す音声ファイルパス")
    parser.add_argument("--record-device", type=int, default=None, help="record_audio.py の入力デバイス番号")

    # スキップ系
    parser.add_argument("--skip-transcribe", action="store_true", help="transcribe.py をスキップ")
    parser.add_argument("--skip-plan", action="store_true", help="book_plan.py をスキップ")
    parser.add_argument("--skip-images", action="store_true", help="画像生成をスキップ")
    parser.add_argument("--skip-pdf", action="store_true", help="make_pdf.py をスキップ")
    parser.add_argument("--skip-publish", action="store_true", help="publish_book.py をスキップ")
    parser.add_argument("--skip-shelf", action="store_true", help="build_shelf.py / build_bookshelf.py をスキップ")

    # 画像生成関連（OpenAI/Comfy 共通）
    parser.add_argument("--force", action="store_true", help="既存画像があっても上書き生成")
    parser.add_argument("--start-page", type=int, default=None)
    parser.add_argument("--end-page", type=int, default=None)

    # Comfy向け追加オプション
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--cfg", type=float, default=None)
    parser.add_argument("--lora-model-strength", type=float, default=None)
    parser.add_argument("--lora-clip-strength", type=float, default=None)
    parser.add_argument("--no-refiner", action="store_true")
    parser.add_argument("--guidance", type=float, default=None)

    args = parser.parse_args()

    live_recording_path = Path("input/live_recording.wav")

    # 1) Record + Transcribe
    if args.skip_transcribe:
        print("\n=== Transcribe ===")
        print("⏭️  スキップ (--skip-transcribe) / 既存 work/transcript.txt を利用")
    else:
        # 1-1) 録音
        if args.record:
            record_cmd = pycmd("record_audio.py")
            if args.record_device is not None:
                record_cmd += ["--device", str(args.record_device)]

            run_step(record_cmd, "Record Audio")

            # --audio-input が未指定なら録音ファイルを使う
            if args.audio_input is None:
                args.audio_input = str(live_recording_path)

        # 1-2) 文字起こし
        transcribe_cmd = pycmd("transcribe.py")
        if args.audio_input:
            transcribe_cmd += ["--input", args.audio_input]

        run_step(transcribe_cmd, "Transcribe")

    # 2) Book Plan
    if args.skip_plan:
        print("\n=== Book Plan ===")
        print("⏭️  スキップ (--skip-plan)")
    else:
        run_step(pycmd("book_plan.py"), "Book Plan")

    # 3) Images
    if args.skip_images:
        print("\n=== Generate Images ===")
        print("⏭️  スキップ (--skip-images)")
    else:
        if args.engine == "openai":
            cmd = pycmd("generate_images.py")

            if args.force:
                cmd.append("--force")
            if args.start_page is not None:
                cmd += ["--start-page", str(args.start_page)]
            if args.end_page is not None:
                cmd += ["--end-page", str(args.end_page)]

            run_step(cmd, "Generate Images (OpenAI)")
        else:
            cmd = pycmd("generate_images_sd.py")

            if args.force:
                cmd.append("--force")
            if args.start_page is not None:
                cmd += ["--start-page", str(args.start_page)]
            if args.end_page is not None:
                cmd += ["--end-page", str(args.end_page)]

            if args.seed is not None:
                cmd += ["--seed", str(args.seed)]
            if args.width is not None:
                cmd += ["--width", str(args.width)]
            if args.height is not None:
                cmd += ["--height", str(args.height)]
            if args.steps is not None:
                cmd += ["--steps", str(args.steps)]
            if args.cfg is not None:
                cmd += ["--cfg", str(args.cfg)]
            if args.lora_model_strength is not None:
                cmd += ["--lora-model-strength", str(args.lora_model_strength)]
            if args.lora_clip_strength is not None:
                cmd += ["--lora-clip-strength", str(args.lora_clip_strength)]
            if args.no_refiner:
                cmd += ["--no-refiner"]
            if args.guidance is not None:
                cmd += ["--guidance", str(args.guidance)]

            run_step(cmd, "Generate Images (ComfyUI)")

    # 4) PDF
    if args.skip_pdf:
        print("\n=== Make PDF ===")
        print("⏭️  スキップ (--skip-pdf)")
    else:
        run_step(pycmd("make_pdf.py"), "Make PDF")

    # 5) Publish
    if args.skip_publish:
        print("\n=== Publish Book ===")
        print("⏭️  スキップ (--skip-publish)")
    else:
        run_step(pycmd("publish_book.py"), "Publish Book")

    # 6) Shelf
    if args.skip_shelf:
        print("\n=== Build Shelf ===")
        print("⏭️  スキップ (--skip-shelf)")
    else:
        shelf_script = "build_shelf.py"
        if not Path(shelf_script).exists() and Path("build_bookshelf.py").exists():
            shelf_script = "build_bookshelf.py"
        run_step(pycmd(shelf_script), "Build Shelf")

    print("\n✅ Pipeline completed.")


if __name__ == "__main__":
    main()