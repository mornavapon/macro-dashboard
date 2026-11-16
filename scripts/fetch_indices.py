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


def norm_date(v):
    """แปลง 20261116 -> 2026-11-16 (ถ้าเป็นรูปแบบอื่นคืนค่าเดิม)"""
    if v is None:
        return None
    v = str(v).strip()
    if re.fullmatch(r"\d{8}", v):
        return f"{v[:4]}-{v[4:6]}-{v[6:]}"
    if re.match(r"\d{4}-\d{2}-\d{2}T", v):
        return v[:10]
    return v


def strip_tags(html):
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text)


SANE = {"pe": (3, 60), "pbv": (0.3, 10)}  # กันตัวเลขผิดที่ regex ไปจับมั่ว


def html_probe(tag, url, patterns, headers=None, cap_scale=1.0, cap_currency=None,
               asof_regex=None, note=None, source=None, discover=None,
               decimal_comma=False):
    """
    ดึงหน้าเว็บ (HTML) แล้วหาตัวเลขด้วย regex จากข้อความที่ตัด tag ออกแล้ว
    patterns: {"pe": r"...(ตัวเลข)", ...}
    discover: regex สำหรับเก็บ URL ของ API ที่ซ่อนอยู่ในหน้า (เพื่อใช้ปรับปรุงรอบหน้า)
    """
    html = get(url, headers=headers or {"Accept": "text/html"})
    text = strip_tags(html)
    save_debug(f"{tag}_html", url, text)
    if discover:
        found_urls = sorted(set(re.findall(discover, html)))[:200]
        save_debug(f"{tag}_discover", url, "\n".join(found_urls))
    asof = None
    if asof_regex:
        m = re.search(asof_regex, text)
        asof = m.group(1) if m else None
    out = {}
    for field, rx in patterns.items():
        m = re.search(rx, text)
        if not m or to_num(m.group(1)) is None:
            out[field] = {"value": None, "error": "ดึงข้อมูลไม่สำเร็จ / หาตัวเลขในหน้าเว็บไม่เจอ"}
            continue
        raw = m.group(1)
        if decimal_comma:  # รูปแบบเวียดนาม 13,4 = 13.4
            raw = raw.replace(".", "").replace(",", ".")
        v = to_num(raw)
        if v is None:
            out[field] = {"value": None, "error": "อ่านตัวเลขไม่ได้"}
            continue
        if field in SANE and not (SANE[field][0] <= v <= SANE[field][1]):
            out[field] = {"value": None, "error": f"ค่าที่เจอ ({v}) ดูผิดปกติ จึงไม่ใช้"}
            continue
        r = {"value": v * cap_scale if field == "market_cap" else round(v, 2),
             "asof": asof, "source": source or url.split("/")[2]}
        if field == "market_cap":
            r["currency"] = cap_currency
        if note:
            r["note"] = note
        out[field] = r
    PROBE_LOG.append(f"{tag} html {url} -> found {[k for k, v in out.items() if v.get('value') is not None] or 'nothing'}")
    return out


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
               cap_currency=None, date_keys=None, note=None, stop_on_hit=False,
               todo_fields=None):
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
        if stop_on_hit and found:
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
                    found[field] = {"value": v, "asof": norm_date(asof), "source": url.split("/")[2]}
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
    for field in todo_fields or []:
        out[field] = todo("แหล่งข้อมูลนี้ไม่มีค่านี้")
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


def first_ok(*fns, todo_fields=()):
    """ลองหลายแหล่งตามลำดับ ช่องไหนได้จากแหล่งแรกแล้ว ไม่ต้องใช้แหล่งถัดไป"""
    res = {}
    errs = []
    for fn in fns:
        try:
            r = fn()
        except Exception as e:  # noqa: BLE001
            errs.append(err_text(e))
            PROBE_LOG.append(f"  source FAIL {err_text(e)}")
            continue
        for k, v in r.items():
            if k not in res or (res[k].get("value") is None and v.get("value") is not None):
                res[k] = v
    for f in todo_fields:
        res[f] = todo("ยังไม่มีแหล่งข้อมูลฟรี")
    for f in ("market_cap", "pe", "pbv"):
        if f not in res:
            res[f] = {"value": None, "error": "ดึงข้อมูลไม่สำเร็จ (" + " | ".join(errs) + ")"}
    return res


NUM = r"(-?[\d,]+(?:\.\d+)?)"

INDICES = [
    {
        "id": "spx", "name": "S&P 500", "flag": "🇺🇸", "market": "สหรัฐฯ",
        "level": [lambda: yahoo_level("^GSPC")],
        "fund": {  # แยกทีละช่อง: ช่องไหนพัง ช่องอื่นไม่พังตาม
            "market_cap": lambda: todo("ยังไม่มีแหล่งข้อมูลฟรี"),
            "pe": lambda: multpl("s-p-500-pe-ratio", "pe"),
            "pbv": lambda: multpl("s-p-500-price-to-book", "pbv"),
        },
    },
    {
        "id": "nasdaq", "name": "NASDAQ Composite", "flag": "🇺🇸", "market": "สหรัฐฯ",
        "level": [lambda: yahoo_level("^IXIC")],
        "fund": {
            "market_cap": lambda: todo("ยังไม่มีแหล่งข้อมูลฟรี"),
            "pe": lambda: todo("ยังไม่มีแหล่งข้อมูลฟรี"),
            "pbv": lambda: todo("ยังไม่มีแหล่งข้อมูลฟรี"),
        },
    },
    {
        "id": "set", "name": "SET Index", "flag": "🇹🇭", "market": "ไทย",
        "level": [lambda: yahoo_level("^SET.BK")],
        # หน้า "Key Market Statistics" ของ SET (ตลาด SET ไม่รวม mai)
        "fund": lambda: first_ok(
            lambda: html_probe(
                "set_en", "https://www.set.or.th/en/market/product/stock/overview",
                {"market_cap": r"Market Cap\.?\s*\(M\.\s*Baht\)\s*" + NUM,
                 "pe": r"P/E\s*\(times\)\s*" + NUM,
                 "pbv": r"P/BV\s*\(times\)\s*" + NUM},
                cap_scale=1e6, cap_currency="THB",
                asof_regex=r"As of\s+(\d{1,2}\s+\w{3}\s+\d{4})",
                discover=r"/api/set/[A-Za-z0-9/_\-?=&.{}$]+"),
            lambda: html_probe(
                "set_th", "https://www.set.or.th/th/market/product/stock/overview",
                {"market_cap": r"มูลค่าหลักทรัพย์ตามราคาตลาด\s*\(ล้านบาท\)\s*" + NUM,
                 "pe": r"P/E\s*\(เท่า\)\s*" + NUM,
                 "pbv": r"P/BV\s*\(เท่า\)\s*" + NUM},
                cap_scale=1e6, cap_currency="THB",
                asof_regex=r"ข้อมูล ณ วันที่\s*(\d{1,2}\s*\S+\s*\d{4})"),
        ),
    },
    {
        "id": "hscei", "name": "Hang Seng China Enterprises (HSCEI)", "flag": "🇭🇰", "market": "ฮ่องกง",
        "level": [lambda: yahoo_level("^HSCE")],
        "fund": lambda: first_ok(
            # หน้าเว็บทางการของ Hang Seng Indexes (เก็บ URL API ที่ซ่อนอยู่ไว้ดูด้วย)
            lambda: html_probe(
                "hscei_hsi", "https://www.hsi.com.hk/en/indexes/all-indexes/hscei",
                {"pe": r"P/E\s*Ratio[^0-9]{0,40}" + NUM,
                 "pbv": r"P/B[^0-9]{0,40}" + NUM},
                discover=r"(?:https?://[a-z.]*hsi\.com\.hk)?/data/[A-Za-z0-9/_\-?=&.]+"),
            # สำรอง: P/E ของ ETF 2828 ที่ลอกตามดัชนี HSCEI
            lambda: html_probe(
                "hscei_etf", "https://stockanalysis.com/quote/hkg/2828/",
                {"pe": r"PE Ratio\s*" + NUM},
                note="อ้างอิง ETF 2828", source="stockanalysis.com"),
            todo_fields=("market_cap",),
        ),
    },
    {
        "id": "sse", "name": "SSE Composite (000001)", "flag": "🇨🇳", "market": "จีน",
        "level": [lambda: yahoo_level("000001.SS")],
        "fund": lambda: probe_json(
            "sse", sse_candidates(),
            {"pe": ["AVG_PE_RATE"], "market_cap": ["TOTAL_VALUE"]},
            select=["17"],            # PRODUCT_CODE 17 = หุ้นทั้งหมดในตลาดเซี่ยงไฮ้
            cap_scale=1e8, cap_currency="CNY",  # หน่วย 亿元 (ร้อยล้านหยวน)
            note="สถิติทั้งตลาดเซี่ยงไฮ้", stop_on_hit=True, todo_fields=["pbv"]),
    },
    {
        "id": "vni", "name": "VN-Index", "flag": "🇻🇳", "market": "เวียดนาม",
        "level": [lambda: yahoo_level("^VNINDEX.VN"), vndirect_level],
        "fund": lambda: first_ok(
            lambda: html_probe(
                "vni_simplize", "https://simplize.vn/chi-so/VNINDEX",
                {"pe": r"P/E[^0-9]{0,30}" + NUM,
                 "pbv": r"P/B[^0-9]{0,30}" + NUM},
                discover=r"https?://api[a-z0-9.\-]*/[A-Za-z0-9/_\-?=&.]+", decimal_comma=True),
            lambda: html_probe(
                "vni_24h", "https://24hmoney.vn/indices/vn-index",
                {"pe": r"P/E[^0-9]{0,30}" + NUM,
                 "pbv": r"P/B[^0-9]{0,30}" + NUM},
                discover=r"https?://api[a-z0-9.\-]*/[A-Za-z0-9/_\-?=&.]+", decimal_comma=True),
            todo_fields=("market_cap",),
        ),
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
