import argparse
import json
import os
import shutil
import time
import uuid
from pathlib import Path

import requests

PLAN_PATH = Path("work/book_plan.json")
OUT_DIR = Path("output/pages")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# あなたが保存したAPI形式JSON
WORKFLOW_API_JSON = Path("work/sdxl_pictures_api.json")  # ←必要ならパス変更

COMFY_BASE = os.getenv("COMFY_BASE_URL", "http://127.0.0.1:8188")

# --- このJSONに合わせたノードID（今回のアップロード内容ベース） ---
NODE_SIZE = "5"
NODE_POS_BASE = "6"
NODE_NEG_BASE = "7"
NODE_KSAMPLER_BASE = "10"

NODE_KSAMPLER_REFINER = "11"
NODE_REFINER_POS = "15"
NODE_REFINER_NEG = "16"

NODE_SAVE = "19"
NODE_LORA = "50"

# 使う/使わないを切り替え（最初はTrueのまま）
USE_REFINER = True


def comfy_post_prompt(prompt_workflow: dict, client_id: str) -> str:
    url = f"{COMFY_BASE}/prompt"
    payload = {
        "prompt": prompt_workflow,
        "client_id": client_id,
    }
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["prompt_id"]


def comfy_get_history(prompt_id: str) -> dict:
    url = f"{COMFY_BASE}/history/{prompt_id}"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.json()


def comfy_view_image(filename: str, subfolder: str, folder_type: str = "output") -> bytes:
    url = f"{COMFY_BASE}/view"
    params = {
        "filename": filename,
        "subfolder": subfolder,
        "type": folder_type,
    }
    r = requests.get(url, params=params, timeout=120)
    r.raise_for_status()
    return r.content


def wait_for_completion_and_get_images(prompt_id: str, poll_sec: float = 1.0, timeout_sec: int = 300):
    """
    /history/{prompt_id} に出るまで待機して、生成画像メタを返す。
    返り値: [{"filename":..., "subfolder":..., "type":...}, ...]
    """
    start = time.time()
    while True:
        if time.time() - start > timeout_sec:
            raise TimeoutError(f"ComfyUI generation timed out: {prompt_id}")

        hist = comfy_get_history(prompt_id)

        # 形式は {"<prompt_id>": {...}} で返る
        if prompt_id in hist:
            entry = hist[prompt_id]
            outputs = entry.get("outputs", {})

            images = []
            for node_id, out in outputs.items():
                for img in out.get("images", []):
                    images.append(img)

            if images:
                return images

            # outputsはあるがimagesがない場合も少し待つ
        time.sleep(poll_sec)


def build_prompts_for_page(page: dict, style_bible: str, characters: list[str]) -> tuple[str, str]:
    """
    pageのimage_prompt_sd / negative_prompt_sd をベースに、共通スタイル文を足す。
    """
    base_pos = (page.get("image_prompt_sd") or "").strip()
    base_neg = (page.get("negative_prompt_sd") or "").strip()

    if not base_pos:
        raise RuntimeError(f'page {page.get("page")} に image_prompt_sd がありません。')

    char_text = ", ".join([c for c in characters if c])
    style_text = (style_bible or "").strip()

    # 共通の一貫性補助（英語寄りにしておく）
    consistency = "consistent character design, same outfit, same hairstyle, children's picture book illustration, soft watercolor, pastel colors"

    pos_parts = [style_text, consistency, char_text, base_pos]
    positive = ", ".join([p for p in pos_parts if p]).strip(", ")

    # negative は既存 + 追加の無難なもの
    extra_neg = "text, watermark, logo, blurry, low quality, extra fingers, malformed hands"
    negative = ", ".join([p for p in [base_neg, extra_neg] if p]).strip(", ")

    return positive, negative


def extract_character_descriptions(plan: dict) -> list[str]:
    chars = []
    for c in plan.get("characters", []):
        name = (c.get("name") or "").strip()
        desc = (c.get("description") or "").strip()
        if desc and name:
            chars.append(f"{name}: {desc}")
        elif desc:
            chars.append(desc)
    return chars


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="既存ページ画像を上書き生成")
    parser.add_argument("--start-page", type=int, default=None)
    parser.add_argument("--end-page", type=int, default=None)
    parser.add_argument("--seed", type=int, default=12345, help="base seed（page番号を足して使う）")
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--steps", type=int, default=25)
    parser.add_argument("--cfg", type=float, default=7.0)
    parser.add_argument("--lora-model-strength", type=float, default=None, help="LoRA strength_model を上書き")
    parser.add_argument("--lora-clip-strength", type=float, default=None, help="LoRA strength_clip を上書き")
    args = parser.parse_args()

    if not PLAN_PATH.exists():
        raise FileNotFoundError(f"{PLAN_PATH} が見つかりません。")
    if not WORKFLOW_API_JSON.exists():
        raise FileNotFoundError(f"{WORKFLOW_API_JSON} が見つかりません。")

    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    pages = plan.get("pages", [])
    if not pages:
        raise RuntimeError("book_plan.json に pages がありません。")

    workflow_template = json.loads(WORKFLOW_API_JSON.read_text(encoding="utf-8"))

    title = plan.get("title", "storybook")
    style_bible = plan.get("style_bible", "")
    characters = extract_character_descriptions(plan)

    print(f"📘 SD/ComfyUI generating images for: {title}")
    print(f"pages: {len(pages)} | comfy: {COMFY_BASE} | workflow: {WORKFLOW_API_JSON}")
    print(f"refiner: {USE_REFINER}\n")

    client_id = str(uuid.uuid4())

    for p in pages:
        page_num = int(p["page"])

        if args.start_page is not None and page_num < args.start_page:
            continue
        if args.end_page is not None and page_num > args.end_page:
            continue

        out_path = OUT_DIR / f"{page_num:02d}.png"
        if out_path.exists() and not args.force:
            print(f"skip page {page_num:02d} (already exists)")
            continue

        # テンプレから毎回コピーして安全に書き換える
        wf = json.loads(json.dumps(workflow_template))

        positive, negative = build_prompts_for_page(p, style_bible, characters)

        # サイズ
        wf[NODE_SIZE]["inputs"]["width"] = args.width
        wf[NODE_SIZE]["inputs"]["height"] = args.height

        # prompt（BASE）
        wf[NODE_POS_BASE]["inputs"]["text"] = positive
        wf[NODE_NEG_BASE]["inputs"]["text"] = negative

        # prompt（REFINER）
        if USE_REFINER:
            wf[NODE_REFINER_POS]["inputs"]["text"] = positive
            wf[NODE_REFINER_NEG]["inputs"]["text"] = negative

        # seed / steps / cfg
        page_seed = args.seed + page_num
        wf[NODE_KSAMPLER_BASE]["inputs"]["noise_seed"] = page_seed
        wf[NODE_KSAMPLER_BASE]["inputs"]["steps"] = args.steps
        wf[NODE_KSAMPLER_BASE]["inputs"]["cfg"] = args.cfg

        if USE_REFINER:
            # refiner側は add_noise=disable なのでseedは影響薄いが、管理上合わせる
            wf[NODE_KSAMPLER_REFINER]["inputs"]["noise_seed"] = page_seed
            wf[NODE_KSAMPLER_REFINER]["inputs"]["steps"] = args.steps
            wf[NODE_KSAMPLER_REFINER]["inputs"]["cfg"] = args.cfg

        # LoRA強度をCLIで上書き可能に
        if args.lora_model_strength is not None:
            wf[NODE_LORA]["inputs"]["strength_model"] = args.lora_model_strength
        if args.lora_clip_strength is not None:
            wf[NODE_LORA]["inputs"]["strength_clip"] = args.lora_clip_strength

        # Save prefix をページごとに（履歴の見分け用）
        wf[NODE_SAVE]["inputs"]["filename_prefix"] = f"StoryBook/page_{page_num:02d}"

        print(f"→ generating page {page_num:02d} (seed={page_seed})")

        prompt_id = comfy_post_prompt(wf, client_id=client_id)
        images = wait_for_completion_and_get_images(prompt_id, poll_sec=1.0, timeout_sec=600)

        # 最後の画像を採用（通常1枚）
        img_meta = images[-1]
        img_bytes = comfy_view_image(
            filename=img_meta["filename"],
            subfolder=img_meta.get("subfolder", ""),
            folder_type=img_meta.get("type", "output"),
        )

        out_path.write_bytes(img_bytes)
        print(f"   saved: {out_path}")

    print("\n✅ Done! Images saved to output/pages/")


if __name__ == "__main__":
    main()