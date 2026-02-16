import json
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

PLAN_PATH = Path("work/book_plan.json")
PAGES_DIR = Path("output/pages")
OUT_PDF = Path("output/book.pdf")

# 横向き（生成画像1024x1536の回転版に合わせると扱いやすい）
PAGE_W, PAGE_H = 1536, 1024

MARGIN = 64
GAP = 32  # 左右カラムの間

# 左右 50:50
CONTENT_W = PAGE_W - 2 * MARGIN
COL_W = (CONTENT_W - GAP) / 2

# テキスト設定
FONT_NAME = "HeiseiKakuGo-W5"
FONT_SIZE = 34
LEADING = 46
INNER_MARGIN = 44  # 右テキスト枠の内側余白
TEXT_BOX_RADIUS = 24

def wrap_text_by_width(text: str, font_name: str, font_size: int, max_width: float):
    """
    実際の描画幅（stringWidth）で折り返し。
    日本語はスペースが少ないので1文字ずつ詰めていく方式。
    """
    text = (text or "").strip()
    if not text:
        return []

    lines = []
    current = ""
    for ch in text:
        # 改行が入ってたら強制改行
        if ch == "\n":
            if current:
                lines.append(current)
                current = ""
            continue

        trial = current + ch
        w = pdfmetrics.stringWidth(trial, font_name, font_size)
        if w <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
                current = ch
            else:
                # 1文字すら入らない場合は無理やり入れる
                lines.append(ch)
                current = ""
    if current:
        lines.append(current)
    return lines

def main():
    pdfmetrics.registerFont(UnicodeCIDFont(FONT_NAME))

    if not PLAN_PATH.exists():
        raise FileNotFoundError(f"{PLAN_PATH} が見つかりません。")
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    pages = plan.get("pages", [])
    if not pages:
        raise RuntimeError("book_plan.json に pages がありません。")

    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(OUT_PDF), pagesize=(PAGE_W, PAGE_H))
    c.setTitle(plan.get("title", "storybook"))

    # カラム座標
    left_x0 = MARGIN
    right_x0 = MARGIN + COL_W + GAP
    y0 = MARGIN
    h = PAGE_H - 2 * MARGIN

    for p in pages:
        page_num = int(p["page"])
        img_path = PAGES_DIR / f"{page_num:02d}.png"
        if not img_path.exists():
            raise FileNotFoundError(f"画像がありません: {img_path}")

        # --- 右：テキスト枠（白背景） ---
        c.setFillGray(1.0)
        c.roundRect(right_x0, y0, COL_W, h, radius=TEXT_BOX_RADIUS, stroke=0, fill=1)

        # --- 左：画像（枠内フィット） ---
        img = ImageReader(str(img_path))
        c.drawImage(
            img,
            left_x0,
            y0,
            width=COL_W,
            height=h,
            preserveAspectRatio=True,
            anchor="c",
        )

        # --- 右：テキスト ---
        c.setFillGray(0.0)
        c.setFont(FONT_NAME, FONT_SIZE)

        text = (p.get("text") or "").strip()

        text_area_x = right_x0 + INNER_MARGIN
        text_area_y_top = y0 + h - INNER_MARGIN - FONT_SIZE
        text_area_w = COL_W - 2 * INNER_MARGIN
        text_area_h = h - 2 * INNER_MARGIN

        lines = wrap_text_by_width(text, FONT_NAME, FONT_SIZE, text_area_w)

        max_lines = int(text_area_h / LEADING)
        lines = lines[:max_lines]

        center_x = right_x0 + (COL_W / 2)

        num_lines = len(lines)
        max_lines = int(text_area_h / LEADING)
        lines = lines[:max_lines]
        num_lines = len(lines)

        block_h = (num_lines - 1) * LEADING
        start_y = y0 + (h / 2) + (block_h / 2)  # 右枠の中央を基準に上端を決める

        for i, line in enumerate(lines):
            y = start_y - i * LEADING
            c.drawCentredString(center_x, y, line)


        # --- ページ番号 ---
        c.setFont(FONT_NAME, 18)
        c.setFillGray(0.35)
        c.drawRightString(right_x0 + COL_W - INNER_MARGIN, y0 + 20, f"{page_num}/{len(pages)}")

        c.showPage()

    c.save()
    print("✅ PDF saved:", OUT_PDF)

if __name__ == "__main__":
    main()
