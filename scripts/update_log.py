import os, datetime, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

RSS_URL = "https://hwamgai.tistory.com/rss"
KST = datetime.timezone(datetime.timedelta(hours=9))

def fetch_posts():
    req = urllib.request.Request(RSS_URL, headers={"User-Agent": "study-log-bot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ET.fromstring(r.read())
    posts = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        try:
            d = parsedate_to_datetime(pub).astimezone(KST).date()
        except Exception:
            continue
        posts.append({"title": title, "link": link, "date": d})
    return posts

def main():
    today = datetime.datetime.now(KST).date()
    todays = [p for p in fetch_posts() if p["date"] == today]
    if not todays:
        print(f"No blog post for {today}. Skip.")
        return
    path = os.path.join(f"{today:%Y}", f"{today:%m}", f"{today}.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [f"# {today}", "", "## 오늘 공부 (블로그)", ""]
    lines += [f"- [{p['title']}]({p['link']})" for p in todays]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {path} ({len(todays)} post).")

if __name__ == "__main__":
    main()
