import urllib.request, re, os, http.cookiejar, json
OUT="data/debug/probe_inv"; os.makedirs(OUT, exist_ok=True)
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
B={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36","Accept":"application/json, text/plain, */*","Accept-Language":"th,en;q=0.9","Referer":"https://www.set.or.th/th/market/statistics/investor-type"}
def get(url):
    with op.open(urllib.request.Request(url,headers=B),timeout=60) as r: return r.read().decode("utf-8","replace")
out=[]
try: get("https://www.set.or.th/th/market/statistics/investor-type")
except Exception as e: out.append(f"warm FAIL {e}")
base="https://www.set.or.th/api/set/market/SET/"
for p in ["investor-type","investor-type?type=M","investor-type?type=Y","investor-type?type=D","investor-type?period=M",
          "investor-type-summary","investor-type-average","investor-type-chart?period=1Y","investor-type-remark"]:
    try: t=get(base+p); out.append(f"OK {p} :: {t[:2500]}")
    except Exception as e: out.append(f"FAIL {p} {e}")
open(f"{OUT}/probe2.txt","w").write("\n\n".join(out)[:100000]); print("OK")
