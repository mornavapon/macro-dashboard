"""BOI: ยอดขอรับส่งเสริมการลงทุนจากต่างชาติ (FDI ขั้นคำขอ) -> data/boi.json

แยกจากสคริปต์อื่นทั้งหมด: ถ้าพัง จะกระทบเฉพาะไฟล์ data/boi.json

ข้อจำกัด: หน้าเว็บ boi.go.th มีระบบกันบอท บอทเลยหาลิงก์ไฟล์รายงานใหม่เองไม่ได้
  -> ลิงก์ไฟล์ PDF ของแต่ละรอบเก็บไว้ใน data/boi_reports.json (Claude เพิ่มให้เมื่อ BOI ประกาศรอบใหม่)
  -> สคริปต์นี้ดาวน์โหลด PDF แล้วอ่านตัวเลขเองอัตโนมัติ
  -> และคอยดู Google News ว่า BOI ประกาศตัวเลขรอบใหม่แล้วหรือยัง ถ้าประกาศแล้วแต่ยังไม่มีลิงก์
     หน้าเว็บจะขึ้นเตือนให้มาบอก Claude (แบบเดียวกับ MSCI)
รายงานต้นทาง: https://www.boi.go.th/index.php?page=statistics_oversea_report_st (สถิติการลงทุนโดยตรงจากต่างประเทศ)
"""
import datetime
import email.utils
import io
import json
import os
import re
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

BKK = ZoneInfo("Asia/Bangkok")
ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "data", "boi.json")
REPORTS = os.path.join(ROOT, "data", "boi_reports.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
PAGE = "https://www.boi.go.th/index.php?page=statistics_oversea_report_st&language=th"
TH_MON = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]

# ยอดคำขอของต่างชาติทั้งปี (ล้านบาท / โครงการ) จากรายงาน BOI รายปี ไว้ทำกราฟเทียบปี
ANNUAL_HISTORY = {
    2022: {"value": 386210, "projects": 1009},     # FDI Q4 2023 report
    2023: {"value": 663239, "projects": 1394},     # FDI Q4 2023 report
    2024: {"value": 818978, "projects": 2000},     # FDI Q4 2025 report
    2025: {"value": 1359925, "projects": 2421},    # FDI Q4 2025 report
}
NEWS_PATTERNS = {3: r"ไตรมาส(แรก|ที่ ?1| ?1)|3 เดือน|Q1", 6: r"ครึ่งปี|6 เดือน|H1|ครึ่งแรก",
                 9: r"9 เดือน|เก้าเดือน", 12: r"ทั้งปี|12 เดือน|ตลอดปี"}


def now_bkk():
    return datetime.datetime.now(BKK)


def get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def num(s):
    return int(s.replace(",", ""))


def parse_report(text):
    t = re.sub(r"[ \t]+", " ", text)
    m = re.search(r"(\d{4})\s*\(\s*มกราคม\s*-\s*(\S+?)\s*\)", t)
    year_be, end_month_name = int(m.group(1)), m.group(2)
    months = {"มีนาคม": 3, "มิถุนายน": 6, "กันยายน": 9, "ธันวาคม": 12}
    end_m = months.get(end_month_name)
    if not end_m:
        raise ValueError(f"อ่านช่วงเวลาไม่ได้: {end_month_name}")
    fdi = re.search(r"\(FDI\)\s*([\d,]+)\s+([\d,]+)\s+([-+]?\d+)\s+([\d,]+)\s+([\d,]+)\s+([-+]?\d+)", t)
    tot = re.search(r"ทั้งสิ้น\s*\n?\s*([\d,]+)\s+([\d,]+)\s+([-+]?\d+)\s+([\d,]+)\s+([\d,]+)\s+([-+]?\d+)", t)
    if not fdi:
        raise ValueError("ไม่พบแถว FDI")
    out = {"period": f"{year_be - 543}-{end_m:02d}", "year": year_be - 543, "end_month": end_m,
           "fdi": {"projects": num(fdi.group(2)), "projects_prev": num(fdi.group(1)), "projects_chg": int(fdi.group(3)),
                   "value": num(fdi.group(5)), "value_prev": num(fdi.group(4)), "value_chg": int(fdi.group(6))}}
    if tot:
        out["total"] = {"projects": num(tot.group(2)), "value": num(tot.group(5)), "value_chg": int(tot.group(6))}
    # รายอุตสาหกรรม: ชื่อ (อาจขึ้นบรรทัดใหม่) ตามด้วย 6 ตัวเลข
    ind_part = t.split("จำแนกตามรายอุตสาหกรรม", 1)[-1].split("รวมทั้งสิ้น", 1)[0] if "รวมทั้งสิ้น" in t else ""
    if not ind_part:
        ind_part = t.split("อุตสาหกรรม", 2)[-1]
    inds = []
    for mm in re.finditer(r"([ก-๙A-Za-z][ก-๙A-Za-z \n]*?)\s+(\d[\d,]*)\s+(\d[\d,]*)\s+([-+]?\d+)\s+(\d[\d,]*)\s+(\d[\d,]*)\s+([-+]?\d+)", ind_part):
        name = re.sub(r"\s+", "", mm.group(1)).strip()
        if len(name) < 2 or "เปลี่ยน" in name:
            continue
        inds.append({"name": name, "projects": num(mm.group(3)), "value": num(mm.group(6)), "value_chg": int(mm.group(7))})
    inds.sort(key=lambda x: -x["value"])
    out["industries"] = inds[:6]
    # 10 ประเทศแรก
    cpart = t.split("10 อันดับแรก", 1)[-1]
    countries = []
    for mm in re.finditer(r"\n\s*(\d{1,2})\s+([ก-๙A-Za-z][ก-๙A-Za-z ]*?)\s+([\d,]+)\s+([\d,]+)\s*(?=\n)", cpart):
        if int(mm.group(1)) != len(countries) + 1:
            break
        countries.append({"name": mm.group(2).strip().replace("สาธารณรัฐประชาชนจีน", "จีน"),
                          "projects": num(mm.group(3)), "value": num(mm.group(4))})
    out["countries"] = countries[:6]
    nw = re.search(r"โครงการใหม่\s+([\d,]+)\s+(\d+)\s+([\d,]+)\s+(\d+)", t)
    if nw:
        out["new_projects"] = {"projects": num(nw.group(1)), "value_share": int(nw.group(4))}
    return out


def next_period(year, end_m):
    return (year + 1, 3) if end_m == 12 else (year, end_m + 3)


def check_news(after_year, after_m):
    """ดูข่าวว่า BOI ประกาศตัวเลขรอบถัดไปแล้วหรือยัง"""
    ny, nm = next_period(after_year, after_m)
    period_end = datetime.date(ny, nm, 28)
    q = "BOI ยอดขอรับส่งเสริมการลงทุน"
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q) + "&hl=th&gl=TH&ceid=TH:th"
    xml = get(url, timeout=30).decode("utf-8", "replace")
    for title, link, pub in re.findall(r"<item><title>(.*?)</title><link>(.*?)</link>.*?<pubDate>(.*?)</pubDate>", xml):
        try:
            d = email.utils.parsedate_to_datetime(pub).astimezone(BKK).date()
        except Exception:  # noqa: BLE001
            continue
        if d <= period_end or (d - period_end).days > 80:
            continue
        if re.search(r"BOI|บีโอไอ", title) and re.search(r"ขอ|ส่งเสริม|ลงทุน", title) and re.search(NEWS_PATTERNS[nm], title):
            return {"period": f"{ny}-{nm:02d}", "label": period_label(ny, nm), "title": re.sub(r"&\w+;", "", title)[:140],
                    "link": link, "date": d.isoformat()}
    return None


def period_label(y, m):
    return f"ม.ค.–{TH_MON[m]} {y + 543}" if m != 12 else f"ทั้งปี {y + 543}"


def build(old):
    with open(REPORTS, encoding="utf-8") as f:
        reports = json.load(f)["reports"]
    reports.sort(key=lambda r: r["period"])
    latest_ref = reports[-1]
    cache = (old or {}).get("latest") if (old or {}).get("latest", {}).get("pdf") == latest_ref["pdf"] else None
    try:
        from pypdf import PdfReader
        data = get(latest_ref["pdf"])
        text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages)
        latest = parse_report(text)
        latest["pdf"] = latest_ref["pdf"]
        if latest["period"] != latest_ref["period"]:
            raise ValueError(f"ช่วงเวลาในไฟล์ ({latest['period']}) ไม่ตรงกับที่ระบุ ({latest_ref['period']})")
    except Exception:
        if cache:          # ดาวน์โหลด/อ่านไม่ได้ แต่เคยอ่านไฟล์เดียวกันได้แล้ว -> ใช้ค่าเดิม
            latest = cache
        else:
            raise
    latest["label"] = period_label(latest["year"], latest["end_month"])
    annual = [{"year": y, "label": str(y + 543), **v, "full": True} for y, v in sorted(ANNUAL_HISTORY.items())]
    if latest["end_month"] == 12:
        annual = [a for a in annual if a["year"] != latest["year"]]
        annual.append({"year": latest["year"], "label": str(latest["year"] + 543), "value": latest["fdi"]["value"],
                       "projects": latest["fdi"]["projects"], "full": True})
    else:
        annual.append({"year": latest["year"], "label": f"{latest['year'] + 543} ({latest['end_month']} ด.)",
                       "value": latest["fdi"]["value"], "projects": latest["fdi"]["projects"], "full": False})
    try:
        pending = check_news(latest["year"], latest["end_month"])
        news_ok = True
    except Exception:  # noqa: BLE001
        pending, news_ok = (old or {}).get("pending"), False
    ny, nm = next_period(latest["year"], latest["end_month"])
    return {"ok": True, "latest": latest, "annual": annual, "pending": pending, "news_check_ok": news_ok,
            "next": {"period": f"{ny}-{nm:02d}", "label": period_label(ny, nm),
                     "expected": "ปลายเดือน" + TH_MON[nm % 12 + 1] + " – ต้นเดือน" + TH_MON[(nm + 1) % 12 + 1]},
            "freq": "รายไตรมาส (BOI แถลงหลังสิ้นไตรมาสประมาณ 3–5 สัปดาห์)",
            "source": "สำนักงานคณะกรรมการส่งเสริมการลงทุน (BOI)", "link": PAGE}


def main():
    old = {}
    try:
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    except Exception:  # noqa: BLE001
        pass
    try:
        data = build(old)
        log = f"OK {data['latest']['period']} FDI {data['latest']['fdi']['value']:,} · pending={bool(data['pending'])}"
    except Exception as e:  # noqa: BLE001
        msg = f"{type(e).__name__}: {e}"[:200]
        log = "FAIL " + msg
        data = dict(old, stale=True, error=msg) if old.get("ok") else {"ok": False, "error": msg}
    data["updated_at"] = now_bkk().isoformat(timespec="minutes")
    data["log"] = log
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("boi:", log)


if __name__ == "__main__":
    main()
