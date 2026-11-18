"""FDI (เงินลงทุนโดยตรงจากต่างประเทศ สุทธิ) จากแบงก์ชาติ -> data/fdi.json

แยกจากสคริปต์อื่นทั้งหมด: ถ้าพัง จะกระทบเฉพาะไฟล์ data/fdi.json
แหล่งข้อมูล: ตารางแนบรายงานภาวะเศรษฐกิจรายไตรมาสของแบงก์ชาติ (PDF ไม่ต้องใช้ API key)
  https://www.bot.or.th/content/dam/bot/documents/en/thai-economy/state-of-thai-economy/monthly-report/macro-YYYY-MM-table_q.pdf
  (ออกทุกไตรมาส: MM = 03, 06, 09, 12 · บรรทัด "FDI" ในหมวด Net Financial Flows หน่วยล้านดอลลาร์ สรอ.)
แต่ละไฟล์มีแค่ ~2 ปี จึงอ่านหลายไฟล์ย้อนหลัง แล้วใช้ค่าจากไฟล์ใหม่สุดของแต่ละไตรมาส (แบงก์ชาติปรับตัวเลขย้อนหลังบ่อย)
"""
import datetime
import io
import json
import os
import re
import urllib.request
from zoneinfo import ZoneInfo

BKK = ZoneInfo("Asia/Bangkok")
ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "data", "fdi.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
BASE = "https://www.bot.or.th/content/dam/bot/documents/en/thai-economy/state-of-thai-economy/monthly-report/"
PAGE = "https://www.bot.or.th/th/thai-economy/state-of-thai-economy/monthly-report.html"
KEEP_QUARTERS = 12


def now_bkk():
    return datetime.datetime.now(BKK)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def pdf_text(data):
    from pypdf import PdfReader
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages)


def parse_table(text):
    """คืน ({(ปี, ไตรมาส): ล้านดอลลาร์}, (ปี, ไตรมาสของรายงาน))"""
    m = re.search(r"Conditions in Quarter (\d) (\d{4})", text)
    if not m:
        raise ValueError("ไม่พบชื่อไตรมาสของรายงาน")
    rq, ry = int(m.group(1)), int(m.group(2))
    lines = text.splitlines()
    fdi_i = next((i for i, l in enumerate(lines) if re.match(r"\s*FDI\s+[-\d,n]", l)), None)
    if fdi_i is None:
        raise ValueError("ไม่พบบรรทัด FDI")
    vals = re.findall(r"-?[\d,]+|n\.a\.", lines[fdi_i].split("FDI", 1)[1])
    head = next(l for l in reversed(lines[:fdi_i]) if re.search(r"(Year|Quarter \d)", l))
    labels = re.findall(r"Year|Quarter (\d)", head)
    labels = ["Y" if not x else int(x) for x in labels]
    if len(labels) != len(vals):
        raise ValueError(f"จำนวนคอลัมน์ไม่ตรง {len(labels)} vs {len(vals)}")
    # เดินย้อนจากคอลัมน์สุดท้าย (= ไตรมาสของรายงาน) แล้วไล่ไตรมาสถอยหลัง ข้ามคอลัมน์ "ทั้งปี"
    out, y, last_q = {}, ry, None
    for lab, v in zip(reversed(labels), reversed(vals)):
        if lab == "Y":
            continue
        if last_q is not None and lab >= last_q:
            y -= 1
        last_q = lab
        if v != "n.a.":
            out[(y, lab)] = int(v.replace(",", ""))
    return out, (ry, rq)


def build():
    today = now_bkk().date()
    files, quarters, latest_report = [], {}, None
    # หาไฟล์ย้อนหลังประมาณ 3.5 ปี (ไฟล์เก่าก่อน ไฟล์ใหม่ทับ)
    cands = []
    for y in range(today.year - 3, today.year + 1):
        for m in (3, 6, 9, 12):
            if datetime.date(y, m, 1) <= today:
                cands.append((y, m))
    errors = []
    for y, m in cands:
        url = f"{BASE}macro-{y}-{m:02d}-table_q.pdf"
        try:
            vals, rep = parse_table(pdf_text(get(url)))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{y}-{m:02d}: {type(e).__name__} {str(e)[:60]}")
            continue
        files.append(url)
        quarters.update(vals)
        latest_report = (rep, url)
    if not quarters or not latest_report:
        raise ValueError("อ่านไฟล์ของแบงก์ชาติไม่ได้เลย: " + "; ".join(errors[-3:]))
    keys = sorted(quarters)[-KEEP_QUARTERS:]
    q = [{"q": f"{y}-Q{k}", "year": y, "quarter": k, "value": quarters[(y, k)]} for y, k in keys]
    ly, lq = keys[-1]
    latest = quarters[(ly, lq)]
    prev_year_same = quarters.get((ly - 1, lq))
    ytd = sum(v for (y, k), v in quarters.items() if y == ly and k <= lq)
    ytd_prev = sum(v for (y, k), v in quarters.items() if y == ly - 1 and k <= lq)
    has_prev = all((ly - 1, k) in quarters for k in range(1, lq + 1))
    years = {}
    for (y, k), v in quarters.items():
        years.setdefault(y, {})[k] = v
    annual = [{"year": y, "value": sum(d.values()), "full": len(d) == 4} for y, d in sorted(years.items())
              if len(d) == 4 or y == ly]
    # ไตรมาสถัดไปที่จะออก: แบงก์ชาติแถลงภาวะเศรษฐกิจรายไตรมาส ~ปลายเดือนถัดจากสิ้นไตรมาส แต่ FDI มักช้าไปอีก 1 รอบ
    return {
        "ok": True,
        "quarters": q,
        "annual": annual,
        "latest": {"q": f"{ly}-Q{lq}", "year": ly, "quarter": lq, "value": latest,
                   "same_q_last_year": prev_year_same,
                   "ytd": ytd, "ytd_prev": ytd_prev if has_prev else None},
        "report": {"year": latest_report[0][0], "quarter": latest_report[0][1], "url": latest_report[1]},
        "unit": "ล้านดอลลาร์ สรอ.",
        "freq": "รายไตรมาส (ออกพร้อมรายงานภาวะเศรษฐกิจของแบงก์ชาติ ช้ากว่าสิ้นไตรมาสประมาณ 2–4 เดือน)",
        "source": "ธนาคารแห่งประเทศไทย (Net Financial Flows: FDI)",
        "link": PAGE,
        "files_read": len(files),
    }


def main():
    old = {}
    try:
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    except Exception:  # noqa: BLE001
        pass
    try:
        data = build()
        log = f"OK latest {data['latest']['q']} = {data['latest']['value']} (อ่าน {data['files_read']} ไฟล์)"
    except Exception as e:  # noqa: BLE001
        msg = f"{type(e).__name__}: {e}"[:200]
        log = "FAIL " + msg
        data = dict(old, stale=True, error=msg) if old.get("ok") else {"ok": False, "error": msg}
    data["updated_at"] = now_bkk().isoformat(timespec="minutes")
    data["log"] = log
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("fdi:", log)


if __name__ == "__main__":
    main()
