"""เงินต่างชาติในตลาดตราสารหนี้ไทย (Non-resident Flows) จาก ThaiBMA -> data/bondflow.json

แยกจากสคริปต์อื่นทั้งหมด: ถ้า ThaiBMA เปลี่ยนรูปแบบ จะกระทบเฉพาะไฟล์ data/bondflow.json
(หน้าเว็บขึ้น "ดึงข้อมูลไม่สำเร็จ" เฉพาะกล่องนี้)

แหล่งข้อมูล: https://www.thaibma.or.th/nrdaily/GetNR/  (ข้อมูลเดียวกับหน้า
https://www.thaibma.or.th/EN/Market/NR/NRDaily.aspx) ได้รายวันย้อนหลังตั้งแต่ปี 2016 ในครั้งเดียว
หน่วย: ล้านบาท
  ShortTermTrade / LongTermTrade  ซื้อขายสุทธิ ตราสารอายุคงเหลือ <= 1 ปี / > 1 ปี
  ExpireToday                     ตราสารที่ต่างชาติถือแล้วครบอายุวันนี้ (เงินไหลออกโดยไม่ได้ขาย)
  NetFlow                         เงินไหลเข้า(+)/ออก(-) สุทธิ = ซื้อขายสุทธิ - ครบอายุ
  ShortTermHolding / LongTermHolding / NetHolding   ยอดถือครองของต่างชาติ (มูลค่าที่ตราไว้)
ThaiBMA ประกาศวันละ 3 รอบ: 08:30 (ของเย็นวานนี้), 12:00, 16:30
"""
import datetime
import json
import os
import urllib.request
from collections import OrderedDict
from zoneinfo import ZoneInfo

BKK = ZoneInfo("Asia/Bangkok")
URL = "https://www.thaibma.or.th/nrdaily/GetNR/"
PAGE = "https://www.thaibma.or.th/EN/Market/NR/NRDaily.aspx"
ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "data", "bondflow.json")
DEBUG = os.path.join(ROOT, "data", "debug", "bondflow_raw.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
MONTHS = 24          # กราฟรายเดือนย้อนหลัง
HOLD_DAYS = 731      # กราฟยอดถือครองย้อนหลัง (วัน)


def now_bkk():
    return datetime.datetime.now(BKK)


def num(v):
    return None if v is None else float(v)


def fetch_rows():
    req = urllib.request.Request(URL, headers={"User-Agent": UA, "Accept": "application/json",
                                               "Referer": PAGE})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = json.load(r)
    os.makedirs(os.path.dirname(DEBUG), exist_ok=True)
    with open(DEBUG, "w", encoding="utf-8") as f:   # เก็บดิบเฉพาะ 30 วันล่าสุด ไว้ตรวจสอบ
        json.dump(raw[:30], f, ensure_ascii=False, indent=0)
    rows = []
    for x in raw:
        d = datetime.date.fromisoformat(x["Asof"][:10])
        st, lt, ex = num(x.get("ShortTermTrade")), num(x.get("LongTermTrade")), num(x.get("ExpireToday")) or 0.0
        flow = num(x.get("NetFlow"))
        if flow is None and st is not None and lt is not None:
            flow = st + lt - ex
        rows.append({"date": d, "st": st, "lt": lt, "exp": ex, "flow": flow,
                     "h_st": num(x.get("ShortTermHolding")), "h_lt": num(x.get("LongTermHolding")),
                     "h": num(x.get("NetHolding")), "exp_next": num(x.get("ExpireNextDay")),
                     "p3_buy": num(x.get("P3Buy")) or 0.0, "p3_sell": num(x.get("P3Sell")) or 0.0})
    rows.sort(key=lambda r: r["date"])
    rows = [r for r in rows if r["flow"] is not None]
    if len(rows) < 300:
        raise ValueError(f"ข้อมูลน้อยผิดปกติ ({len(rows)} วัน)")
    return rows


def total(rows):
    """รวมยอดของหลายวัน: ระยะสั้น ระยะยาว ครบอายุ และสุทธิ"""
    s = {"st": 0.0, "lt": 0.0, "exp": 0.0, "flow": 0.0, "days": len(rows)}
    for r in rows:
        s["st"] += r["st"] or 0.0
        s["lt"] += r["lt"] or 0.0
        s["exp"] += r["exp"] or 0.0
        s["flow"] += r["flow"]
    return {k: (round(v) if k != "days" else v) for k, v in s.items()}


def build():
    rows = fetch_rows()
    now = now_bkk()
    last = rows[-1]
    ld = last["date"]

    # ข้อมูลของ "วันนี้" ยังไม่ครบถ้ายังไม่ถึงรอบประกาศ 16:30
    partial = None
    if ld == now.date():
        if now.time() < datetime.time(12, 0):
            partial = "มีแค่รอบ 08:30 (รายการเย็นวานนี้) · รอบถัดไป 12:00 น."
        elif now.time() < datetime.time(16, 30) or (last["p3_buy"] == 0 and last["p3_sell"] == 0):
            partial = "มีถึงรอบ 12:00 น. · รอบสุดท้ายของวันประกาศ 16:30 น."

    week = rows[-5:]                     # 5 วันทำการล่าสุด
    mtd = [r for r in rows if r["date"].year == ld.year and r["date"].month == ld.month]
    ytd = [r for r in rows if r["date"].year == ld.year]

    # รายเดือนย้อนหลัง
    months = OrderedDict()
    for r in rows:
        months.setdefault(r["date"].strftime("%Y-%m"), []).append(r)
    monthly = [{"month": m, **total(rs)} for m, rs in list(months.items())[-MONTHS:]]

    # ยอดถือครองย้อนหลัง (ใช้ค่าวันสุดท้ายของแต่ละสัปดาห์ให้ไฟล์ไม่ใหญ่เกิน + วันล่าสุด)
    cut = ld - datetime.timedelta(days=HOLD_DAYS)
    hold_rows = [r for r in rows if r["date"] >= cut and r["h"]]
    weekly_last = OrderedDict()
    for r in hold_rows:
        weekly_last[r["date"].isocalendar()[:2]] = r
    hold = list(weekly_last.values())
    if hold and hold[-1] is not hold_rows[-1]:
        hold.append(hold_rows[-1])
    holding = {
        "total": [[r["date"].isoformat(), round(r["h"] / 1000, 1)] for r in hold],   # พันล้านบาท
        "st": [[r["date"].isoformat(), round(r["h_st"] / 1000, 1)] for r in hold if r["h_st"] is not None],
        "lt": [[r["date"].isoformat(), round(r["h_lt"] / 1000, 1)] for r in hold if r["h_lt"] is not None],
    }
    year_ago = min(hold_rows, key=lambda r: abs((r["date"] - (ld - datetime.timedelta(days=365))).days))
    ytd_start = [r for r in rows if r["date"].year < ld.year]
    ytd_base = ytd_start[-1] if ytd_start else None

    # 5 วันทำการล่าสุด แบบรายวัน (ไว้แสดงเป็นแถว)
    days = [{"date": r["date"].isoformat(), "st": round(r["st"] or 0), "lt": round(r["lt"] or 0),
             "exp": round(r["exp"] or 0), "flow": round(r["flow"])} for r in reversed(week)]

    # ขนาด flow รายสัปดาห์ (5 วันทำการ) ย้อนหลัง 2 ปี ไว้เทียบว่า "มาก/น้อย" แค่ไหน
    recent = [r for r in rows if r["date"] >= cut]
    roll = [sum(x["flow"] for x in recent[i - 4:i + 1]) for i in range(4, len(recent))]
    roll_sorted = sorted(abs(v) for v in roll)
    p80 = roll_sorted[int(len(roll_sorted) * 0.8)] if roll_sorted else None
    p95 = roll_sorted[int(len(roll_sorted) * 0.95)] if roll_sorted else None

    return {
        "ok": True,
        "latest": {"date": ld.isoformat(), "partial": partial, **{k: round(last[k] or 0) for k in ("st", "lt", "exp", "flow")},
                   "exp_next": round(last["exp_next"] or 0)},
        "days": days,
        "week": {"from": week[0]["date"].isoformat(), "to": ld.isoformat(), **total(week)},
        "mtd": {"month": ld.strftime("%Y-%m"), **total(mtd)},
        "ytd": {"year": ld.year, **total(ytd)},
        "monthly": monthly,
        "holding_now": {"total": round(last["h"]), "st": round(last["h_st"] or 0), "lt": round(last["h_lt"] or 0)},
        "holding_year_ago": {"date": year_ago["date"].isoformat(), "total": round(year_ago["h"])},
        "holding_ytd_base": {"date": ytd_base["date"].isoformat(), "total": round(ytd_base["h"])} if ytd_base and ytd_base["h"] else None,
        "holding": holding,
        # ขนาด flow รวม 5 วันทำการ (ค่าสัมบูรณ์) ใน 2 ปีที่ผ่านมา: 80% ของช่วงเวลาไม่เกิน p80, 95% ไม่เกิน p95
        "week_p80": round(p80) if p80 else None,
        "week_p95": round(p95) if p95 else None,
        "week_min_2y": round(min(roll)) if roll else None,
        "weeks_out_over_20k_2y": sum(1 for v in roll if v <= -20000),
        "freq": "ทุกวันทำการ วันละ 3 รอบ (08:30 / 12:00 / 16:30 น.)",
        "source": "ThaiBMA (Non-resident Flows)",
        "link": PAGE,
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
        log = "OK"
    except Exception as e:  # noqa: BLE001
        msg = f"{type(e).__name__}: {e}"[:200]
        log = "FAIL " + msg
        if old.get("ok"):
            data = dict(old)
            data["stale"] = True
            data["error"] = msg
        else:
            data = {"ok": False, "error": msg}
    data["updated_at"] = now_bkk().isoformat(timespec="minutes")
    data["log"] = log
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("bondflow:", log)


if __name__ == "__main__":
    main()
