#!/usr/bin/env python3
"""
ภาพวงกลม "จักรวาลดัชนีหุ้นสหรัฐฯ" (หน้า 1) -> data/universe.json

- NYSE Composite  = หุ้นทุกตัวในตลาด NYSE
- Nasdaq Composite = หุ้นทุกตัวในตลาด Nasdaq   (สองตลาดนี้ไม่ทับกัน)
- S&P 500  = หุ้นใหญ่ 500 บริษัท คร่อมทั้ง 2 ตลาด
- Dow Jones = 30 ตัว อยู่ใน S&P 500 ทั้งหมด

แหล่งข้อมูล: stockanalysis.com (รายชื่อหุ้น + Market Cap + ตลาดที่จดทะเบียน + ยอดรวมทั้งตลาด)
รันทุกวันที่ 1 และ 15 ของเดือน (ประมาณทุก 2 สัปดาห์)
"""
import datetime
import json
import os
import re
import urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "universe.json")
BKK = ZoneInfo("Asia/Bangkok")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
SA = "https://stockanalysis.com/list/"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_list(html):
    """คืน (รายการหุ้น, ยอดรวม Market Cap ที่หน้าเว็บแสดง, จำนวนหุ้นทั้งหมด)"""
    rows = []
    for obj in re.findall(r'\{[^{}]*?\bs:"[^"]+"[^{}]*?\bmarketCap:[^{}]*?\}', html):
        s = re.search(r'\bs:"([^"]+)"', obj).group(1)
        n = re.search(r'\bn:"([^"]*)"', obj)
        cap = re.search(r"\bmarketCap:\s*([0-9.]+(?:e\+?\d+)?)", obj)
        ex = re.search(r'\bexchange:"([^"]+)"', obj)
        if cap:
            rows.append({"s": s, "n": n.group(1) if n else s, "cap": float(cap.group(1)),
                         "ex": ex.group(1) if ex else None})
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", text))
    tot = re.search(r"Total Market Cap\D{0,40}?([\d.]+)\s*([TB])", text)
    cnt = re.search(r"Total Stocks\D{0,40}?([\d,]+)", text)
    total = None
    if tot:
        total = float(tot.group(1)) * (1e12 if tot.group(2) == "T" else 1e9)
    return rows, total, int(cnt.group(1).replace(",", "")) if cnt else len(rows)


def split_by_exchange(members, exch_of):
    """แบ่ง Market Cap ของสมาชิกดัชนีตามตลาดที่จดทะเบียน (บริษัทที่มีหลายคลาสหุ้นนับครั้งเดียว)"""
    seen, out, unknown = set(), {"NYSE": 0.0, "NASDAQ": 0.0}, []
    for r in members:
        key = (r["n"], round(r["cap"]))
        if key in seen:
            continue
        seen.add(key)
        ex = exch_of.get(r["s"])
        if ex not in out:
            unknown.append(r["s"])
            ex = "NYSE"  # หุ้นใหญ่ที่ไม่อยู่ในรายชื่อ Nasdaq ส่วนใหญ่อยู่ NYSE
        out[ex] += r["cap"]
    return out, unknown


def main():
    log = []
    nasdaq_rows, nasdaq_total, nasdaq_n = parse_list(get(SA + "nasdaq-stocks/"))
    nyse_rows, nyse_total, nyse_n = parse_list(get(SA + "nyse-stocks/"))
    sp_rows, sp_total, sp_n = parse_list(get(SA + "sp-500-stocks/"))
    dow_rows, dow_total, dow_n = parse_list(get(SA + "dow-jones-stocks/"))
    check = {"nasdaq_total": nasdaq_total, "nyse_total": nyse_total,
             "sp_rows": len(sp_rows), "dow_rows": len(dow_rows), "nasdaq_rows": len(nasdaq_rows)}
    print("check:", check)
    if not all(check.values()):
        raise SystemExit("อ่านข้อมูลไม่ครบ (หน้าเว็บอาจเปลี่ยนรูปแบบ)")

    exch_of = {r["s"]: r["ex"] for r in nasdaq_rows + nyse_rows if r["ex"]}
    sp_split, sp_unknown = split_by_exchange(sp_rows, exch_of)
    dow_split, dow_unknown = split_by_exchange(dow_rows, exch_of)
    # ใช้ยอดรวมทางการของหน้าเว็บ แล้วแบ่งสัดส่วนตามผลรวมรายตัว
    sp_total = sp_total or sum(sp_split.values())
    dow_total = dow_total or sum(dow_split.values())
    sp_nyse_frac = sp_split["NYSE"] / max(1, sum(sp_split.values()))
    dow_nyse_frac = dow_split["NYSE"] / max(1, sum(dow_split.values()))
    log.append(f"S&P ที่หาตลาดไม่เจอ (นับเป็น NYSE): {sp_unknown}")
    log.append(f"Dow ที่หาตลาดไม่เจอ (นับเป็น NYSE): {dow_unknown}")

    today = datetime.datetime.now(BKK).date()
    nxt = datetime.date(today.year + (today.month == 12), today.month % 12 + 1, 1) if today.day >= 15 \
        else datetime.date(today.year, today.month, 15)
    out = {
        "asof": today.isoformat(), "next": nxt.isoformat(),
        "freq": "ประมาณทุก 2 สัปดาห์ (วันที่ 1 และ 15 ของเดือน)",
        "nyse": {"cap": nyse_total, "count": nyse_n},
        "nasdaq": {"cap": nasdaq_total, "count": nasdaq_n},
        "sp500": {"cap": sp_total, "count": sp_n, "nyse_frac": round(sp_nyse_frac, 4)},
        "dow": {"cap": dow_total, "count": dow_n, "nyse_frac": round(dow_nyse_frac, 4)},
        "source": "stockanalysis.com", "log": log,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
