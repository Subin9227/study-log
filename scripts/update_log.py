import os, json, datetime, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

KST = datetime.timezone(datetime.timedelta(hours=9))
RSS_URL = "https://hwamgai.tistory.com/rss"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

BOOTCAMP_CATEGORY = "부트캠프"
SLOT_MINUTES = 10
BOOTCAMP_MIN_HOURS = 2.0   # ← 기준: 부트캠프 N시간 이상이면 '공부한 날'

def blog_posts_today(today):
    try:
        req = urllib.request.Request(RSS_URL, headers={"User-Agent": "study-log-bot"})
        with urllib.request.urlopen(req, timeout=30) as r:
            root = ET.fromstring(r.read())
    except Exception as e:
        print("blog fetch failed:", e); return []
    out = []
    for item in root.iter("item"):
        try:
            d = parsedate_to_datetime((item.findtext("pubDate") or "").strip()).astimezone(KST).date()
        except Exception:
            continue
        if d == today:
            out.append({"title": (item.findtext("title") or "").strip(),
                        "link": (item.findtext("link") or "").strip()})
    return out

def bootcamp_hours_today(today):
    if not (SUPABASE_URL and SUPABASE_KEY):
        return 0.0
    url = f"{SUPABASE_URL}/rest/v1/days?date=eq.{today}&select=data"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            rows = json.loads(r.read())
    except Exception as e:
        print("supabase fetch failed:", e); return 0.0
    if not rows:
        return 0.0
    slots = (rows[0].get("data") or {}).get("slots") or {}
    count = sum(1 for s in slots.values() if (s or {}).get("categoryName") == BOOTCAMP_CATEGORY)
    return round(count * SLOT_MINUTES / 60, 1)

def main():
    today = datetime.datetime.now(KST).date()
    posts = blog_posts_today(today)
    bc = bootcamp_hours_today(today)
    if not (posts or bc >= BOOTCAMP_MIN_HOURS):
        print(f"{today}: not studied (blog={len(posts)}, bootcamp={bc}h). Skip."); return
    path = os.path.join(f"{today:%Y}", f"{today:%m}", f"{today}.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [f"# {today}", ""]
    if bc > 0:
        lines += [f"- 부트캠프 {bc}시간", ""]
    if posts:
        lines.append("## 블로그")
        lines += [f"- [{p['title']}]({p['link']})" for p in posts]
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {path} (blog={len(posts)}, bootcamp={bc}h).")

if __name__ == "__main__":
    main()
