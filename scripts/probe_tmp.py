import urllib.request, re, os, io, json
from pypdf import PdfReader
OUT="data/debug/probe_inv"; os.makedirs(OUT, exist_ok=True)
B={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36","Accept":"*/*"}
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers=B),timeout=90) as r: return r.read()
out=[]
for name,url in [("ir_dates","https://www.msci.com/eqb/pressreleases/archive/ir_dates.pdf"),
                 ("st_nov26","https://www.msci.com/eqb/gimi/stdindex/MSCI_Nov26_STPublicList.pdf"),
                 ("sc_nov26","https://www.msci.com/eqb/gimi/smallcap/MSCI_Nov26_SCPublicList.pdf")]:
    try:
        b=get(url); txt="\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(b)).pages)
        open(f"{OUT}/{name}.txt","w").write(txt[:200000])
        i=txt.find("THAILAND")
        out.append(f"OK {name} pages_len={len(txt)} thai_at={i} :: {txt[:600]}\n--- THAI ---\n{txt[i-200:i+1500] if i>=0 else ''}")
    except Exception as e: out.append(f"FAIL {name} {e}")
open(f"{OUT}/msci.txt","w").write("\n\n".join(out)); print("OK")
