#!/usr/bin/env python3
"""
add_doc.py — Thêm văn bản mới vào vn-tax-corpus (schema chuẩn, không bị lỗi p3)
Usage: python3 scripts/add_doc.py <url_congbao> <folder_path> [--dry-run]

Ví dụ:
  python3 scripts/add_doc.py \
    https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-xxx.htm \
    'I.THUE/001._VBPQ_THUE/001.LUAT_QLT'
"""
import sys, re, json, requests, html
from pathlib import Path

REPO = Path(__file__).parent.parent
DOCS = REPO / "docs"
INDEX = REPO / "index.json"

TX_MAP = {
    "001.LUAT QLT":       "QLT",
    "003.THUE GTGT":      "GTGT",
    "004.THUE TNDN":      "TNDN",
    "005.THUE TTDB":      "TTDB",
    "006.THUE TNCN":      "TNCN",
    "007.THUE BVMT":      "BVMT",
    "008.THUE NHA THAU":  "FCT",
    "012. GIAO DICH LK":  "GDLK",
    "018. HO KINH DOANH": "HKD",
}

def normalize_p(raw):
    return raw.replace("_", " ").replace("  ", " ").strip()

def fetch_doc(url):
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 Chrome/120", "Accept-Language": "vi-VN,vi;q=0.9"})
    r = s.get(url, timeout=20)
    r.raise_for_status()
    h = r.text
    og = re.search(r'property="og:title"[^>]*content="([^"]+)"', h)
    title = html.unescape(og.group(1)).strip() if og else ""
    dates = re.findall(r"(\d{2}/\d{2}/20\d{2})", h)
    date = dates[0] if dates else ""
    ym = re.search(r"/(20\d{2})/", url)
    year = ym.group(1) if ym else ""
    return title, date, year, h

def add_doc(url, folder_path, dry_run=False):
    folder_rel = folder_path.strip("/").replace("docs/", "")
    parts = folder_rel.split("/")
    s   = parts[0]
    p2  = normalize_p(parts[1]) if len(parts) > 1 else ""
    p3  = normalize_p(parts[2]) if len(parts) > 2 else ""
    tx  = TX_MAP.get(p3, "")

    print(f"Fetching: {url}")
    title, date, year, raw_html = fetch_doc(url)
    print(f"  Title: {title[:80]}")
    print(f"  Date: {date} | p2: {p2} | p3: {p3} | tx: {tx}")

    m = re.search(r"/van-ban/([^/]+?)(?:-\d+)?\.htm", url)
    slug = m.group(1) if m else re.sub(r"[^a-z0-9-]", "", title.lower().replace(" ", "-"))[:60]
    filename = slug + ".html"
    target_dir = DOCS / folder_rel
    doc_p = str((target_dir / filename).relative_to(DOCS))

    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    if any(slug in d.get("p", "") for d in idx):
        print(f"  WARNING: slug already in index — skipping")
        return False

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)
        clean = (
            '<!DOCTYPE html>\n<html lang="vi"><head>\n'
            '<meta charset="UTF-8">\n'
            f'<title>{html.escape(title)}</title>\n'
            f'<meta name="date" content="{date}">\n'
            f'<meta name="source" content="{url}">\n'
            '</head><body>\n'
            f'<p style="background:#f5f5f5;padding:8px 12px">Nguon: <a href="{url}">{url}</a> - Ngay: {date}</p>\n'
            f'{raw_html}\n</body></html>'
        )
        (target_dir / filename).write_text(clean, encoding="utf-8")
        entry = {
            "n": title, "fn": filename, "p": doc_p,
            "y": year,
            "t": "Nghi dinh" if "nd-" in slug else ("Thong tu" if "tt-" in slug else "Van ban"),
            "tx": tx, "tl": p3.split(".")[-1].strip(),
            "hl": 1, "s": s, "p2": p2, "p3": p3,
        }
        idx.append(entry)
        INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Added to index.json (total: {len(idx)})")
    else:
        print(f"  [DRY RUN] docs/{doc_p} | p2={p2} | p3={p3}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    add_doc(sys.argv[1], sys.argv[2], "--dry-run" in sys.argv)
