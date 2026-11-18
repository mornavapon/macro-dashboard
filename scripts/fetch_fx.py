"""ค่าเงินบาท USD/THB ย้อนหลัง 1 ปี (รายวัน) -> data/fx.json

แยกจากสคริปต์อื่นทั้งหมด: ถ้าพัง จะกระทบเฉพาะไฟล์ data/fx.json
แหล่งข้อมูล: Yahoo Finance (THB=X)
"""
import datetime
import json
import os
import urllib.request
from zoneinfo import ZoneInfo

BKK = ZoneInfo("Asia/Bangkok")
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "fx.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
URL = "https://query1.finance.yahoo.com/v8/finance/chart/THB%3DX?range=1y&interval=1d"


def now_bkk():
    return datetime.datetime.now(BKK)


def build():
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        res = json.load(r)["chart"]["result"][0]
    out = {}
    for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]):
        if c is not None:
            out[datetime.datetime.fromtimestamp(t, BKK).date().isoformat()] = round(c, 3)
    p, pt = res["meta"].get("regularMarketPrice"), res["meta"].get("regularMarketTime")
    if p is not None and pt:
        out[datetime.datetime.fromtimestamp(pt, BKK).date().isoformat()] = round(p, 3)
    data = sorted(out.items())
    if len(data) < 150:
        raise ValueError(f"ข้อมูลน้อยผิดปกติ ({len(data)} วัน)")
    last_d, last = data[-1]
    if not 20 < last < 50:
        raise ValueError(f"ค่าผิดปกติ {last}")

    def ago(days):
        target = (datetime.date.fromisoformat(last_d) - datetime.timedelta(days=days)).isoformat()
        return next(v for d, v in reversed(data) if d <= target)

    vals = [v for _, v in data]
    return {"ok": True, "data": [list(x) for x in data],
            "latest": {"date": last_d, "value": last, "m1": ago(30), "m3": ago(91), "y1": data[0][1],
                       "y1_date": data[0][0], "hi": max(vals), "lo": min(vals)},
            "source": "Yahoo Finance (THB=X)", "link": "https://th.tradingview.com/symbols/USDTHB/"}


def main():
    old = {}
    try:
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    except Exception:  # noqa: BLE001
        pass
    try:
        data = build()
        log = f"OK {data['latest']['date']} {data['latest']['value']}"
    except Exception as e:  # noqa: BLE001
        msg = f"{type(e).__name__}: {e}"[:200]
        log = "FAIL " + msg
        data = dict(old, stale=True, error=msg) if old.get("ok") else {"ok": False, "error": msg}
    data["updated_at"] = now_bkk().isoformat(timespec="minutes")
    data["log"] = log
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print("fx:", log)


if __name__ == "__main__":
    main()
