#!/usr/bin/env python3
"""
หน้า 2 (อเมริกา): GDP / ตารางประชุมเฟด / CPI -> data/us.json

แยกจากตัวดึงข้อมูลหน้า 1 (fetch_indices.py) และแต่ละหัวข้อในไฟล์นี้ก็ดึงแยกกัน
ถ้าหัวข้อไหนพัง หัวข้ออื่นยังทำงานได้ และถ้าเคยดึงได้ จะเก็บข้อมูลเก่าไว้พร้อมติดป้าย stale

แหล่งข้อมูลหลัก: FRED (ธนาคารกลางสหรัฐฯ สาขาเซนต์หลุยส์) แบบ CSV ไม่ต้องใช้ API key
- GDP                    : ขนาด GDP (พันล้านดอลลาร์, ปรับเป็นรายปี)
- A191RL1Q225SBEA        : Real GDP growth % QoQ (ปรับเป็นรายปี) = ตัวเลขที่สื่อรายงาน
- CPIAUCNS               : ดัชนี CPI (ไม่ปรับฤดูกาล) ใช้คำนวณ % YoY แบบที่ BLS ประกาศ
- DFEDTARU / DFEDTARL    : กรอบบน/ล่างของดอกเบี้ยนโยบายเฟด (รายวัน)
ตารางประชุมเฟด: federalreserve.gov (สำรองด้วยรายการวันที่ที่ใส่ไว้ในไฟล์นี้)
"""
import calendar
import csv
import datetime
import io
import json
import os
import re
import urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "us.json")
DEBUG_DIR = os.path.join(ROOT, "data", "debug")
BKK = ZoneInfo("Asia/Bangkok")
NY = ZoneInfo("America/New_York")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
LOG = []

# สำรอง: วันประชุม FOMC (วันแรก, วันสุดท้าย) ใช้เมื่อดึงจากเว็บเฟดไม่ได้
FOMC_FALLBACK = {
    2026: [("2026-01-27", "2026-01-28"), ("2026-03-17", "2026-03-18"),
           ("2026-04-28", "2026-04-29"), ("2026-06-16", "2026-06-17"),
           ("2026-07-28", "2026-07-29"), ("2026-09-15", "2026-09-16"),
           ("2026-10-27", "2026-10-28"), ("2026-12-08", "2026-12-09")],
}


# ---------------------------------------------------------------- helpers
def now_bkk():
    return datetime.datetime.now(BKK)


def get(url, headers=None, timeout=30):
    h = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}
    if headers:
        h.update(headers)
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        raw = r.read()
        cs = r.headers.get_content_charset() or "utf-8"
    return raw.decode(cs, errors="replace")


def save_debug(name, url, text):
    os.makedirs(DEBUG_DIR, exist_ok=True)
    with open(os.path.join(DEBUG_DIR, f"us_{name}.txt"), "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\nFETCHED: {now_bkk().isoformat()}\n\n{text[:8000]}")


def err_text(e):
    return f"{type(e).__name__}: {e}"[:220]


def strip_tags(html):
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text)


def fred(series_id, start=None):
    """คืน list ของ (date, float) จาก FRED CSV (ข้ามค่าที่ว่าง)"""
    # หมายเหตุ: ส่ง User-Agent แบบเบราว์เซอร์หรือพารามิเตอร์ cosd แล้ว FRED ค้าง จึงขอแบบเรียบๆ
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    text = get(url, headers={"User-Agent": "curl/8.5.0", "Accept": "*/*"}, timeout=60)
    rows = list(csv.reader(io.StringIO(text)))
    out = []
    for r in rows[1:]:
        if len(r) < 2:
            continue
        try:
            out.append((datetime.date.fromisoformat(r[0]), float(r[1])))
        except ValueError:
            continue  # ค่า "." = ยังไม่มีข้อมูล
    if start:
        start_d = datetime.date.fromisoformat(start)
        out = [(d, v) for d, v in out if d >= start_d]
    if not out:
        save_debug(f"fred_{series_id}", url, text)
        raise ValueError(f"FRED {series_id} ไม่มีข้อมูล")
    LOG.append(f"FRED {series_id} OK ({len(out)} แถว, ล่าสุด {out[-1][0]})")
    return out


def quarter_label(d):
    return f"Q{(d.month - 1) // 3 + 1} {d.year}"


# ---------------------------------------------------------------- GDP
def build_gdp():
    size = dict(fred("GDP", "2020-01-01"))
    growth = fred("A191RL1Q225SBEA", "2020-01-01")
    rows = []
    for d, g in growth[-4:]:
        rows.append({
            "quarter": quarter_label(d),
            "date": d.isoformat(),
            "growth": round(g, 1),
            "size_bn": round(size[d], 1) if d in size else None,
        })
    rows.reverse()  # ล่าสุดอยู่บน
    return {"rows": rows, "source": "BEA ผ่าน FRED",
            "link": "https://www.investing.com/economic-calendar/gdp-375"}


# ---------------------------------------------------------------- CPI
def build_cpi():
    idx = fred("CPIAUCNS", "2019-01-01")
    by_month = {(d.year, d.month): v for d, v in idx}
    rows = []
    for d, v in idx[-6:]:
        prev = by_month.get((d.year - 1, d.month))
        if prev:
            rows.append({"month": d.strftime("%Y-%m"), "yoy": round((v / prev - 1) * 100, 1)})
        else:
            # เช่น ต.ค. 2025 ไม่มีข้อมูล (รัฐบาลสหรัฐฯ shutdown) จึงคำนวณ YoY ของ ต.ค. 2026 ไม่ได้
            rows.append({"month": d.strftime("%Y-%m"), "yoy": None,
                         "note": f"ไม่มีดัชนี CPI ของเดือนเดียวกันปี {d.year - 1} ให้เทียบ"})
    rows.reverse()
    return {"rows": rows, "source": "BLS ผ่าน FRED",
            "link": "https://th.investing.com/economic-calendar/cpi-733"}


# ---------------------------------------------------------------- FOMC
MONTHS = {m: i for i, m in enumerate(calendar.month_name) if m}


def fomc_dates_from_fed(year):
    url = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    html = get(url, headers={"Accept": "text/html"})
    text = strip_tags(html)
    save_debug("fomc_calendar", url, text)
    m = re.search(rf"{year} FOMC Meetings(.*?)(?:\d{{4}} FOMC Meetings|$)", text)
    if not m:
        raise ValueError(f"ไม่พบหัวข้อ {year} FOMC Meetings")
    sec = m.group(1)
    names = "|".join(MONTHS)
    pat = rf"\b({names})(?:/({names}))?\s+(\d{{1,2}})-(\d{{1,2}})\*?"
    out = []
    for m1, m2, d1, d2 in re.findall(pat, sec):
        start = datetime.date(year, MONTHS[m1], int(d1))
        end_month = MONTHS[m2] if m2 else MONTHS[m1]
        end = datetime.date(year, end_month, int(d2))
        out.append((start, end))
    # ปีหนึ่งมี 8 ครั้ง ถ้าได้น้อยกว่านี้ถือว่าอ่านผิด
    if len(out) < 8:
        raise ValueError(f"อ่านวันประชุมได้แค่ {len(out)} ครั้ง")
    return out[:8]


def rate_on(series, day):
    """ค่าล่าสุดที่ไม่เกินวันที่กำหนด"""
    val = None
    for d, v in series:
        if d > day:
            break
        val = v
    return val


def build_fed():
    today = now_bkk().date()
    year = today.year
    try:
        meetings = fomc_dates_from_fed(year)
        src = "federalreserve.gov"
    except Exception as e:  # noqa: BLE001
        LOG.append(f"FOMC calendar FAIL {err_text(e)} -> ใช้รายการสำรอง")
        if year not in FOMC_FALLBACK:
            raise
        meetings = [(datetime.date.fromisoformat(a), datetime.date.fromisoformat(b))
                    for a, b in FOMC_FALLBACK[year]]
        src = "รายการวันที่สำรองในโปรแกรม"
    LOG.append(f"FOMC meetings {year}: {len(meetings)} ครั้ง ({src})")

    upper = fred("DFEDTARU", f"{year - 1}-12-01")
    lower = fred("DFEDTARL", f"{year - 1}-12-01")
    last_data_day = upper[-1][0]

    rows = []
    next_marked = False
    for start, end in meetings:
        # เฟดแถลงผล 14:00 ตามเวลานิวยอร์ก -> แปลงเป็นเวลาไทย
        ann = datetime.datetime(end.year, end.month, end.day, 14, 0, tzinfo=NY).astimezone(BKK)
        prev_u = rate_on(upper, start - datetime.timedelta(days=1))
        prev_l = rate_on(lower, start - datetime.timedelta(days=1))
        done = ann <= now_bkk()
        row = {
            "start": start.isoformat(), "end": end.isoformat(),
            "thai_date": ann.date().isoformat(), "thai_time": ann.strftime("%H:%M"),
            "previous": prev_u, "previous_range": [prev_l, prev_u],
            "actual": None, "actual_range": None, "status": "done" if done else "upcoming",
        }
        effective = end + datetime.timedelta(days=1)  # ดอกเบี้ยใหม่มีผลวันถัดไป
        if done and last_data_day >= effective:
            row["actual"] = rate_on(upper, effective)
            row["actual_range"] = [rate_on(lower, effective), row["actual"]]
        elif done:
            row["status"] = "waiting"  # ประชุมแล้ว แต่ FRED ยังไม่อัปเดต
        if not done and not next_marked:
            row["next"] = True
            next_marked = True
        if not done and prev_u is None:
            row["previous"] = upper[-1][1]
            row["previous_range"] = [lower[-1][1], upper[-1][1]]
        rows.append(row)

    # ประชุมที่ยังไม่ถึง: "ก่อนหน้า" = ดอกเบี้ยปัจจุบัน
    for r in rows:
        if r["status"] == "upcoming":
            r["previous"] = upper[-1][1]
            r["previous_range"] = [lower[-1][1], upper[-1][1]]

    return {"year": year, "meetings": rows, "calendar_source": src,
            "current_range": [lower[-1][1], upper[-1][1]], "rate_asof": last_data_day.isoformat(),
            "source": "Federal Reserve ผ่าน FRED",
            "link": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"}


# ---------------------------------------------------------------- ตารางวันประกาศ (ใช้ทำแจ้งเตือน)
BROWSER = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
           "Accept-Language": "en-US,en;q=0.9"}

# CPI: เว็บ BLS บล็อกบอท (403) จึงใส่ตารางทางการไว้ในโปรแกรม
# ที่มา: https://www.bls.gov/schedule/news_release/cpi.htm (เวลา 08:30 ตามเวลานิวยอร์ก)
# ** ต้องเติมตารางปี 2028 เมื่อ BLS ประกาศ (ประมาณกลางปี 2027) **
CPI_SCHEDULE = [
    ("2026-10", "2026-11-10"), ("2026-11", "2026-12-10"), ("2026-12", "2027-01-13"),
    ("2027-01", "2027-02-11"), ("2027-02", "2027-03-10"), ("2027-03", "2027-04-13"),
    ("2027-04", "2027-05-12"), ("2027-05", "2027-06-10"), ("2027-06", "2027-07-14"),
    ("2027-07", "2027-08-11"), ("2027-08", "2027-09-14"), ("2027-09", "2027-10-14"),
    ("2027-10", "2027-11-10"), ("2027-11", "2027-12-10"),
]

GDP_KIND = {"Advance": "ประมาณการครั้งแรก", "Second": "ประมาณการครั้งที่ 2",
            "Third": "ประมาณการครั้งที่ 3"}


def release_item(day, hh, mm, title, ref):
    et = datetime.datetime(day.year, day.month, day.day, hh, mm, tzinfo=NY)
    th = et.astimezone(BKK)
    return {"et": et.isoformat(), "thai": th.isoformat(timespec="minutes"),
            "thai_date": th.date().isoformat(), "thai_time": th.strftime("%H:%M"),
            "title": title, "ref": ref}


def gdp_releases():
    url = "https://www.bea.gov/news/schedule"
    text = strip_tags(get(url, headers=BROWSER))
    save_debug("bea_schedule", url, text)
    names = "|".join(MONTHS)
    pat = (rf"\b({names}) (\d{{1,2}}) (\d{{1,2}}):(\d{{2}}) ([AP]M) N\s?ews (.*?)"
           rf"(?= (?:{names}) \d{{1,2}} \d{{1,2}}:\d{{2}} [AP]M N\s?ews|$)")
    today = now_bkk().date()
    out = []
    for mon, d, hh, mm, ap, title in re.findall(pat, text):
        title = title.strip()[:160]
        if not title.startswith("GDP ("):
            continue  # ข้าม GDP by County / by State ฯลฯ
        day = datetime.date(today.year, MONTHS[mon], int(d))
        if day < today - datetime.timedelta(days=60):
            day = datetime.date(today.year + 1, MONTHS[mon], int(d))
        h = int(hh) % 12 + (12 if ap == "PM" else 0)
        kind = re.search(r"\((Advance|Second|Third) Estimate\)", title)
        q = re.search(r"(\d)(?:st|nd|rd|th) Quarter(?: and Year)? (\d{4})", title)
        ref = f"Q{q.group(1)} {q.group(2)}" if q else ""
        th_title = " ".join(x for x in ["GDP สหรัฐฯ", ref,
                                         f"({GDP_KIND[kind.group(1)]})" if kind else ""] if x)
        out.append(release_item(day, h, int(mm), th_title, ref))
    if not out:
        raise ValueError("ไม่พบกำหนดการประกาศ GDP ในหน้า BEA")
    out.sort(key=lambda r: r["et"])
    LOG.append(f"BEA GDP releases: {[r['thai_date'] for r in out]}")
    return out


def cpi_releases():
    out = []
    for ref, day in CPI_SCHEDULE:
        d = datetime.date.fromisoformat(day)
        y, m = ref.split("-")
        out.append(release_item(d, 8, 30, f"CPI สหรัฐฯ เดือน {calendar.month_abbr[int(m)]} {y}", ref))
    return out


def build_releases():
    today = now_bkk().date().isoformat()
    res = {}
    for key, fn in (("gdp", gdp_releases), ("cpi", cpi_releases)):
        try:
            items = [r for r in fn() if r["thai_date"] >= today]
            res[key] = {"ok": True, "items": items[:6]}
        except Exception as e:  # noqa: BLE001
            LOG.append(f"releases.{key}: FAIL {err_text(e)}")
            res[key] = {"ok": False, "error": err_text(e), "items": []}
    return res


# ---------------------------------------------------------------- runner
def run_section(name, fn, old):
    try:
        data = fn()
        data["ok"] = True
        data["fetched_at"] = now_bkk().isoformat(timespec="minutes")
        LOG.append(f"{name}: OK")
        return data
    except Exception as e:  # noqa: BLE001
        msg = err_text(e)
        LOG.append(f"{name}: FAIL {msg}")
        if old and old.get("ok"):
            kept = dict(old)
            kept["stale"] = True
            kept["error"] = msg
            return kept
        return {"ok": False, "error": msg}


def main():
    try:
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    except Exception:  # noqa: BLE001
        old = {}

    out = {
        "updated_at": now_bkk().isoformat(timespec="minutes"),
        "gdp": run_section("gdp", build_gdp, old.get("gdp")),
        "fed": run_section("fed", build_fed, old.get("fed")),
        "cpi": run_section("cpi", build_cpi, old.get("cpi")),
        "releases": build_releases(),
    }
    # ถ้าดึงตารางวันประกาศไม่ได้ ใช้ของเดิมไปก่อน (แจ้งเตือนจะได้ไม่หาย)
    for k, v in out["releases"].items():
        old_v = (old.get("releases") or {}).get(k)
        if not v["ok"] and old_v and old_v.get("items"):
            today = now_bkk().date().isoformat()
            v["items"] = [r for r in old_v["items"] if r["thai_date"] >= today]
            v["stale"] = True
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    os.makedirs(DEBUG_DIR, exist_ok=True)
    with open(os.path.join(DEBUG_DIR, "_summary_us.txt"), "w", encoding="utf-8") as f:
        f.write(f"run at {now_bkk().isoformat()}\n\n" + "\n".join(LOG) + "\n")
    print("\n".join(LOG))


if __name__ == "__main__":
    main()
