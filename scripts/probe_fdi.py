import re, urllib.request
from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
r = urllib.request.urlopen(urllib.request.Request("https://www.boi.go.th/", headers={"User-Agent": UA}), timeout=30)
print("RAW212:", r.read().decode("utf-8", "replace")[:400])
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(user_agent=UA, locale="th-TH"); pg = ctx.new_page()
    for u in ["https://www.boi.go.th/", "https://www.boi.go.th/index.php?page=statistics_investment&language=th",
              "https://www.boi.go.th/index.php?page=fdi_statistics&language=th"]:
        try:
            pg.goto(u, wait_until="networkidle", timeout=60000); pg.wait_for_timeout(3000)
            links = pg.eval_on_selector_all("a", "els=>els.map(e=>[e.innerText.trim().slice(0,60), e.href])")
            print("\n#####", u, "->", pg.url, "title:", pg.title(), "links", len(links))
            for t, h in links:
                if re.search(r"สถิติ|statist|FDI|ต่างประเทศ|Foreign", t + h, re.I):
                    print("   ", t, "|", h)
        except Exception as e:
            print("x", u, e)
    # follow statistics links once
    cand = [h for t, h in pg.eval_on_selector_all("a", "els=>els.map(e=>[e.innerText, e.href])") if re.search(r"statist|สถิติ", t + h, re.I)]
    for u in list(dict.fromkeys(cand))[:8]:
        try:
            pg.goto(u, wait_until="networkidle", timeout=60000); pg.wait_for_timeout(2000)
            pdfs = pg.eval_on_selector_all("a[href$='.pdf'], a[href*='.pdf']", "els=>els.map(e=>[e.innerText.trim().slice(0,60), e.href])")
            print("\nPAGE", u, "pdfs", len(pdfs))
            for t, h in pdfs[:20]:
                print("   ", t, "|", h)
        except Exception as e:
            print("x", u, e)
    b.close()
