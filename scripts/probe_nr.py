"""ชั่วคราว: ดูว่าหน้า Non-resident Flows ของ ThaiBMA โหลดข้อมูลจาก API อะไร"""
from playwright.sync_api import sync_playwright
PAGES = ["https://www.thaibma.or.th/EN/Market/NR/NRDaily.aspx",
         "https://www.thaibma.or.th/EN/Market/NR/NRMonthly.aspx",
         "https://www.thaibma.or.th/EN/Market/NR/NRYearly.aspx",
         "https://www.thaibma.or.th/EN/Market/Outstanding/Outstanding.aspx"]
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    seen = []
    def on_resp(r):
        if r.request.resource_type in ("xhr", "fetch"):
            try: body = r.text()[:700]
            except Exception as e: body = f"<{e}>"
            seen.append((r.status, r.request.method, r.url, r.request.post_data, body))
    pg.on("response", on_resp)
    for u in PAGES:
        seen.clear()
        try:
            resp = pg.goto(u, wait_until="networkidle", timeout=60000)
            print(f"\n##### {u} -> {resp.status if resp else None}")
            pg.wait_for_timeout(3000)
            print("TEXT:", pg.inner_text("body")[:1500].replace("\n", " | "))
        except Exception as e:
            print(f"\n##### {u} FAIL {e}")
        for s in seen:
            print("XHR", s[0], s[1], s[2], "POST=", (s[3] or "")[:200]); print("   ", s[4].replace("\n", " ")[:700])
        links = pg.eval_on_selector_all("a[href*='NR'], a[href*='Outstanding'], a[href*='Foreign']", "els=>els.map(e=>e.href)")
        print("LINKS", sorted(set(links))[:40])
    b.close()
