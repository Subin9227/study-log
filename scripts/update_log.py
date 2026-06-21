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

def target_date():
    now = datetime.datetime.now(KST)
    # 저녁(18시 이후) 실행 → 오늘 / 새벽 실행 → 어제(전날 마무리 백필)
    return now.date() if now.hour >= 18 else now.date() - datetime.timedelta(days=1)

def blog_posts(day):
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
        if d == day:
            out.append({"title": (item.findtext("title") or "").strip(),
                        "link": (item.findtext("link") or "").strip()})
    return out

def fetch_day(day):
    if not (SUPABASE_URL and SUPABASE_KEY):
        return None
    url = f"{SUPABASE_URL}/rest/v1/days?date=eq.{day}&select=data"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            rows = json.loads(r.read())
    except Exception as e:
        print("supabase fetch failed:", e); return None
    return rows[0].get("data") if rows else None

def bootcamp_hours(data):
    slots = (data or {}).get("slots") or {}
    count = sum(1 for s in slots.values() if (s or {}).get("categoryName") == BOOTCAMP_CATEGORY)
    return round(count * SLOT_MINUTES / 60, 1)

def task_lines(data):
    data = data or {}
    cat_name = {c.get("id"): c.get("name", "") for c in (data.get("categories") or [])}
    tasks = [t for t in (data.get("tasks") or [])
             if cat_name.get(t.get("categoryId")) == BOOTCAMP_CATEGORY]
    if not tasks:
        return []
    lines = ["## 할 일 (부트캠프)", ""]
    for t in tasks:
        box = "x" if t.get("done") else " "
        lines.append(f"- [{box}] {t.get('title', '')}")
    lines.append("")
    return lines

def main():
    day = target_date()
    posts = blog_posts(day)
    data = fetch_day(day)
    bc = bootcamp_hours(data)
    if not (posts or bc >= BOOTCAMP_MIN_HOURS):
        print(f"{day}: not studied (blog={len(posts)}, bootcamp={bc}h). Skip."); return
    lines = [f"# {day}", ""]
    if bc > 0:
        lines += [f"- 부트캠프 {bc}시간", ""]
    lines += task_lines(data)
    if posts:
        lines.append("## 블로그")
        lines += [f"- [{p['title']}]({p['link']})" for p in posts]
        lines.append("")
    path = os.path.join(f"{day:%Y}", f"{day:%m}", f"{day}.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {path} (blog={len(posts)}, bootcamp={bc}h).")

if __name__ == "__main__":
    main()
