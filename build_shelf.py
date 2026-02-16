import json
from pathlib import Path
from datetime import datetime

DOCS_DIR = Path("docs")
BOOKS_DIR = DOCS_DIR / "books"
OUT_INDEX = DOCS_DIR / "index.html"

def parse_dt(book_id: str):
    # book_id: YYYYMMDD_HHMMSS
    try:
        return datetime.strptime(book_id, "%Y%m%d_%H%M%S")
    except Exception:
        return None

def main():
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)

    books = []
    for book_dir in BOOKS_DIR.iterdir():
        if not book_dir.is_dir():
            continue
        plan_path = book_dir / "book_plan.json"
        cover_path = book_dir / "pages" / "01.png"
        viewer_path = book_dir / "viewer.html"
        pdf_path = book_dir / "book.pdf"

        if not plan_path.exists() or not viewer_path.exists():
            continue

        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        title = plan.get("title", book_dir.name)

        dt = parse_dt(book_dir.name)
        label = dt.strftime("%Y-%m-%d %H:%M:%S") if dt else book_dir.name

        books.append({
            "id": book_dir.name,
            "title": title,
            "label": label,
            "viewer": f"books/{book_dir.name}/viewer.html",
            "pdf": f"books/{book_dir.name}/book.pdf",
            "cover": f"books/{book_dir.name}/pages/01.png" if cover_path.exists() else "",
        })

    # 新しい順
    def sort_key(b):
        dt = parse_dt(b["id"])
        return dt or datetime.min
    books.sort(key=sort_key, reverse=True)

    cards = []
    for b in books:
        cover_html = f'<img src="{b["cover"]}" alt="cover" />' if b["cover"] else '<div class="noimg">No cover</div>'
        cards.append(f"""
        <article class="card">
          <a class="cover" href="{b["viewer"]}">
            {cover_html}
          </a>
          <div class="meta">
            <div class="title">{b["title"]}</div>
            <div class="sub">{b["label"]}</div>
          </div>
          <div class="actions">
            <a class="btn" href="{b["viewer"]}">Webで読む</a>
            <a class="btn" href="{b["pdf"]}" target="_blank" rel="noreferrer">PDF</a>
          </div>
        </article>
        """.strip())

    html = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>StoryBook Shelf</title>
  <style>
    body{{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;margin:0;background:#f6f6f6}}
    header{{padding:18px 20px;background:#fff;border-bottom:1px solid #eee}}
    h1{{font-size:18px;margin:0}}
    .wrap{{max-width:1200px;margin:18px auto;padding:0 16px}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}}
    .card{{background:#fff;border:1px solid #eee;border-radius:16px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.04);display:flex;flex-direction:column}}
    .cover img{{width:100%;height:auto;display:block;background:#fafafa}}
    .noimg{{height:280px;display:flex;align-items:center;justify-content:center;color:#999;background:#fafafa}}
    .meta{{padding:12px 12px 0}}
    .title{{font-weight:700}}
    .sub{{color:#666;font-size:12px;margin-top:4px}}
    .actions{{display:flex;gap:8px;padding:12px}}
    .btn{{display:inline-block;padding:10px 12px;border:1px solid #ddd;border-radius:12px;background:#fff;text-decoration:none;color:#0b57d0;text-align:center;flex:1}}
    .hint{{color:#666;font-size:13px;margin:10px 0 0}}
  </style>
</head>
<body>
  <header>
    <h1>📚 StoryBook Shelf</h1>
    <div class="hint">新しい本ほど上に表示されます。</div>
  </header>

  <div class="wrap">
    <div class="grid">
      {"".join(cards) if cards else "<p>まだ本がありません。publish_book.py を実行してください。</p>"}
    </div>
  </div>
</body>
</html>
"""
    OUT_INDEX.write_text(html, encoding="utf-8")
    print("✅ Shelf generated:", OUT_INDEX)

if __name__ == "__main__":
    main()
