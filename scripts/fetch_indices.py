#!/usr/bin/env python3
"""
ดึงข้อมูลดัชนีสำคัญ 6 ตัว -> data/indices.json

หลักการ:
- แต่ละดัชนี และแต่ละช่องข้อมูล (ระดับดัชนี / Market Cap / P/E / P/BV) ดึงแยกกัน
  ถ้าอันไหนพัง อันอื่นยังทำงานต่อได้
- ถ้ารอบนี้ดึงไม่สำเร็จ แต่รอบก่อนเคยได้ค่า -> เก็บค่าเก่าไว้ และติดป้าย "ข้อมูลเก่า"
- ทุกแหล่งที่ลองดึง จะบันทึกผลดิบไว้ใน data/debug/ เพื่อใช้ตรวจสอบ/ปรับแหล่งข้อมูลรอบถัดไป
- ใช้แค่ Python มาตรฐาน ไม่ต้องติดตั้งอะไรเพิ่ม
"""
import datetime
import http.cookiejar
import json
import os
import re
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "indices.json")
DEBUG_DIR = os.path.join(ROOT, "data", "debug")
BKK = ZoneInfo("Asia/Bangkok")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

PROBE_LOG = []  # สรุปผลการลองแต่ละแหล่ง (เขียนลง data/debug/_summary.txt)


# ---------------------------------------------------------------- helpers
def now_bkk():
    return datetime.datetime.now(BKK)


def get(url, headers=None, timeout=25):
    h = {
        "User-Agent": UA,
        "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,th;q=0.8",
    }
    if headers:
        h.update(headers)
    with _opener.open(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        raw = r.read()
        cs = r.headers.get_content_charset() or "utf-8"
    return raw.decode(cs, errors="replace")


def save_debug(name, url, text):
    os.makedirs(DEBUG_DIR, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    with open(os.path.join(DEBUG_DIR, safe + ".txt"), "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\nFETCHED: {now_bkk().isoformat()}\n\n{text[:8000]}")


def to_num(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def err_text(e):
    return f"{type(e).__name__}: {e}"[:220]


def find_obj_with_value(obj, wanted):
    """หา dict ใน JSON ที่มีค่า (string) ตรงกับ wanted ตัวใดตัวหนึ่ง"""
    wanted = {w.lower() for w in wanted}
    queue = [obj]
    while queue:
        o = queue.pop(0)
        if isinstance(o, dict):
            for v in o.values():
                if isinstance(v, str) and v.strip().lower() in wanted:
                    return o
            queue.extend(o.values())
        elif isinstance(o, list):
            queue.extend(o)
    return None


def add_pair_keys(obj):
    """แปลงรายการแบบ {ratioCode: X, value: Y} ให้กลายเป็น key X: Y เพื่อค้นหาง่าย"""
    if isinstance(obj, dict):
        code = obj.get("ratioCode") or obj.get("itemCode") or obj.get("itemName")
        if code is not None and "value" in obj:
            obj[str(code)] = obj["value"]
        for v in list(obj.values()):
            add_pair_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            add_pair_keys(v)


def find_by_keys(obj, keys):
    """ค้นหา key (ไม่สนตัวพิมพ์เล็กใหญ่) ใน JSON ซ้อนหลายชั้น คืนค่าตัวเลขแรกที่เจอ"""
    keys = {k.lower() for k in keys}
    queue = [obj]
    while queue:
        o = queue.pop(0)
        if isinstance(o, dict):
            for k, v in o.items():
                if k.lower() in keys and to_num(v) is not None:
                    return to_num(v)
            queue.extend(o.values())
        elif isinstance(o, list):
            queue.extend(o)
    return None


def find_text_by_keys(obj, keys):
    keys = {k.lower() for k in keys}
    queue = [obj]
    while queue:
        o = queue.pop(0)
        if isinstance(o, dict):
            for k, v in o.items():
                if k.lower() in keys and isinstance(v, (str, int)) and str(v).strip():
                    return str(v)
            queue.extend(o.values())
        elif isinstance(o, list):
            queue.extend(o)
    return None


def regex_by_keys(text, keys):
    """สำหรับหน้า HTML ที่ฝัง JSON ไว้ เช่น "pe":12.3"""
    for k in keys:
        m = re.search(r'"%s"\s*:\s*"?(-?[\d.,]+)' % re.escape(k), text)
        if m and to_num(m.group(1)) is not None:
            return to_num(m.group(1))
    return None


# ------------------------------------------------------- index level sources
def yahoo_level(symbol):
    last_err = None
    res = None
    for host in ("query1", "query2"):
        url = (f"https://{host}.finance.yahoo.com/v8/finance/chart/"
               f"{urllib.parse.quote(symbol)}?range=10d&interval=1d")
        try:
            text = get(url)
            res = json.loads(text)["chart"]["result"][0]
            break
        except Exception as e:  # noqa: BLE001
            last_err = e
    if res is None:
        raise last_err or ValueError("Yahoo ไม่ตอบกลับ")

    meta = res["meta"]
    tz = ZoneInfo(meta.get("exchangeTimezoneName") or "UTC")
    ts = res.get("timestamp") or []
    closes = (res.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    pts = [(t, c) for t, c in zip(ts, closes) if c is not None]

    price = meta.get("regularMarketPrice")
    ptime = meta.get("regularMarketTime")
    if (price is None or ptime is None) and pts:
        ptime, price = pts[-1]
    if price is None:
        raise ValueError("ไม่มีราคาในผลลัพธ์")

    pdate = datetime.datetime.fromtimestamp(ptime, tz).date()
    prev = None
    for t, c in reversed(pts):
        if datetime.datetime.fromtimestamp(t, tz).date() < pdate:
            prev = c
            break

    out = {"value": round(price, 2), "asof": pdate.isoformat(),
           "source": f"Yahoo Finance ({symbol})"}
    if prev:
        out["change"] = round(price - prev, 2)
        out["pct"] = round((price - prev) / prev * 100, 2)
    return out


def vndirect_level():
    url = ("https://finfo-api.vndirect.com.vn/v4/vnmarket_prices"
           "?sort=date&q=code:VNINDEX&size=3")
    text = get(url, headers={"Referer": "https://dstock.vndirect.com.vn/"})
    save_debug("vni_level_vndirect", url, text)
    rows = json.loads(text).get("data") or []
    if not rows:
        raise ValueError("VNDirect ไม่มีข้อมูล")
    r = rows[0]
    out = {"value": round(to_num(r.get("close")), 2), "asof": r.get("date"),
           "source": "VNDirect"}
    if to_num(r.get("change")) is not None:
        out["change"] = round(to_num(r.get("change")), 2)
    if to_num(r.get("pctChange")) is not None:
        out["pct"] = round(to_num(r.get("pctChange")), 2)
    return out


# --------------------------------------------- fundamentals (P/E, P/BV, Cap)
FIELD_LABEL = {"pe": "P/E", "pbv": "P/BV", "market_cap": "Market Cap"}


def probe_json(tag, candidates, keymap, select=None, cap_scale=1.0,
               cap_currency=None, date_keys=None, note=None):
    """
    ลองดึงจากหลาย URL ตามลำดับ แล้วค้นหาค่าตาม keymap
    candidates: list ของ (url, headers)
    keymap: {"pe": [...keys], "pbv": [...], "market_cap": [...]}
    select: ถ้ามี จะหา sub-object ที่มีค่าตรงกับชื่อนี้ก่อน (เช่น "SET", "HSCE")
    คืน {field: result}
    """
    date_keys = date_keys or ["marketDateTime", "asOfDate", "asOf", "tradeDate",
                              "TRADE_DATE", "date", "reportDate", "updateTime"]
    found = {}
    errors = []
    for i, (url, headers) in enumerate(candidates):
        if all(f in found for f in keymap):
            break
        try:
            text = get(url, headers=headers)
            save_debug(f"{tag}_{i}", url, text)
        except Exception as e:  # noqa: BLE001
            errors.append(f"[{i}] {err_text(e)}")
            PROBE_LOG.append(f"{tag}[{i}] FAIL {url} -> {err_text(e)}")
            continue

        obj = None
        try:
            s = text.strip()
            if s.startswith("(") and s.endswith(")"):  # JSONP
                s = s[1:-1]
            obj = json.loads(s)
        except ValueError:
            obj = None

        got_here = []
        if obj is not None:
            add_pair_keys(obj)
            scope = obj
            if select:
                sub = find_obj_with_value(obj, select)
                if sub is not None:
                    scope = sub
            asof = find_text_by_keys(scope, date_keys) or find_text_by_keys(obj, date_keys)
            for field, keys in keymap.items():
                if field in found:
                    continue
                v = find_by_keys(scope, keys)
                if v is not None:
                    found[field] = {"value": v, "asof": asof, "source": url.split("/")[2]}
                    got_here.append(field)
        else:
            for field, keys in keymap.items():
                if field in found:
                    continue
                v = regex_by_keys(text, keys)
                if v is not None:
                    found[field] = {"value": v, "asof": None, "source": url.split("/")[2]}
                    got_here.append(field)
        PROBE_LOG.append(f"{tag}[{i}] OK  {url} -> found {got_here or 'nothing'}"
                         f" ({'json' if obj is not None else 'html/text'})")

    out = {}
    for field in keymap:
        if field in found:
            r = found[field]
            if field == "market_cap":
                r["value"] = r["value"] * cap_scale
                r["currency"] = cap_currency
            else:
                r["value"] = round(r["value"], 2)
            if note:
                r["note"] = note
            out[field] = r
        else:
            out[field] = {"value": None,
                          "error": "ดึงข้อมูลไม่สำเร็จ / ไม่พบค่าในแหล่งข้อมูล"
                          + (f" ({'; '.join(errors)})" if errors else "")}
    return out


def multpl(path, label):
    url = f"https://www.multpl.com/{path}"
    text = get(url, headers={"Accept": "text/html"})
    save_debug(f"spx_{label}_multpl", url, text)
    m = re.search(r'id="current".*?</b>\s*([\d,]+\.?\d*)', text, re.S)
    if not m:
        raise ValueError("หาตัวเลขในหน้า multpl ไม่เจอ (โครงสร้างหน้าเว็บอาจเปลี่ยน)")
    ts = re.search(r'id="timestamp"[^>]*>\s*([^<]+?)\s*<', text)
    return {"value": round(to_num(m.group(1)), 2),
            "asof": ts.group(1) if ts else None, "source": "multpl.com"}


def todo(reason="ยังไม่มีแหล่งข้อมูล"):
    return {"value": None, "todo": True, "error": reason}


# ---------------------------------------------------------------- the list
def sse_candidates():
    """ตลาดหุ้นเซี่ยงไฮ้: สถิติรายวัน (P/E เฉลี่ย, มูลค่าตลาดรวม) ลองย้อนหลัง 7 วัน"""
    sh = datetime.datetime.now(ZoneInfo("Asia/Shanghai")).date()
    out = []
    for d in range(0, 7):
        day = (sh - datetime.timedelta(days=d)).isoformat()
        url = ("https://query.sse.com.cn/commonQuery.do?jsonCallBack=&isPagination=false"
               "&sqlId=COMMON_SSE_SJ_GPSJ_CJGK_MRGK_C&PRODUCT_CODE=01%2C02%2C03%2C11%2C17"
               f"&type=inParams&SEARCH_DATE={day}")
        out.append((url, {"Referer": "https://www.sse.com.cn/"}))
    return out


def set_warmup():
    try:
        get("https://www.set.or.th/th/home", headers={"Accept": "text/html"})
    except Exception:  # noqa: BLE001
        pass


INDICES = [
    {
        "id": "spx", "name": "S&P 500", "flag": "🇺🇸", "market": "สหรัฐฯ",
        "level": [lambda: yahoo_level("^GSPC")],
        "fund": {  # แยกทีละช่อง: ช่องไหนพัง ช่องอื่นไม่พังตาม
            "market_cap": lambda: todo("ยังไม่มีแหล่งข้อมูลฟรี (กำลังหา)"),
            "pe": lambda: multpl("s-p-500-pe-ratio", "pe"),
            "pbv": lambda: multpl("s-p-500-price-to-book", "pbv"),
        },
    },
    {
        "id": "nasdaq", "name": "NASDAQ Composite", "flag": "🇺🇸", "market": "สหรัฐฯ",
        "level": [lambda: yahoo_level("^IXIC")],
        "fund": {
            "market_cap": lambda: todo("ยังไม่มีแหล่งข้อมูลฟรี (กำลังหา)"),
            "pe": lambda: todo("ยังไม่มีแหล่งข้อมูลฟรี (กำลังหา)"),
            "pbv": lambda: todo("ยังไม่มีแหล่งข้อมูลฟรี (กำลังหา)"),
        },
    },
    {
        "id": "set", "name": "SET Index", "flag": "🇹🇭", "market": "ไทย",
        "level": [lambda: yahoo_level("^SET.BK")],
        "fund": lambda: (set_warmup(), probe_json(
            "set",
            [
                ("https://www.set.or.th/api/set/index/info/list?type=INDEX", {"Referer": "https://www.set.or.th/"}),
                ("https://www.set.or.th/api/set/market/SET/info", {"Referer": "https://www.set.or.th/"}),
                ("https://www.set.or.th/api/set/index/SET/info", {"Referer": "https://www.set.or.th/"}),
                ("https://www.set.or.th/th/market/index/set/overview", {"Accept": "text/html"}),
            ],
            {"pe": ["pe", "peRatio", "p_e"], "pbv": ["pbv", "pbvRatio", "pbRatio", "p_bv"],
             "market_cap": ["marketCap", "mktCap", "marketCapitalization"]},
            select=["SET"], cap_currency="THB"))[1],
    },
    {
        "id": "hscei", "name": "Hang Seng China Enterprises (HSCEI)", "flag": "🇭🇰", "market": "ฮ่องกง",
        "level": [lambda: yahoo_level("^HSCE")],
        "fund": lambda: probe_json(
            "hscei",
            [("https://www.hsi.com.hk/data/eng/rt/index-overview.do", {"Referer": "https://www.hsi.com.hk/"})],
            {"pe": ["peRatio", "pe", "per"], "pbv": ["pbRatio", "pb", "pbv"],
             "market_cap": ["marketCap", "mktCap", "marketCapitalization"]},
            select=["HSCE", "HSCEI", "Hang Seng China Enterprises Index"], cap_currency="HKD"),
    },
    {
        "id": "sse", "name": "SSE Composite (000001)", "flag": "🇨🇳", "market": "จีน",
        "level": [lambda: yahoo_level("000001.SS")],
        "fund": lambda: probe_json(
            "sse", sse_candidates(),
            {"pe": ["AVG_PE_RATE", "PE_RATE"], "pbv": ["PB_RATE", "AVG_PB_RATE"],
             "market_cap": ["TOTAL_VALUE", "MARKET_VALUE"]},
            cap_scale=1e8, cap_currency="CNY",  # SSE รายงานหน่วย 亿元 (ร้อยล้านหยวน)
            note="สถิติทั้งตลาดเซี่ยงไฮ้"),
    },
    {
        "id": "vni", "name": "VN-Index", "flag": "🇻🇳", "market": "เวียดนาม",
        "level": [vndirect_level, lambda: yahoo_level("^VNINDEX.VN")],
        "fund": lambda: probe_json(
            "vni",
            [("https://finfo-api.vndirect.com.vn/v4/ratios/latest?where=code:VNINDEX&order=reportDate",
              {"Referer": "https://dstock.vndirect.com.vn/"})],
            {"pe": ["PRICE_TO_EARNINGS", "PE", "pe"], "pbv": ["PRICE_TO_BOOK", "PB", "pb", "pbv"],
             "market_cap": ["MARKETCAP", "MARKET_CAP", "marketCap"]},
            cap_currency="VND"),
    },
]


# ---------------------------------------------------------------- runner
def run_level(fns, tag):
    errors = []
    for fn in fns:
        try:
            r = fn()
            if r and r.get("value") is not None:
                PROBE_LOG.append(f"{tag}.level OK via {r.get('source')}")
                return r
            errors.append("ไม่มีค่า")
        except Exception as e:  # noqa: BLE001
            errors.append(err_text(e))
    PROBE_LOG.append(f"{tag}.level FAIL {' | '.join(errors)}")
    return {"value": None, "error": "ดึงข้อมูลไม่สำเร็จ (" + " | ".join(errors) + ")"}


def run_fund(fn, tag):
    """ดึงพื้นฐาน ถ้าฟังก์ชันพังทั้งก้อน ให้ทุกช่องแสดงว่าดึงไม่สำเร็จ แต่ไม่ล้มทั้งโปรแกรม"""
    if isinstance(fn, dict):  # แบบแยกทีละช่อง
        res = {}
        for field, f in fn.items():
            try:
                r = f()
                res[field] = r
                PROBE_LOG.append(f"{tag}.{field} {'TODO' if r.get('todo') else 'OK via ' + str(r.get('source'))}")
            except Exception as e:  # noqa: BLE001
                PROBE_LOG.append(f"{tag}.{field} FAIL {err_text(e)}")
                res[field] = {"value": None, "error": "ดึงข้อมูลไม่สำเร็จ (" + err_text(e) + ")"}
        return res
    try:
        res = {}
        raw = fn()
        for field in ("market_cap", "pe", "pbv"):
            res[field] = raw.get(field) or {"value": None, "error": "ไม่พบค่า"}
        return res
    except Exception as e:  # noqa: BLE001
        PROBE_LOG.append(f"{tag}.fund FAIL {err_text(e)}")
        return {f: {"value": None, "error": "ดึงข้อมูลไม่สำเร็จ (" + err_text(e) + ")"}
                for f in ("market_cap", "pe", "pbv")}


def merge_with_previous(new, old):
    """ถ้ารอบนี้ล้มเหลวแต่รอบก่อนมีค่า -> ใช้ค่าเก่า และติดป้ายข้อมูลเก่า"""
    if new.get("value") is not None or new.get("todo"):
        return new
    if old and old.get("value") is not None:
        kept = dict(old)
        kept["stale"] = True
        kept["error"] = new.get("error")
        kept["checked_at"] = now_bkk().isoformat(timespec="minutes")
        return kept
    return new


def main():
    try:
        with open(OUT, encoding="utf-8") as f:
            previous = {i["id"]: i for i in json.load(f).get("indices", [])}
    except Exception:  # noqa: BLE001
        previous = {}

    result = []
    for idx in INDICES:
        tag = idx["id"]
        level = run_level(idx["level"], tag)

        fund = run_fund(idx["fund"], tag)

        old = previous.get(tag, {})
        entry = {
            "id": tag, "name": idx["name"], "flag": idx["flag"], "market": idx["market"],
            "level": merge_with_previous(level, old.get("level")),
        }
        for f in ("market_cap", "pe", "pbv"):
            entry[f] = merge_with_previous(fund[f], old.get(f))
        result.append(entry)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"updated_at": now_bkk().isoformat(timespec="minutes"),
                   "indices": result}, f, ensure_ascii=False, indent=2)

    os.makedirs(DEBUG_DIR, exist_ok=True)
    with open(os.path.join(DEBUG_DIR, "_summary.txt"), "w", encoding="utf-8") as f:
        f.write(f"run at {now_bkk().isoformat()}\n\n" + "\n".join(PROBE_LOG) + "\n")
    print("\n".join(PROBE_LOG))


if __name__ == "__main__":
    main()
