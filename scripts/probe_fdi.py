import io, os, urllib.request
from pypdf import PdfReader
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "*/*"}), timeout=60).read()
os.makedirs("data/debug", exist_ok=True)
u = "https://www.boi.go.th/upload/content/FDI%20Q3%202026%20final_6af29e7b03bdb.pdf"
t = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(get(u))).pages)
open("data/debug/boi_fdi_q3_2026.txt", "w").write(t)
print("BOI chars", len(t))
out = []
for y in (2023, 2024, 2025, 2026):
    for m in (3, 6, 9, 12):
        u = f"https://www.bot.or.th/content/dam/bot/documents/en/thai-economy/state-of-thai-economy/monthly-report/macro-{y}-{m:02d}-table_q.pdf"
        try:
            t = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(get(u))).pages)
            lines = [l for l in t.splitlines() if "FDI" in l or "Quarter" in l or "Table Attached" in l]
            out.append(f"OK {y}-{m:02d}\n" + "\n".join(lines[:8]))
        except Exception as e:
            out.append(f"x {y}-{m:02d} {e}")
open("data/debug/bot_fdi_probe.txt", "w").write("\n\n".join(out))
print("\n".join(out))
