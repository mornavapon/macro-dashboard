import urllib.request, re, os, io, json
from pypdf import PdfReader
OUT="data/debug/probe_fill"; os.makedirs(OUT, exist_ok=True)
B={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36","Accept":"*/*"}
def get(url,binary=False):
    with urllib.request.urlopen(urllib.request.Request(url,headers=B),timeout=60) as r:
        b=r.read(); return b if binary else b.decode("utf-8","replace")
s=[]
for name,url in [("sa_sp500","https://stockanalysis.com/list/sp-500-stocks/"),("sa_nasdaq","https://stockanalysis.com/list/nasdaq-stocks/"),
                 ("sa_api1","https://stockanalysis.com/api/screener/s/f?m=marketCap&s=desc&c=s,marketCap,pbRatio,peRatio&f=exchange-is-NASDAQ&i=stocks"),
                 ("sa_api2","https://api.stockanalysis.com/api/screener/s/f?m=marketCap&s=desc&c=s,marketCap,pbRatio,peRatio&f=exchange-is-NASDAQ&i=stocks")]:
    try:
        t=get(url); n=len(re.findall(r'marketCap',t))
        i=t.find('marketCap'); open(f"{OUT}/{name}.txt","w").write(f"LEN {len(t)} count={n}\n"+t[max(0,i-1500):i+3000])
        s.append(f"{name}: OK len={len(t)} marketCap={n}")
    except Exception as e: s.append(f"{name}: FAIL {e}")
for name,url in [("hscei_fs","https://www.hsi.com.hk/static/uploads/contents/en/dl_centre/factsheets/hsceie.pdf"),
                 ("hsi_fs","https://www.hsi.com.hk/static/uploads/contents/en/dl_centre/factsheets/hsie.pdf")]:
    try:
        b=get(url,binary=True); txt="\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(b)).pages)
        open(f"{OUT}/{name}.txt","w").write(txt[:15000]); s.append(f"{name}: OK pdf")
    except Exception as e: s.append(f"{name}: FAIL {e}")
open(f"{OUT}/_summary2.txt","w").write("\n".join(s)); print("\n".join(s))
