import os, json, datetime, urllib.request
import calendar as _cal
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

KST = datetime.timezone(datetime.timedelta(hours=9))
RSS_URL = "https://hwamgai.tistory.com/rss"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

BOOTCAMP_CATEGORY = "부트캠프"
SLOT_MINUTES = 10
BOOTCAMP_MIN_HOURS = 2.0   # ← 기준: 부트캠프 N시간 이상이면 '공부한 날'

HERE = os.path.dirname(os.path.abspath(__file__))
CALENDAR_JSON = os.path.join(HERE, "calendar.json")   # 달력 단일 출처(일자별 전체/부트캠프)
README_PATH = os.path.join(os.path.dirname(HERE), "README.md")
CAL_START = "<!-- CAL:START -->"
CAL_END = "<!-- CAL:END -->"

DETAIL_FROM = "2026-06-25"     # 이 날짜부터 날짜칸에 시간 표시, 그 전은 숫자만(주간 합계엔 포함)
BACKFILL_START = "2026-05-12"  # 백필 기본 시작일(부트캠프 개강)

def target_date():
    mode = os.environ.get("DATE_MODE", "auto")
    now = datetime.datetime.now(KST)
    if mode == "today":
        return now.date()
    if mode == "yesterday":
        return now.date() - datetime.timedelta(days=1)
    if mode == "manual":
        return datetime.date.fromisoformat(os.environ.get("TARGET_DATE", ""))
    # auto: 저녁(18시 이후) → 오늘 / 새벽·낮 → 어제(전날 백필)
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

def fetch_range(start, end):
    # start~end(포함) 모든 날 한 번에 조회. 백필용.
    if not (SUPABASE_URL and SUPABASE_KEY):
        return []
    url = f"{SUPABASE_URL}/rest/v1/days?date=gte.{start}&date=lte.{end}&select=date,data"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except Exception as e:
        print("supabase range fetch failed:", e); return []

def bootcamp_hours(data):
    slots = (data or {}).get("slots") or {}
    count = sum(1 for s in slots.values() if (s or {}).get("categoryName") == BOOTCAMP_CATEGORY)
    return round(count * SLOT_MINUTES / 60, 1)

def total_minutes(data):
    # 카테고리가 찍힌 모든 슬롯 = 하루 전체 공부시간(분). 달력의 큰 숫자(예 10:53)용.
    slots = (data or {}).get("slots") or {}
    count = sum(1 for s in slots.values() if (s or {}).get("categoryName"))
    return count * SLOT_MINUTES

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

# ───────────────────────── 달력 ─────────────────────────
def load_calendar():
    try:
        with open(CALENDAR_JSON, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}

def save_calendar(cal):
    with open(CALENDAR_JSON, "w", encoding="utf-8") as f:
        json.dump(cal, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

def _hhmm(total_min):
    return f"{total_min // 60:02d}:{total_min % 60:02d}"

def _emoji(total_min):
    h = total_min / 60
    if h >= 8: return "🟫"
    if h >= 5: return "🟥"
    if h >= 2: return "🟧"
    if h > 0:  return "🟨"
    return ""

def _week_total(week, entries, month):
    # 한 주(월~일) 행의 합 — 이번 달 날짜만, 컷오프와 무관하게 전부 합산
    days = [d.isoformat() for d in week if d.month == month and d.isoformat() in entries]
    tm = sum(entries[ds]["total_min"] for ds in days)
    bc = sum(entries[ds].get("bootcamp_h") or 0 for ds in days)
    return tm, round(bc, 1)

def render_calendar(cal):
    # cal: { "YYYY-MM-DD": {"total_min": int, "bootcamp_h": float} }
    if not cal:
        return "_아직 기록이 없습니다._"
    months = {}
    for ds, v in cal.items():
        months.setdefault(ds[:7], {})[ds] = v
    latest = max(months)   # 최신 달만 펼침(open)
    out = []
    for ym in sorted(months):   # 오름차순: 과거 → 최신 (위 → 아래로 이어서)
        year, month = int(ym[:4]), int(ym[5:7])
        entries = months[ym]
        total_sum = sum(v["total_min"] for v in entries.values())
        open_attr = " open" if ym == latest else ""
        out.append(f"<details{open_attr}>")
        out.append(f"<summary>📅 {ym} · {total_sum // 60}시간 {total_sum % 60}분 · 공부 {len(entries)}일</summary>")
        out.append("")   # <details> 안에서 마크다운 표가 렌더되려면 빈 줄 필요
        out.append("| 월 | 화 | 수 | 목 | 금 | 토 | 일 | 주간 합계 |")
        out.append("|---|---|---|---|---|---|---|---|")
        for week in _cal.Calendar(firstweekday=0).monthdatescalendar(year, month):
            cells = []
            for d in week:
                if d.month != month:
                    cells.append(" ")
                    continue
                ds = d.isoformat()
                if ds in entries and ds >= DETAIL_FROM:   # 컷오프 이후만 날짜칸에 시간 표시
                    tm = entries[ds]["total_min"]
                    bc = entries[ds].get("bootcamp_h") or 0
                    if tm > 0:
                        cell = f"**{d.day}**<br>{_emoji(tm)} {_hhmm(tm)}"
                        if bc:
                            cell += f"<br><sub>부트 {bc}h</sub>"
                    else:
                        cell = f"**{d.day}**<br>✍️"   # 측정시간 0(블로그 등)
                    cells.append(cell)
                else:
                    cells.append(str(d.day))   # 컷오프 이전 or 데이터 없음 → 숫자만
            wt, wbc = _week_total(week, entries, month)
            if wt > 0:
                wcell = f"**{_hhmm(wt)}**"
                if wbc:
                    wcell += f"<br><sub>부트 {wbc}h</sub>"
            else:
                wcell = "·"
            cells.append(wcell)
            out.append("| " + " | ".join(cells) + " |")
        out.append("")
        out.append("</details>")
        out.append("")
    return "\n".join(out).rstrip()

def update_readme(cal):
    block = f"{CAL_START}\n{render_calendar(cal)}\n{CAL_END}"
    try:
        with open(README_PATH, encoding="utf-8") as f:
            txt = f.read()
    except FileNotFoundError:
        txt = "# Study Log\n"
    if CAL_START in txt and CAL_END in txt:
        head, rest = txt.split(CAL_START, 1)
        _, tail = rest.split(CAL_END, 1)
        txt = head + block + tail
    else:   # 마커 없으면 달력 섹션을 새로 붙임
        txt = txt.rstrip() + "\n\n## 📊 공부 달력\n" + block + "\n"
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(txt)

def backfill():
    # 5/12(기본)~오늘 범위를 한 번에 읽어 calendar.json·README에 합계만 채움.
    # logs/ md나 과거 잔디는 안 건드림(표시 백필) — 수동 dispatch에서 1회 실행용.
    start = os.environ.get("BACKFILL_START") or BACKFILL_START
    end = datetime.datetime.now(KST).date().isoformat()
    rows = fetch_range(start, end)
    cal = load_calendar()
    n = 0
    for row in rows:
        day = row.get("date")
        data = row.get("data")
        tm = total_minutes(data)
        bc = bootcamp_hours(data)
        if day and (tm > 0 or bc > 0):
            cal[day] = {"total_min": tm, "bootcamp_h": bc}
            n += 1
    save_calendar(cal)
    update_readme(cal)
    print(f"Backfilled {n} days ({start} ~ {end}).")

def main():
    if os.environ.get("DATE_MODE") == "backfill":
        backfill(); return
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
    path = os.path.join("logs", f"{day:%Y}", f"{day:%m}", f"{day}.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    # 달력 갱신: 그날 칸에 전체시간 + 부트캠프 시간 기록 후 README 주입
    tm = total_minutes(data)
    cal = load_calendar()
    cal[str(day)] = {"total_min": tm, "bootcamp_h": bc}
    save_calendar(cal)
    update_readme(cal)
    print(f"Wrote {path} (blog={len(posts)}, bootcamp={bc}h, total={_hhmm(tm)}).")

if __name__ == "__main__":
    main()
