import json
import shutil
from datetime import datetime
from pathlib import Path
print("publish_book.py started")
SRC_PLAN = Path("work/book_plan.json")
SRC_PDF = Path("output/book.pdf")
SRC_PAGES_DIR = Path("output/pages")

DOCS_DIR = Path("docs")
BOOKS_DIR = DOCS_DIR / "books"

def timestamp_id():
    # 例: 20260216_142233
    return datetime.now().strftime("%Y%m%d_%H%M%S")

VIEWER_HTML_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{title}</title>
  <style>
    body{{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;margin:0;background:#f6f6f6}}
    header{{padding:16px 20px;background:#fff;border-bottom:1px solid #eee;display:flex;gap:12px;align-items:center;flex-wrap:wrap}}
    header h1{{font-size:16px;margin:0}}
    main{{max-width:1100px;margin:18px auto;padding:0 16px;display:grid;grid-template-columns:1fr 1fr;gap:16px}}
    .card{{background:#fff;border:1px solid #eee;border-radius:16px;padding:14px;box-shadow:0 1px 6px rgba(0,0,0,.04)}}
    img{{width:100%;height:auto;border-radius:12px;border:1px solid #eee;background:#fafafa}}
    .controls{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
    button{{padding:10px 12px;border:1px solid #ddd;border-radius:12px;background:#fff;cursor:pointer}}
    button:disabled{{opacity:.5;cursor:not-allowed}}
    .meta{{color:#666;font-size:13px}}
    .text{{font-size:18px;line-height:1.75;white-space:pre-wrap}}
    a{{color:#0b57d0;text-decoration:none}}
    @media (max-width:900px){{main{{grid-template-columns:1fr}}}}
  </style>
</head>
<body>
  <header>
    <h1 id="title">{title}</h1>
    <div class="controls">
      <button id="prev">← Prev</button>
      <div class="meta"><span id="pageInfo">-/-</span></div>
      <button id="next">Next →</button>
      <a id="pdfLink" href="book.pdf" target="_blank" rel="noreferrer">PDFを開く</a>
      <a href="../../index.html">本棚へ戻る</a>
    </div>
  </header>

  <main>
    <section class="card">
      <img id="pageImg" alt="page image" />
      <div class="meta" id="scene"></div>
    </section>
    <section class="card">
      <div class="text" id="pageText"></div>
    </section>
  </main>

  <script>
    const state = {{ plan: null, idx: 0 }};

    const el = {{
      title: document.getElementById('title'),
      prev: document.getElementById('prev'),
      next: document.getElementById('next'),
      pageInfo: document.getElementById('pageInfo'),
      pageImg: document.getElementById('pageImg'),
      pageText: document.getElementById('pageText'),
      scene: document.getElementById('scene'),
    }};

    function pad2(n){{ return String(n).padStart(2,'0'); }}

    function render(){{
      const pages = state.plan.pages;
      const p = pages[state.idx];
      const total = pages.length;

      el.title.textContent = state.plan.title || '{title}';
      el.pageInfo.textContent = `${{p.page}}/${{total}}`;

      el.pageImg.src = `pages/${{pad2(p.page)}}.png`;
      el.pageText.textContent = p.text || '';
      el.scene.textContent = p.scene_summary ? `Scene: ${{p.scene_summary}}` : '';

      el.prev.disabled = state.idx === 0;
      el.next.disabled = state.idx === total - 1;
    }}

    async function init(){{
      const res = await fetch('book_plan.json', {{ cache: 'no-store' }});
      if(!res.ok) throw new Error('book_plan.json が読めません');
      state.plan = await res.json();
      state.idx = 0;

      window.addEventListener('keydown', (e) => {{
        if(e.key === 'ArrowLeft' && state.idx > 0){{ state.idx--; render(); }}
        if(e.key === 'ArrowRight' && state.idx < state.plan.pages.length - 1){{ state.idx++; render(); }}
      }});

      el.prev.addEventListener('click', () => {{ state.idx--; render(); }});
      el.next.addEventListener('click', () => {{ state.idx++; render(); }});

      render();
    }}

    init().catch(err => {{
      document.body.innerHTML = `<pre style="padding:20px">Error: ${{err.message}}</pre>`;
    }});
  </script>
</body>
</html>
"""

def main():
    # 入力チェック
    if not SRC_PLAN.exists():
        raise FileNotFoundError("work/book_plan.json が見つかりません")
    if not SRC_PDF.exists():
        raise FileNotFoundError("output/book.pdf が見つかりません")
    if not SRC_PAGES_DIR.exists():
        raise FileNotFoundError("output/pages が見つかりません")

    plan = json.loads(SRC_PLAN.read_text(encoding="utf-8"))
    title = plan.get("title", "StoryBook").strip() or "StoryBook"

    book_id = timestamp_id()
    dst_dir = BOOKS_DIR / book_id
    dst_pages = dst_dir / "pages"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst_pages.mkdir(parents=True, exist_ok=True)

    # コピー
    shutil.copy2(SRC_PLAN, dst_dir / "book_plan.json")
    shutil.copy2(SRC_PDF, dst_dir / "book.pdf")

    for img in sorted(SRC_PAGES_DIR.glob("*.png")):
        shutil.copy2(img, dst_pages / img.name)

    # viewer.html 生成（この本フォルダ内で相対参照する）
    (dst_dir / "viewer.html").write_text(
        VIEWER_HTML_TEMPLATE.format(title=title),
        encoding="utf-8"
    )

    print("✅ Published book:")
    print("   id:", book_id)
    print("   path:", dst_dir.as_posix())

if __name__ == "__main__":
    main()
