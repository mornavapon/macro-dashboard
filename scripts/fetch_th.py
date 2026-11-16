#!/usr/bin/env python3
"""
หน้า 3 (ไทย): ตารางประชุม กนง. / เงินเฟ้อไทย / GDP ไทย -> data/th.json

แยกจากหน้า 1 และหน้า 2 และแต่ละหัวข้อดึงแยกกัน ถ้าหัวข้อไหนพัง หัวข้ออื่นยังทำงานได้

แหล่งข้อมูล
- ตารางประชุม กนง.     : bot.or.th หน้า "การประชุม กนง." (สำรองด้วยรายการวันที่ในไฟล์นี้)
- ดอกเบี้ยนโยบาย/มติ     : ไฟล์ Excel ตารางมติ กนง. ของ ธปท. (ลิงก์อยู่ในหน้า "อัตราดอกเบี้ยนโยบาย")
- เงินเฟ้อทั่วไป (CPI)  : index.tpso.go.th (สนค. กระทรวงพาณิชย์)
- GDP ไทย              : ยังไม่มีแหล่งที่ดึงอัตโนมัติได้ (เว็บ สศช. ดึงข้อมูลออกยาก)
"""
import datetime
import html
import http.cookiejar
import io
import json
import os
import re
import urllib.request
import zipfile
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "th.json")
DEBUG_DIR = os.path.join(ROOT, "data", "debug")
BKK = ZoneInfo("Asia/Bangkok")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
LOG = []
_op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

TH_MON = {"ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4, "พ.ค.": 5, "มิ.ย.": 6,
          "ก.ค.": 7, "ส.ค.": 8, "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12}

# สำรอง: วันแถลงผลประชุม กนง. (ใช้เมื่ออ่านจากเว็บ ธปท. ไม่ได้)
MPC_FALLBACK = {
    2026: ["2026-02-25", "2026-04-29", "2026-06-24", "2026-08-26", "2026-10-28", "2026-12-23"],
}
MPC_TIME = (14, 0)  # ธปท. แถลงผลประชุม กนง. เวลา 14:00 น.


# ---------------------------------------------------------------- helpers
def now_bkk():
    return datetime.datetime.now(BKK)


def get(url, headers=None, data=None, binary=False, timeout=45):
    h = {"User-Agent": UA, "Accept": "text/html,application/json,*/*;q=0.8",
         "Accept-Language": "th,en;q=0.9"}
    if headers:
        h.update(headers)
    with _op.open(urllib.request.Request(url, headers=h, data=data), timeout=timeout) as r:
        raw = r.read()
    return raw if binary else raw.decode("utf-8", errors="replace")


def save_debug(name, url, text):
    os.makedirs(DEBUG_DIR, exist_ok=True)
    with open(os.path.join(DEBUG_DIR, f"th_{name}.txt"), "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\nFETCHED: {now_bkk().isoformat()}\n\n{text[:8000]}")


def err_text(e):
    return f"{type(e).__name__}: {e}"[:220]


def clean_text(raw):
    # หน้าเว็บ ธปท. ฝังตารางไว้แบบ escape ซ้อน 2 ชั้น
    t = html.unescape(html.unescape(raw)).replace("\\r\\n", " ").replace('\\"', '"')
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t)


def excel_date(serial):
    return datetime.date(1899, 12, 30) + datetime.timedelta(days=int(float(serial)))


# ---------------------------------------------------------------- กนง.
def mpc_schedule(year):
    url = "https://www.bot.or.th/th/our-roles/monetary-policy/mpc-meeting.html"
    text = clean_text(get(url))
    be = year + 543
    m = re.search(rf"กำหนดการ {be}(.*?)ปฏิทิน silent period", text)
    if not m:
        save_debug("mpc_page", url, text)
        raise ValueError(f"ไม่พบตารางกำหนดการ {be}")
    months = "|".join(re.escape(k) for k in TH_MON)
    dates = []
    for no, d, mon, y in re.findall(rf"\b([1-8]) พุธที่ (\d{{1,2}}) ({months}) (25\d\d)", m.group(1)):
        if len(dates) < int(no):  # เอาวันแรกของแต่ละครั้ง (วันถัดไปคือวันเผยแพร่รายงาน)
            dates.append(datetime.date(int(y) - 543, TH_MON[mon], int(d)))
    if len(dates) < 4:
        raise ValueError(f"อ่านวันประชุมได้แค่ {len(dates)} ครั้ง")
    return dates


def mpc_decisions():
    """คืน list ของ dict: date, rate, decision (จากไฟล์ Excel ของ ธปท.)"""
    page_url = "https://www.bot.or.th/th/our-roles/monetary-policy/mpc-publication/policy-interest-rate.html"
    page = get(page_url)
    m = re.search(r'(/content/dam/[^"]*table-mpc-[^"]*\.xlsx)', page)
    if not m:
        raise ValueError("ไม่พบลิงก์ไฟล์ Excel ตารางมติ กนง.")
    z = zipfile.ZipFile(io.BytesIO(get("https://www.bot.or.th" + m.group(1), binary=True)))
    ss = [re.sub(r"<[^>]+>", "", x) for x in
          re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode("utf-8"), re.S)]
    sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
    out = []
    for row in re.findall(r"<row [^>]*>(.*?)</row>", sheet, re.S):
        cells = {}
        for col, attrs, v in re.findall(
                r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(?:<f>.*?</f>)?(?:<v>([^<]*)</v>)?</c>)', row):
            if v:
                cells[col] = ss[int(v)] if 't="s"' in attrs else v
        try:
            out.append({"date": excel_date(cells["B"]), "rate": float(cells["H"]),
                        "decision": cells.get("F", "").replace("\r\n", " ").strip(),
                        "no": cells.get("A", "")})
        except (KeyError, ValueError):
            continue  # แถวหัวตาราง / หมายเหตุ
    if not out:
        raise ValueError("อ่านไฟล์ Excel ไม่ได้")
    LOG.append(f"BOT xlsx: {len(out)} มติ ล่าสุด {out[-1]['date']} = {out[-1]['rate']}%")
    return out


def build_mpc():
    today = now_bkk().date()
    year = today.year
    try:
        dates = mpc_schedule(year)
        src = "bot.or.th"
    except Exception as e:  # noqa: BLE001
        LOG.append(f"MPC schedule FAIL {err_text(e)} -> ใช้รายการสำรอง")
        dates = [datetime.date.fromisoformat(x) for x in MPC_FALLBACK[year]]
        src = "รายการวันที่สำรองในโปรแกรม"
    LOG.append(f"MPC {year}: {len(dates)} ครั้ง ({src})")
    decisions = mpc_decisions()
    by_date = {d["date"]: (i, d) for i, d in enumerate(decisions)}
    current = decisions[-1]["rate"]

    rows, next_marked = [], False
    for d in dates:
        ann = datetime.datetime(d.year, d.month, d.day, *MPC_TIME, tzinfo=BKK)
        row = {"thai_date": d.isoformat(), "thai_time": ann.strftime("%H:%M"),
               "actual": None, "previous": None, "decision": None}
        if d in by_date:
            i, dec = by_date[d]
            row.update(actual=dec["rate"], decision=dec["decision"], status="done",
                       previous=decisions[i - 1]["rate"] if i > 0 else None)
        elif ann <= now_bkk():
            row.update(status="waiting", previous=current)  # ประชุมแล้ว แต่ไฟล์ยังไม่อัปเดต
        else:
            row.update(status="upcoming", previous=current)
            if not next_marked:
                row["next"] = True
                next_marked = True
        rows.append(row)
    return {"year": year, "meetings": rows, "current": current, "calendar_source": src,
            "source": "ธนาคารแห่งประเทศไทย",
            "link": "https://www.bot.or.th/th/our-roles/monetary-policy/mpc-meeting.html"}


# ---------------------------------------------------------------- เงินเฟ้อ
TPSO = "https://index.tpso.go.th"


def tpso_change(year_be, month, base):
    body = json.dumps({"type": "TG", "yearBase": base, "Categories": ["00000"],
                       "month": month, "year": year_be}).encode()
    t = get(TPSO + "/api/cpig/ChangeRate", data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json",
                     "Origin": TPSO, "Referer": TPSO + "/cpi"})
    rows = json.loads(t)
    return rows[0] if rows else None


def build_cpi():
    master = json.loads(get(TPSO + "/api/cpig/master", headers={"Accept": "application/json"}))
    end = master["period"]["end"]
    base = max(master.get("yearBase") or [2566])
    y, m = end["year"], end["month"]
    rows = []
    for _ in range(6):
        r = tpso_change(y, m, base)
        if r and r.get("changeYear") is not None:
            rows.append({"month": f"{y - 543}-{m:02d}", "yoy": round(r["changeYear"], 2),
                         "mom": r.get("change"), "index": r.get("currentMonthIndex")})
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    if not rows:
        raise ValueError("TPSO ไม่คืนค่าเงินเฟ้อ")
    LOG.append(f"TPSO CPI: ล่าสุด {rows[0]['month']} = {rows[0]['yoy']}%")
    return {"rows": rows, "last_updated": master.get("lastUpdated"),
            "source": "สนค. กระทรวงพาณิชย์",
            "link": "https://index.tpso.go.th/cpi"}


# ---------------------------------------------------------------- GDP
def build_gdp():
    raise ValueError("ยังไม่มีแหล่งข้อมูลที่ดึงอัตโนมัติได้ (เว็บ สศช. ไม่เปิดให้ดึงข้อมูลตรงๆ)")


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


def build_releases(mpc):
    today = now_bkk().date().isoformat()
    items = []
    for r in (mpc or {}).get("meetings") or []:
        if r["thai_date"] >= today and r.get("status") == "upcoming":
            items.append({"thai_date": r["thai_date"], "thai_time": r["thai_time"],
                          "title": "ประชุม กนง. (ดอกเบี้ยนโยบายไทย)"})
    return {"mpc": {"ok": bool(mpc and mpc.get("ok")), "items": items}}


def main():
    try:
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    except Exception:  # noqa: BLE001
        old = {}
    mpc = run_section("mpc", build_mpc, old.get("mpc"))
    out = {
        "updated_at": now_bkk().isoformat(timespec="minutes"),
        "gdp": run_section("gdp", build_gdp, old.get("gdp")),
        "mpc": mpc,
        "cpi": run_section("cpi", build_cpi, old.get("cpi")),
        "releases": build_releases(mpc),
    }
    out["gdp"].update({"todo": True, "link": "https://www.nesdc.go.th/info/economic-aspect/"})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    os.makedirs(DEBUG_DIR, exist_ok=True)
    with open(os.path.join(DEBUG_DIR, "_summary_th.txt"), "w", encoding="utf-8") as f:
        f.write(f"run at {now_bkk().isoformat()}\n\n" + "\n".join(LOG) + "\n")
    print("\n".join(LOG))


if __name__ == "__main__":
    main()
