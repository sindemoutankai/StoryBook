import argparse
import json
import os
import time
import uuid
from pathlib import Path

import requests

PLAN_PATH = Path("work/book_plan.json")
OUT_DIR = Path("output/pages")
OUT_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = Path("config_flux.json")


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"{CONFIG_PATH} が見つかりません。")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def deep_copy_json(d: dict) -> dict:
    return json.loads(json.dumps(d))


def comfy_post_prompt(comfy_base: str, prompt_workflow: dict, client_id: str) -> str:
    url = f"{comfy_base}/prompt"
    payload = {"prompt": prompt_workflow, "client_id": client_id}
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["prompt_id"]


def comfy_get_history(comfy_base: str, prompt_id: str) -> dict:
    url = f"{comfy_base}/history/{prompt_id}"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.json()


def comfy_view_image(comfy_base: str, filename: str, subfolder: str, folder_type: str = "output") -> bytes:
    url = f"{comfy_base}/view"
    params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    r = requests.get(url, params=params, timeout=120)
    r.raise_for_status()
    return r.content


def wait_for_completion_and_get_images(comfy_base: str, prompt_id: str, poll_sec: float, timeout_sec: int):
    start = time.time()
    while True:
        if time.time() - start > timeout_sec:
            raise TimeoutError(f"ComfyUI generation timed out: {prompt_id}")

        hist = comfy_get_history(comfy_base, prompt_id)
        if prompt_id in hist:
            entry = hist[prompt_id]
            outputs = entry.get("outputs", {})
            images = []
            for _, out in outputs.items():
                for img in out.get("images", []):
                    images.append(img)
            if images:
                return images

        time.sleep(poll_sec)


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


def build_flux_prompt_for_page(page: dict, plan: dict, config: dict) -> str:
    """
    FLUX用: positive promptのみ組み立てる（negativeなし）
    """
    policy = config.get("prompt_policy", {})

    base_pos = (page.get("image_prompt_sd") or "").strip()
    if not base_pos:
        # 万一 image_prompt_sd が無い時の保険
        base_pos = (page.get("image_prompt_api") or "").strip()
    if not base_pos:
        raise RuntimeError(f'page {page.get("page")} に画像プロンプトがありません。')

    parts = []

    if policy.get("append_style_bible", True):
        style_bible = (plan.get("style_bible") or "").strip()
        if style_bible:
            parts.append(style_bible)

    if policy.get("append_character_consistency", True):
        chars = extract_character_descriptions(plan)
        if chars:
            parts.append(", ".join(chars))

    extra_positive = (policy.get("extra_positive") or "").strip()
    if extra_positive:
        parts.append(extra_positive)

    parts.append(base_pos)

    return ", ".join([p for p in parts if p]).strip(", ")


def generate_flux_images(
    force: bool = False,
    start_page: int | None = None,
    end_page: int | None = None,
    seed: int | None = None,
    width: int | None = None,
    height: int | None = None,
    steps: int | None = None,
    guidance: float | None = None,
    lora_model_strength: float | None = None,
):
    config = load_config()
    comfy_base = os.getenv("COMFY_BASE_URL", config.get("comfy_base_url", "http://127.0.0.1:8188"))
    workflow_api_json = Path(config["workflow_api_json"])
    node = config["nodes"]
    defaults = config.get("defaults", {})

    eff_seed = defaults.get("seed", 12345) if seed is None else seed
    eff_width = defaults.get("width", 1024) if width is None else width
    eff_height = defaults.get("height", 1024) if height is None else height
    eff_steps = defaults.get("steps", 35) if steps is None else steps
    eff_guidance = defaults.get("guidance", 3.5) if guidance is None else guidance
    eff_lora_model_strength = defaults.get("lora_model_strength", None) if lora_model_strength is None else lora_model_strength
    timeout_sec = int(defaults.get("timeout_sec", 600))
    poll_sec = float(defaults.get("poll_sec", 1.0))

    if not PLAN_PATH.exists():
        raise FileNotFoundError(f"{PLAN_PATH} が見つかりません。")
    if not workflow_api_json.exists():
        raise FileNotFoundError(f"{workflow_api_json} が見つかりません。")

    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    pages = plan.get("pages", [])
    if not pages:
        raise RuntimeError("book_plan.json に pages がありません。")

    workflow_template = json.loads(workflow_api_json.read_text(encoding="utf-8"))

    title = plan.get("title", "storybook")
    print(f"📘 FLUX/ComfyUI generating images for: {title}")
    print(f"pages: {len(pages)} | comfy: {comfy_base}")
    print(f"workflow: {workflow_api_json}")
    print(f"size: {eff_width}x{eff_height} | steps: {eff_steps} | guidance: {eff_guidance}\n")

    client_id = str(uuid.uuid4())

    for p in pages:
        page_num = int(p["page"])

        if start_page is not None and page_num < start_page:
            continue
        if end_page is not None and page_num > end_page:
            continue

        out_path = OUT_DIR / f"{page_num:02d}.png"
        if out_path.exists() and not force:
            print(f"skip page {page_num:02d} (already exists)")
            continue

        wf = deep_copy_json(workflow_template)
        positive = build_flux_prompt_for_page(p, plan, config)

        # prompt
        wf[node["prompt"]]["inputs"]["text"] = positive

        # size (CR SDXL Aspect Ratio ノードの width/height を想定)
        wf[node["size"]]["inputs"]["width"] = eff_width
        wf[node["size"]]["inputs"]["height"] = eff_height

        # seed
        page_seed = eff_seed
        wf[node["noise"]]["inputs"]["noise_seed"] = page_seed

        # steps
        wf[node["scheduler"]]["inputs"]["steps"] = eff_steps

        # guidance (FluxGuidance)
        wf[node["guidance"]]["inputs"]["guidance"] = eff_guidance

        # LoRA (model-only)
        if "lora" in node and node["lora"] in wf and eff_lora_model_strength is not None:
            wf[node["lora"]]["inputs"]["strength_model"] = eff_lora_model_strength

        # Save prefix
        wf[node["save"]]["inputs"]["filename_prefix"] = f"StoryBookFLUX/page_{page_num:02d}"

        print(f"→ generating page {page_num:02d} (seed={page_seed})")
        prompt_id = comfy_post_prompt(comfy_base, wf, client_id)
        images = wait_for_completion_and_get_images(comfy_base, prompt_id, poll_sec=poll_sec, timeout_sec=timeout_sec)

        # 通常1枚。最後の画像を採用。
        img_meta = images[-1]
        img_bytes = comfy_view_image(
            comfy_base,
            filename=img_meta["filename"],
            subfolder=img_meta.get("subfolder", ""),
            folder_type=img_meta.get("type", "output"),
        )

        out_path.write_bytes(img_bytes)
        print(f"   saved: {out_path}")

    print("\n✅ Done! Images saved to output/pages/")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--start-page", type=int, default=None)
    parser.add_argument("--end-page", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--guidance", type=float, default=None)
    parser.add_argument("--lora-model-strength", type=float, default=None)
    args = parser.parse_args()

    generate_flux_images(
        force=args.force,
        start_page=args.start_page,
        end_page=args.end_page,
        seed=args.seed,
        width=args.width,
        height=args.height,
        steps=args.steps,
        guidance=args.guidance,
        lora_model_strength=args.lora_model_strength,
    )


if __name__ == "__main__":
    main()