"""ชั่วคราว: หาแหล่ง BOI FDI report และ BOT macro table"""
import io, re, urllib.request, urllib.parse
from pypdf import PdfReader
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
def get(u, b=False):
    r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "*/*"}), timeout=40)
    d = r.read(); return d if b else d.decode("utf-8", "replace")

print("##### BOT")
for lang, yrs in (("en", [2026]), ("th", [2569])):
    for y in yrs:
        for m in range(11, 0, -1):
            for kind in ("table_q", "table_m"):
                u = f"https://www.bot.or.th/content/dam/bot/documents/{lang}/thai-economy/state-of-thai-economy/monthly-report/macro-{y}-{m:02d}-{kind}.pdf"
                try:
                    pdf = get(u, True)
                    t = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)
                    print("OK", u, len(pdf))
                    for line in t.splitlines():
                        if re.search(r"FDI|Direct|โดยตรง|Quarter|ไตรมาส|^\s*20\d\d|25\d\d", line):
                            print("   ", line[:220])
                    raise StopIteration
                except StopIteration:
                    break
                except Exception as e:
                    print("x", u.rsplit("/",1)[1], type(e).__name__, str(e)[:60])
            else:
                continue
            break

print("\n##### BOI")
cands = ["https://www.boi.go.th/", "https://www.boi.go.th/index.php?page=statistics_fdi&language=th",
         "https://www.boi.go.th/index.php?page=statistics_foreign_direct_investment&language=th",
         "https://www.boi.go.th/index.php?page=foreign_direct_investment&language=th",
         "https://www.boi.go.th/index.php?page=statistics&language=th",
         "https://www.boi.go.th/th/statistics", "https://www.boi.go.th/en/statistics"]
seen = set()
for u in cands:
    try:
        h = get(u)
        links = set(re.findall(r'href="([^"]+)"', h))
        fdi = [l for l in links if re.search(r"FDI|Foreign|statist|สถิติ", l, re.I)]
        print("OK", u, len(h), "links", len(links)); [print("   ", l) for l in sorted(fdi)[:40]]
        for l in fdi:
            seen.add(urllib.parse.urljoin(u, l))
    except Exception as e:
        print("x", u, type(e).__name__, str(e)[:80])
for u in sorted(seen)[:25]:
    if u.endswith(".pdf"): continue
    try:
        h = get(u)
        pdfs = sorted(set(re.findall(r'(?:href|src)="([^"]*?\.pdf)"', h, re.I)))
        f = [p for p in pdfs if re.search(r"FDI|Q[1-4]|20[2-3]\d", p)]
        print("PAGE", u, "pdfs", len(pdfs)); [print("   ", p) for p in f[:15]]
    except Exception as e:
        print("x", u, type(e).__name__)
