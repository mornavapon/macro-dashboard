"""ดึงข้อมูลเสริมผ่าน library settfex (https://github.com/lumduan/settfex) -> data/settfex.json

แยกจากสคริปต์อื่นทั้งหมด: ถ้า settfex ติดตั้งไม่ได้ หรือแหล่งข้อมูลเปลี่ยน
จะกระทบเฉพาะไฟล์ data/settfex.json (หน้าเว็บขึ้น "ดึงข้อมูลไม่สำเร็จ" เฉพาะกล่องนี้)

ส่วนที่ใช้:
  th_yields  อัตราผลตอบแทนพันธบัตรรัฐบาลไทย (ThaiBMA) ย้อนหลัง 2 ปี
"""
import asyncio
import datetime
import json
import os
from zoneinfo import ZoneInfo

BKK = ZoneInfo("Asia/Bangkok")
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "settfex.json")
LOG = []
KEY_TENORS = ["3M", "1Y", "2Y", "5Y", "10Y", "20Y", "30Y"]


def now_bkk():
    return datetime.datetime.now(BKK)


def next_business_day(d):
    d += datetime.timedelta(days=1)
    while d.weekday() >= 5:
        d += datetime.timedelta(days=1)
    return d


def run_section(name, fn, old):
    try:
        data = fn()
        data["ok"] = True
        data["fetched_at"] = now_bkk().isoformat(timespec="minutes")
        LOG.append(f"{name}: OK")
        return data
    except Exception as e:  # noqa: BLE001
        msg = f"{type(e).__name__}: {e}"[:200]
        LOG.append(f"{name}: FAIL {msg}")
        if old and old.get("ok"):
            kept = dict(old)
            kept["stale"] = True
            kept["error"] = msg
            return kept
        return {"ok": False, "error": msg}


def build_th_yields():
    from settfex.services.thaibma import get_yield_curve_history  # import ในนี้: ถ้าพังจะพังแค่ส่วนนี้

    end = now_bkk().date()
    start = end - datetime.timedelta(days=731)
    h = asyncio.run(get_yield_curve_history(start, end))
    rows = [r for r in h.rows if r.get("2Y") is not None and r.get("10Y") is not None]
    if len(rows) < 100:
        raise ValueError(f"ข้อมูลน้อยผิดปกติ ({len(rows)} วัน)")
    y2 = [[r.as_of.isoformat(), round(r.get("2Y"), 3)] for r in rows]
    y10 = [[r.as_of.isoformat(), round(r.get("10Y"), 3)] for r in rows]
    spread = [[a[0], round(b[1] - a[1], 3)] for a, b in zip(y2, y10)]
    last = rows[-1]
    # ค่าเมื่อ ~1 ปีก่อน ไว้เทียบในตาราง
    target = last.as_of - datetime.timedelta(days=365)
    year_ago = min(rows, key=lambda r: abs((r.as_of - target).days))
    curve = []
    for t in KEY_TENORS:
        v, p = last.get(t), year_ago.get(t)
        if v is None:
            continue
        curve.append({"tenor": t, "now": round(v, 3), "year_ago": None if p is None else round(p, 3)})
    for x in (y2[-1][1], y10[-1][1]):
        if not -1 < x < 15:
            raise ValueError(f"ค่าผิดปกติ {x}")
    return {"y2": y2, "y10": y10, "spread": spread, "curve": curve,
            "year_ago_date": year_ago.as_of.isoformat(),
            "latest": {"date": last.as_of.isoformat(), "y2": y2[-1][1], "y10": y10[-1][1], "spread": spread[-1][1]},
            "freq": "ทุกวันทำการ (ThaiBMA ประกาศช่วงเย็น)",
            "next": next_business_day(last.as_of).isoformat(),
            "source": "ThaiBMA ผ่าน settfex",
            "link": "https://www.thaibma.or.th/EN/Market/YieldCurve/Government.aspx"}


def main():
    old = {}
    try:
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    except Exception:  # noqa: BLE001
        pass
    try:
        import settfex
        ver = settfex.__version__
    except Exception as e:  # noqa: BLE001
        ver = f"import ไม่ได้: {e}"
    out = {
        "updated_at": now_bkk().isoformat(timespec="minutes"),
        "settfex_version": ver,
        "th_yields": run_section("th_yields", build_th_yields, old.get("th_yields")),
    }
    out["log"] = LOG
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n".join(LOG))


if __name__ == "__main__":
    main()
