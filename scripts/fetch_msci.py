#!/usr/bin/env python3
"""
MSCI ปรับเพิ่ม/ลดหุ้นไทย -> data/msci.json

- ปฏิทินรอบทบทวน: เอกสาร "MSCI Announces the Next Eight Index Review Dates" (ir_dates.pdf)
- รายชื่อหุ้นที่ปรับ: เอกสาร Public List ของแต่ละรอบ (Standard = ดัชนีหลัก, Small Cap = หุ้นขนาดเล็ก)
  เช่น https://www.msci.com/eqb/gimi/stdindex/MSCI_Nov26_STPublicList.pdf
- ถ้าดึงรายชื่ออัตโนมัติไม่ได้: หน้าเว็บจะแจ้งให้บอก Claude ช่วยดึงข้อมูล
  และ Claude ใส่ข้อมูลเองได้ที่ data/msci_manual.json (รูปแบบเดียวกับ "latest")

ต้องใช้ pypdf (ติดตั้งใน workflow)
"""
import calendar
import datetime
import io
import json
import os
import re
import urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "msci.json")
MANUAL = os.path.join(ROOT, "data", "msci_manual.json")
BKK = ZoneInfo("Asia/Bangkok")
CET = ZoneInfo("Europe/Paris")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
LOG = []

# สำรอง ถ้าอ่านปฏิทินจาก MSCI ไม่ได้ (ที่มา: MSCI 11 พ.ย. 2026)
SCHEDULE_FALLBACK = [
    ("November 2026", "2026-11-11", "2026-12-01"),
    ("February 2027", "2027-02-09", "2027-03-01"),
    ("May 2027", "2027-05-10", "2027-05-28"),
    ("August 2027", "2027-08-12", "2027-09-01"),
    ("November 2027", "2027-11-11", "2027-12-01"),
    ("February 2028", "2028-02-10", "2028-03-01"),
    ("May 2028", "2028-05-11", "2028-06-01"),
    ("August 2028", "2028-08-14", "2028-09-01"),
    ("November 2028", "2028-11-13", "2028-12-01"),
]
MONTHS = {m: i for i, m in enumerate(calendar.month_name) if m}


def now_bkk():
    return datetime.datetime.now(BKK)


def get_pdf_text(url):
    from pypdf import PdfReader
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read()
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages)


def prev_business_day(d):
    d -= datetime.timedelta(days=1)
    while d.weekday() >= 5:
        d -= datetime.timedelta(days=1)
    return d


def parse_date(s):
    m = re.match(r"(\w+)\s+(\d{1,2}),\s*(\d{4})", s.strip())
    return datetime.date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))


def review_item(name, ann, eff):
    """ann = วันประกาศ (เวลายุโรป ~23:00) / eff = วันที่ดัชนีใหม่มีผล -> ปรับพอร์ตจริงตอนปิดตลาดวันทำการก่อนหน้า"""
    ann_dt = datetime.datetime(ann.year, ann.month, ann.day, 23, 0, tzinfo=CET).astimezone(BKK)
    close = prev_business_day(eff)
    return {"review": name, "announce_cet": ann.isoformat(),
            "announce_thai": ann_dt.isoformat(timespec="minutes"),
            "effective": eff.isoformat(), "trade_close": close.isoformat()}


def load_schedule():
    items = {}
    for name, a, e in SCHEDULE_FALLBACK:
        items[name] = review_item(name, datetime.date.fromisoformat(a), datetime.date.fromisoformat(e))
    try:
        t = get_pdf_text("https://www.msci.com/eqb/pressreleases/archive/ir_dates.pdf")
        for name, a, e in re.findall(
                r"(\w+ \d{4}) Index Review\s+o?\s*Announcement date:\s*([A-Za-z]+ \d{1,2}, \d{4})\s+o?\s*"
                r"Effective date:\s*([A-Za-z]+ \d{1,2}, \d{4})", t):
            items[name] = review_item(name, parse_date(a), parse_date(e))
        LOG.append("ปฏิทิน MSCI: อ่านจาก ir_dates.pdf สำเร็จ")
    except Exception as e:  # noqa: BLE001
        LOG.append(f"ปฏิทิน MSCI: อ่านไม่ได้ ({e}) -> ใช้รายการสำรอง")
    return sorted(items.values(), key=lambda r: r["announce_cet"])


def thai_section(text):
    """ตัดส่วน 'MSCI THAILAND INDEX' แล้วแยกคอลัมน์ Additions / Deletions"""
    m = re.search(r"MSCI THAILAND INDEX\s*\n\s*Additions\s+Deletions\s*\n(.*?)(?=\nMSCI [A-Z ]+INDEX|\n\s*©|\Z)", text, re.S)
    if not m:
        return {"add": [], "delete": []}  # ไม่มีส่วนไทย = รอบนี้ไม่มีการเปลี่ยนแปลงหุ้นไทย
    add, dele = [], []
    for line in m.group(1).splitlines():
        if not line.strip() or "msci.com" in line or "MSCI Inc" in line:
            continue
        parts = re.split(r"\s{2,}", line.rstrip())
        if line.startswith((" ", "\t")) or (len(parts) == 2 and parts[0] == ""):
            right = parts[-1].strip()
            if right and right != "None":
                dele.append(right)
            continue
        left = parts[0].strip()
        if left and left != "None":
            add.append(left)
        if len(parts) > 1 and parts[1].strip() and parts[1].strip() != "None":
            dele.append(parts[1].strip())
    return {"add": add, "delete": dele}


def fetch_review_lists(review):
    mon, year = review["review"].split()
    code = f"{mon[:3]}{year[2:]}"
    out = {}
    for key, path in (("standard", f"stdindex/MSCI_{code}_STPublicList.pdf"),
                      ("smallcap", f"smallcap/MSCI_{code}_SCPublicList.pdf")):
        url = "https://www.msci.com/eqb/gimi/" + path
        text = get_pdf_text(url)
        if "MSCI GLOBAL" not in text:
            raise ValueError(f"เอกสาร {key} ไม่ใช่รูปแบบที่คาดไว้")
        sec = thai_section(text)
        sec["url"] = url
        eff = re.search(r"effective as of the close of business on ([A-Za-z]+ \d{1,2}, \d{4})", text)
        if eff:
            out["trade_close"] = parse_date(eff.group(1)).isoformat()
        out[key] = sec
        LOG.append(f"{review['review']} {key}: เพิ่ม {sec['add']} / ลด {sec['delete']}")
    return out


def main():
    try:
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    except Exception:  # noqa: BLE001
        old = {}
    sched = load_schedule()
    now = now_bkk()
    announced = [r for r in sched if datetime.datetime.fromisoformat(r["announce_thai"]) + datetime.timedelta(hours=2) <= now]
    upcoming = [r for r in sched if r not in announced]
    latest = dict(announced[-1]) if announced else None

    if latest:
        old_latest = old.get("latest") or {}
        if old_latest.get("review") == latest["review"] and old_latest.get("ok"):
            latest = old_latest  # รอบนี้ดึงสำเร็จไปแล้ว ไม่ต้องดึงซ้ำ
        else:
            try:
                latest.update(fetch_review_lists(latest))
                latest["ok"] = True
            except Exception as e:  # noqa: BLE001
                LOG.append(f"ดึงรายชื่อ {latest['review']} ไม่สำเร็จ: {e}")
                latest["ok"] = False
                latest["error"] = str(e)[:200]
                try:  # ข้อมูลที่ Claude ใส่ให้เอง
                    with open(MANUAL, encoding="utf-8") as f:
                        man = json.load(f)
                    if man.get("review") == latest["review"]:
                        latest.update(man, ok=True, manual=True)
                        LOG.append("ใช้ข้อมูลจาก msci_manual.json")
                except FileNotFoundError:
                    pass

    out = {"updated_at": now.isoformat(timespec="minutes"), "latest": latest,
           "next": upcoming[0] if upcoming else None, "schedule": upcoming[:4],
           "link": "https://www.msci.com/quarterly-index-review", "log": LOG}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\n".join(LOG))


if __name__ == "__main__":
    main()
