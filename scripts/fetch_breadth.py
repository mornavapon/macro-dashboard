"""Market Breadth: % หุ้นใน S&P 500 ที่ยืนเหนือเส้นค่าเฉลี่ย 200 วัน -> data/breadth.json

แยกจากสคริปต์อื่นทั้งหมด: ถ้าพัง จะกระทบเฉพาะไฟล์ data/breadth.json
(หน้าเว็บขึ้น "ดึงข้อมูลไม่สำเร็จ" เฉพาะกล่องนี้)

วิธีคำนวณ (คำนวณเอง เพราะไม่มีแหล่งฟรีที่ให้ย้อนหลัง):
  1. รายชื่อหุ้น S&P 500 จาก stockanalysis.com (ถ้าดึงไม่ได้ ใช้รายชื่อรอบก่อนที่เก็บไว้)
  2. ราคาปิดรายวันย้อนหลัง 3 ปีของทุกตัว จาก Yahoo Finance
  3. ทุกวัน: นับหุ้นที่ราคาปิด > ค่าเฉลี่ย 200 วันของตัวเอง หารด้วยจำนวนหุ้นที่มีข้อมูลครบ 200 วัน
หมายเหตุ: ใช้รายชื่อหุ้นปัจจุบันย้อนไปทั้ง 2 ปี (ไม่รู้ว่าเมื่อก่อนมีตัวไหนเข้า/ออก) ค่าย้อนหลังจึงเป็นค่าประมาณ
"""
import datetime
import json
import os
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo

BKK = ZoneInfo("Asia/Bangkok")
NY = ZoneInfo("America/New_York")
ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "data", "breadth.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
SHOW_DAYS = 731


def now_bkk():
    return datetime.datetime.now(BKK)


def get(url, accept="*/*", timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def sp500_members():
    html = get("https://stockanalysis.com/list/sp-500-stocks/", accept="text/html")
    syms = re.findall(r'\{[^{}]*?\bs:"([^"]+)"[^{}]*?\bmarketCap:', html)
    syms = list(dict.fromkeys(syms))
    if not 480 <= len(syms) <= 520:
        raise ValueError(f"รายชื่อหุ้นผิดปกติ ({len(syms)} ตัว)")
    return syms


def closes(sym):
    """ราคาปิดรายวัน 3 ปี {วันที่: ราคา} (ลองซ้ำ 3 ครั้ง)"""
    ysym = sym.replace(".", "-")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ysym)}?range=3y&interval=1d"
    for i in range(3):
        try:
            res = json.loads(get(url))["chart"]["result"][0]
            out = {datetime.datetime.fromtimestamp(t, NY).date().isoformat(): c
                   for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]) if c is not None}
            p, pt = res["meta"].get("regularMarketPrice"), res["meta"].get("regularMarketTime")
            if p is not None and pt:
                out[datetime.datetime.fromtimestamp(pt, NY).date().isoformat()] = p
            return out
        except Exception:  # noqa: BLE001
            time.sleep(1.5 * (i + 1))
    return None


def above_ma(series, days, n):
    """คืน {วันที่: True/False} ว่าราคาปิดอยู่เหนือค่าเฉลี่ย n วันหรือไม่ (เฉพาะวันที่มีข้อมูลครบ n วัน)"""
    ds = sorted(series)
    vals = [series[d] for d in ds]
    out, s = {}, 0.0
    for i, v in enumerate(vals):
        s += v
        if i >= n:
            s -= vals[i - n]
        if i >= n - 1:
            out[ds[i]] = v > s / n
    return out


def build(old):
    try:
        members = sp500_members()
        members_src = "stockanalysis.com"
    except Exception as e:  # noqa: BLE001
        members = (old or {}).get("members")
        if not members:
            raise
        members_src = f"รายชื่อรอบก่อน (ดึงใหม่ไม่ได้: {type(e).__name__})"

    with ThreadPoolExecutor(max_workers=8) as ex:
        data = dict(zip(members, ex.map(closes, members)))
    ok = {s: c for s, c in data.items() if c and len(c) > 250}
    missing = sorted(set(members) - set(ok))
    if len(ok) < 0.9 * len(members):
        raise ValueError(f"ดึงราคาได้แค่ {len(ok)}/{len(members)} ตัว")

    spx = closes("^GSPC")
    if not spx:
        raise ValueError("ดึงดัชนี S&P 500 ไม่ได้")
    days = sorted(spx)
    last_day = days[-1]
    start = (datetime.date.fromisoformat(last_day) - datetime.timedelta(days=SHOW_DAYS)).isoformat()
    show = [d for d in days if d >= start]

    a200 = {s: above_ma(c, days, 200) for s, c in ok.items()}
    a50 = {s: above_ma(c, days, 50) for s, c in ok.items()}

    def pct(table, d):
        flags = [t[d] for t in table.values() if d in t]
        return (round(100 * sum(flags) / len(flags), 1), sum(flags), len(flags)) if len(flags) >= 400 else None

    series = []
    for d in show:
        p = pct(a200, d)
        if p:
            series.append([d, p[0]])
    if len(series) < 300:
        raise ValueError(f"คำนวณได้น้อยผิดปกติ ({len(series)} วัน)")
    ld = series[-1][0]
    p200, n_up, n_all = pct(a200, ld)
    p50 = pct(a50, ld)

    spx_ma = above_ma(spx, days, 200)
    sv = [spx[d] for d in days]
    ma200 = sum(sv[-200:]) / 200
    hi52 = max(sv[-252:])
    idx3m = len(series) - 1 - 63
    spx_show = [[d, round(spx[d], 2)] for d in show if d >= series[0][0]]
    return {
        "ok": True,
        "series": series,
        "spx": spx_show,
        "latest": {
            "date": ld, "pct200": p200, "up": n_up, "total": n_all,
            "pct50": p50[0] if p50 else None,
            "pct200_3m_ago": series[idx3m][1] if idx3m >= 0 else None,
            "spx": round(spx[ld], 2), "spx_vs_ma200": round((spx[ld] / ma200 - 1) * 100, 1),
            "spx_above_ma200": spx_ma.get(ld),
            "spx_from_high": round((spx[ld] / hi52 - 1) * 100, 1),
            "spx_3m": round((spx[ld] / spx[series[idx3m][0]] - 1) * 100, 1) if idx3m >= 0 else None,
        },
        "members": members,
        "members_source": members_src,
        "missing": missing,
        "freq": "ทุกวันทำการของตลาดสหรัฐฯ (คำนวณเช้าวันถัดไปตามเวลาไทย)",
        "source": "คำนวณเองจากราคาหุ้น S&P 500 ทุกตัว (Yahoo Finance)",
        "link": "https://th.tradingview.com/symbols/INDEX-S5TH/",
    }


def main():
    old = {}
    try:
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    except Exception:  # noqa: BLE001
        pass
    t0 = time.time()
    try:
        data = build(old)
        log = f"OK {data['latest']['date']} {data['latest']['pct200']}% ({len(data['missing'])} ตัวดึงไม่ได้) {time.time() - t0:.0f}s"
    except Exception as e:  # noqa: BLE001
        msg = f"{type(e).__name__}: {e}"[:200]
        log = "FAIL " + msg
        if old.get("ok"):
            data = dict(old, stale=True, error=msg)
        else:
            data = {"ok": False, "error": msg}
    data["updated_at"] = now_bkk().isoformat(timespec="minutes")
    data["log"] = log
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print("breadth:", log)


if __name__ == "__main__":
    main()
