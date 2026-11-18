"""ทดสอบ settfex แต่ละส่วนแยกกัน (ไม่เขียนข้อมูลลง repo) — ใช้ตรวจว่าใช้งานได้จริงไหม"""
import asyncio, json, time, traceback
from datetime import date, timedelta

async def run(name, coro):
    t = time.time()
    try:
        r = await coro
        print(f"\n=== {name}: OK ({time.time()-t:.1f}s)")
        return r
    except Exception as e:
        print(f"\n=== {name}: FAIL ({time.time()-t:.1f}s) {type(e).__name__}: {e}")
        traceback.print_exc(limit=2)

async def main():
    import settfex
    print("settfex", settfex.__version__)
    from settfex import get_index_info
    from settfex.services.thaibma import get_government_yield_curve, get_yield_curve_history
    from settfex.services.tfex.list import get_series_list
    from settfex.services.tfex.trading_statistics import get_trading_statistics

    r = await run("SET index info", get_index_info("SET"))
    if r: print(r.model_dump(mode="json"))
    raw = None
    try:
        from settfex.services.set.index.info import IndexInfoService
        raw = await run("SET index info RAW", IndexInfoService().fetch_index_info_raw("SET"))
        if raw: print(json.dumps(raw, ensure_ascii=False)[:1500])
    except Exception as e: print("raw err", e)

    c = await run("ThaiBMA latest curve", get_government_yield_curve())
    if c:
        d = c.model_dump(mode="json")
        print({k: (v if not isinstance(v, list) else f"list[{len(v)}]") for k, v in d.items()})
        print("curve sample:", json.dumps(d.get("curve", d.get("points", []))[:20], ensure_ascii=False)[:1500])

    h = await run("ThaiBMA 2y history", get_yield_curve_history(date.today()-timedelta(days=730), date.today()))
    if h:
        print("rows", h.count, "columns", h.columns[:60])
        for row in h.rows[:2] + h.rows[-3:]:
            print(row.as_of, {k: row.get(k) for k in ("3M","1Y","2Y","5Y","10Y","30Y")})

    s = await run("TFEX series list", get_series_list())
    if s:
        fut = [x for x in s.series if x.underlying == "SET50" and x.options_type in ("", None, "N/A") and x.active] if hasattr(s, "series") else []
        print("total", len(s.series), "SET50 futures:", [(x.symbol, x.contract_month) for x in fut][:8])
        if not fut:
            print([x.model_dump(mode="json") for x in s.series[:3]])
        if fut:
            fut.sort(key=lambda x: x.last_trading_date)
            t = await run(f"TFEX stats {fut[0].symbol}", get_trading_statistics(fut[0].symbol))
            if t: print(t.model_dump(mode="json"))

asyncio.run(main())
