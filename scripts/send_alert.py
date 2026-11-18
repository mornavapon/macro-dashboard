#!/usr/bin/env python3
"""
ส่งแจ้งเตือนเข้า ntfy ล่วงหน้า 1 วัน ก่อนวันประกาศตัวเลขเศรษฐกิจ

วิธีใช้:  python3 scripts/send_alert.py <หัวข้อ> [--test]
  หัวข้อ: us_gdp, us_cpi
  --test : ส่งข้อความทดสอบทันที (ใช้ตรวจว่ามือถือได้รับ)

อ่านตารางวันประกาศจาก data/us.json (ตัวดึงข้อมูลหน้า 2 เป็นคนอัปเดต)
ไม่ต้องต่อเน็ตไปไหนนอกจาก ntfy -> ถ้าเว็บแหล่งข้อมูลล่ม แจ้งเตือนยังทำงานได้จากตารางล่าสุด
ชื่อช่อง ntfy อ่านจาก Secret ชื่อ NTFY_TOPIC_MACRO (ไม่เขียนไว้ใน repo เพราะ repo เป็น Public)
"""
import datetime
import json
import os
import sys
import urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BKK = ZoneInfo("Asia/Bangkok")
SITE = "https://mornavapon.github.io/macro-dashboard/"

TOPICS = {
    "us_gdp": {"file": "us.json", "release": "gdp", "data": "gdp", "tag": "us",
               "link": "https://www.investing.com/economic-calendar/gdp-375"},
    "us_cpi": {"file": "us.json", "release": "cpi", "data": "cpi", "tag": "us",
               "link": "https://th.investing.com/economic-calendar/cpi-733"},
    "th_mpc": {"file": "th.json", "release": "mpc", "data": "mpc", "tag": "thailand",
               "link": "https://www.bot.or.th/th/our-roles/monetary-policy/mpc-meeting.html"},
    # เงินเฟ้อไทยไม่มีปฏิทินประกาศล่วงหน้าที่ดึงได้ -> แจ้ง "วันที่ตัวเลขออก" แทน (ดู th_cpi_new)
    "th_gdp": {"file": "th.json", "release": None, "data": "gdp", "tag": "thailand",
               "link": "https://www.nesdc.go.th/info/economic-aspect/"},
    "th_export": {"file": "th.json", "release": None, "data": "exports", "tag": "thailand",
                  "link": "https://tradereport.moc.go.th/th/stat/reportmonth01"},
    "th_cpi": {"file": "th.json", "release": None, "data": "cpi", "tag": "thailand",
               "link": "https://index.tpso.go.th/cpi"},
}

TH_DOW = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]
TH_MON = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]


def thai_date(iso):
    d = datetime.date.fromisoformat(iso[:10])
    return f"วัน{TH_DOW[d.weekday()]}ที่ {d.day} {TH_MON[d.month]} {d.year + 543}"


def previous_value(key, data):
    try:
        if key == "us_gdp":
            r = data["gdp"]["rows"][0]
            return f"ครั้งล่าสุด: {r['quarter']} โต {r['growth']}% (QoQ ปรับเป็นรายปี)"
        if key == "th_mpc":
            return f"ดอกเบี้ยนโยบายปัจจุบัน: {data['mpc']['current']:.2f}%"
        if key == "us_cpi":
            r = next(x for x in data["cpi"]["rows"] if x.get("yoy") is not None)
            return f"ครั้งล่าสุดที่มีตัวเลข: เดือน {r['month']} = {r['yoy']}% YoY"
    except Exception:  # noqa: BLE001
        pass
    return ""


def send(title, message, link, tags):
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        sys.exit("ไม่พบ Secret NTFY_TOPIC_MACRO -> ไปตั้งที่ Settings > Secrets and variables > Actions")
    body = json.dumps({"topic": topic, "title": title, "message": message,
                       "tags": tags, "click": link,
                       "actions": [{"action": "view", "label": "ดูข้อมูล", "url": link},
                                   {"action": "view", "label": "เปิดเว็บแอป", "url": SITE}]}).encode()
    req = urllib.request.Request("https://ntfy.sh/", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        print("ntfy:", r.status)


def th_cpi_new(cfg, test):
    """เงินเฟ้อไทย: แจ้งเมื่อ สนค. อัปเดตตัวเลขเดือนใหม่ในวันนี้"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fetch_th  # noqa: E402
    master = json.loads(fetch_th.get(fetch_th.TPSO + "/api/cpig/master",
                                     headers={"Accept": "application/json"}))
    upd = datetime.datetime.fromisoformat(master["lastUpdated"].replace("Z", "+00:00")).astimezone(BKK)
    today = datetime.datetime.now(BKK).date()
    end = master["period"]["end"]
    if not test and upd.date() != today:
        print(f"th_cpi: วันนี้ยังไม่มีตัวเลขใหม่ (อัปเดตล่าสุด {upd.date()})")
        return
    r = fetch_th.tpso_change(end["year"], end["month"], max(master.get("yearBase") or [2566]))
    mon = f"{TH_MON[end['month']]} {end['year']}"
    msg = (f"เงินเฟ้อทั่วไปเดือน {mon}: {r['changeYear']:+.2f}% (YoY)\n"
           f"เทียบเดือนก่อน: {r['change']:+.2f}% (MoM)\n"
           f"เฉลี่ยตั้งแต่ต้นปี: {r['changeAvg']:+.2f}%")
    title = ("[ทดสอบ] " if test else "") + f"เงินเฟ้อไทย {mon} ออกแล้ว"
    send(title, msg, cfg["link"], ["chart_with_upwards_trend", cfg["tag"]])


def th_gdp_new(cfg, test):
    """GDP ไทย: แจ้งเมื่อ สศช. อัปโหลดไฟล์ GDP ไตรมาสใหม่ในวันนี้"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fetch_th  # noqa: E402
    g = fetch_th.build_gdp()
    today = datetime.datetime.now(BKK).date().isoformat()
    if not test and g["release_date"] != today:
        print(f"th_gdp: วันนี้ยังไม่มีตัวเลขใหม่ (ไฟล์ล่าสุด {g['release_date']})")
        return
    r = g["rows"][0]
    q = f"Q{r['q']}/{r['year'] + 543}"
    msg = (f"GDP ไทย {q}\n"
           f"เทียบไตรมาสก่อน (ปรับฤดูกาล): {r['growth']:+.1f}%\n"
           f"เทียบไตรมาสเดียวกันปีก่อน: {r['yoy']:+.1f}%")
    if r.get("size_mb"):
        msg += f"\nขนาด GDP ไตรมาสนี้: {r['size_mb'] / 1e6:.2f} ล้านล้านบาท"
    title = ("[ทดสอบ] " if test else "") + f"GDP ไทย {q} ออกแล้ว"
    send(title, msg, cfg["link"], ["chart_with_upwards_trend", cfg["tag"]])


STATE = os.path.join(ROOT, "data", "alert_state.json")


def th_export_new(cfg, test):
    """ส่งออกไทย: แจ้งเมื่อกระทรวงพาณิชย์มีข้อมูลเดือนใหม่ (จำเดือนที่แจ้งไปแล้วใน data/alert_state.json)"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fetch_th  # noqa: E402
    y, m = fetch_th.trade_latest_month()
    key = f"{y}-{m:02d}"
    try:
        with open(STATE, encoding="utf-8") as f:
            state = json.load(f)
    except Exception:  # noqa: BLE001
        state = {}
    if not test and state.get("th_export") == key:
        print(f"th_export: ยังไม่มีเดือนใหม่ (ล่าสุด {key})")
        return
    cur, prev = fetch_th.trade_month_total(y, m), fetch_th.trade_month_total(y - 1, m)
    yoy = (cur["value_usd_export"] / prev["value_usd_export"] - 1) * 100
    ytd = (cur["acc_value_usd_export"] / prev["acc_value_usd_export"] - 1) * 100
    mon = f"{TH_MON[m]} {y + 543}"
    msg = (f"มูลค่าส่งออก {mon}: {cur['value_usd_export'] / 1e6:,.1f} ล้านดอลลาร์\n"
           f"เทียบปีก่อน: {yoy:+.1f}% (YoY)\n"
           f"สะสมตั้งแต่ต้นปี: {ytd:+.1f}%\n"
           f"ดุลการค้า: {cur['value_usd_balance'] / 1e6:+,.1f} ล้านดอลลาร์")
    title = ("[ทดสอบ] " if test else "") + f"ส่งออกไทย {mon} ออกแล้ว"
    send(title, msg, cfg["link"], ["ship", cfg["tag"]])
    if not test:
        state["th_export"] = key
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)


def msci_alert(test):
    """MSCI: แจ้ง 1 วันก่อนวันประกาศผล และ 1 วันก่อนวันปรับพอร์ตจริง"""
    with open(os.path.join(ROOT, "data", "msci.json"), encoding="utf-8") as f:
        d = json.load(f)
    link = "https://mornavapon.github.io/macro-dashboard/"
    latest, reviews = d.get("latest") or {}, [r for r in [d.get("latest")] + (d.get("schedule") or []) if r]
    today = datetime.datetime.now(BKK).date()
    tomorrow = (today + datetime.timedelta(days=1)).isoformat()

    def changes_text(r):
        if not r.get("ok"):
            return "ยังดึงรายชื่อหุ้นไม่ได้ ดูในเว็บแอป"
        lines = []
        for key, label in (("standard", "ดัชนีหลัก (Standard)"), ("smallcap", "หุ้นขนาดเล็ก (Small Cap)")):
            sec = r.get(key) or {}
            lines.append(f"{label}\n  ➕ {', '.join(sec.get('add') or []) or 'ไม่มี'}\n  ➖ {', '.join(sec.get('delete') or []) or 'ไม่มี'}")
        return "\n".join(lines)

    if test:
        nxt = d.get("next") or {}
        send("[ทดสอบ] แจ้งเตือน MSCI",
             f"✅ ทดสอบสำเร็จ\n\nรอบล่าสุด: {latest.get('review', '-')}\n{changes_text(latest)}\n\n"
             f"รอบถัดไป: {nxt.get('review', '-')} ประกาศ {thai_date(nxt['announce_thai'])}" if nxt else "✅ ทดสอบสำเร็จ",
             link, ["test_tube", "thailand"])
        return
    sent = False
    for r in reviews:
        ann_thai = datetime.datetime.fromisoformat(r["announce_thai"])
        if r["announce_cet"] == today.isoformat():
            send(f"คืนนี้ MSCI ประกาศผลทบทวน {r['review']}",
                 f"📅 ประกาศหลัง 23:00 น. เวลายุโรป = {ann_thai.strftime('%H:%M')} น. {thai_date(ann_thai.date().isoformat())} (เวลาไทย)\n"
                 f"🔁 ปรับพอร์ตจริง: ปิดตลาด{thai_date(r['trade_close'])}", link, ["calendar", "thailand"])
            sent = True
        if r["trade_close"] == tomorrow:
            body = f"🔁 พรุ่งนี้ ({thai_date(r['trade_close'])}) กองทุนปรับพอร์ตตาม MSCI ช่วงปิดตลาด มักมีแรงซื้อขายหนัก\n\n"
            if r.get("review") == latest.get("review"):
                body += "หุ้นไทยที่ปรับรอบนี้\n" + changes_text(latest)
            send(f"พรุ่งนี้ MSCI ปรับพอร์ตจริง ({r['review']})", body, link, ["warning", "thailand"])
            sent = True
    if not sent:
        print("msci: วันนี้ไม่มีอะไรต้องแจ้ง")


def main():
    key = sys.argv[1]
    test = "--test" in sys.argv
    if key == "msci":
        msci_alert(test)
        return
    cfg = TOPICS[key]
    if key == "th_cpi":
        th_cpi_new(cfg, test)
        return
    if key == "th_gdp":
        th_gdp_new(cfg, test)
        return
    if key == "th_export":
        th_export_new(cfg, test)
        return
    with open(os.path.join(ROOT, "data", cfg["file"]), encoding="utf-8") as f:
        data = json.load(f)
    rel = (data.get("releases") or {}).get(cfg["release"]) or {}
    items = rel.get("items") or []
    tomorrow = (datetime.datetime.now(BKK).date() + datetime.timedelta(days=1)).isoformat()

    if test:
        nxt = items[0] if items else None
        msg = "✅ ทดสอบแจ้งเตือนสำเร็จ\n\n"
        msg += (f"ครั้งถัดไป: {nxt['title']}\n{thai_date(nxt['thai_date'])} เวลา {nxt['thai_time']} น. (ไทย)"
                if nxt else "ยังไม่มีตารางวันประกาศครั้งถัดไป")
        send(f"[ทดสอบ] แจ้งเตือน {key}", msg, cfg["link"], ["test_tube", cfg["tag"]])
        return

    due = [r for r in items if r["thai_date"] == tomorrow]
    if not due:
        print(f"{key}: พรุ่งนี้ ({tomorrow}) ไม่มีประกาศ")
        if not items:
            print("คำเตือน: ไม่มีตารางวันประกาศเหลืออยู่เลย")
        return
    for r in due:
        msg = (f"📅 {thai_date(r['thai_date'])}\n"
               f"🕗 เวลา {r['thai_time']} น. (เวลาไทย)\n\n"
               f"{previous_value(key, data)}")
        send(f"พรุ่งนี้ประกาศ: {r['title']}", msg.strip(), cfg["link"], ["calendar", cfg["tag"]])


if __name__ == "__main__":
    main()
