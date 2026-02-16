import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def run(cmd: list[str]) -> None:
    """Run a command and fail fast with nice logs."""
    print("\n🟦 RUN:", " ".join(cmd))
    p = subprocess.run(cmd, text=True)
    if p.returncode != 0:
        raise SystemExit(f"❌ Command failed (exit={p.returncode}): {' '.join(cmd)}")


def ensure_git_clean_enough() -> None:
    # なくても動くけど、事故防止で確認したい場合に使える
    pass


def main():
    parser = argparse.ArgumentParser(description="End-to-end StoryBook pipeline")
    parser.add_argument("--force-images", action="store_true", help="Overwrite existing page PNGs")
    parser.add_argument("--no-push", action="store_true", help="Do not git push (commit only)")
    parser.add_argument("--message", type=str, default="", help="Commit message override")
    args = parser.parse_args()

    # Safety: ensure scripts exist
    required = [
        "book_plan.py",
        "generate_images.py",
        "make_pdf.py",
        "publish_book.py",
        "build_shelf.py",
    ]
    missing = [f for f in required if not Path(f).exists()]
    if missing:
        raise SystemExit(f"❌ Missing files: {missing}")

    # 1) plan
    run([sys.executable, "book_plan.py"])

    # 2) images
    img_cmd = [sys.executable, "generate_images.py"]
    if args.force_images:
        img_cmd.append("--force")
    run(img_cmd)

    # 3) pdf
    run([sys.executable, "make_pdf.py"])

    # 4) publish (create docs/books/<id>/...)
    run([sys.executable, "publish_book.py"])

    # 5) rebuild shelf (docs/index.html)
    run([sys.executable, "build_shelf.py"])

    # 6) git add/commit/push
    # add only docs outputs (safer than git add -A)
    run(["git", "add", "docs/index.html", "docs/books"])

    # If nothing changed, git commit returns non-zero. Handle gently.
    msg = args.message.strip()
    if not msg:
        msg = "Add new book " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("\n🟦 RUN: git commit -m ...")
    p = subprocess.run(["git", "commit", "-m", msg], text=True)
    if p.returncode != 0:
        print("ℹ️ No changes to commit (or commit failed). Continuing...")

    if not args.no_push:
        run(["git", "push"])

    print("\n✅ Pipeline complete!")


if __name__ == "__main__":
    main()
