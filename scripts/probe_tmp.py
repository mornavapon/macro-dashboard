import urllib.request, re, os, http.cookiejar, json
OUT="data/debug/probe_ex"; os.makedirs(OUT, exist_ok=True)
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
B={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36","Accept":"application/json, text/plain, */*","Accept-Language":"th,en","X-Requested-With":"XMLHttpRequest"}
def get(url):
    with op.open(urllib.request.Request(url,headers=B),timeout=60) as r: return r.read().decode("utf-8","replace"), r.headers.get("Content-Type")
out=[]
js,_=get("https://tradereport.moc.go.th/js/app.js")
for k in ["/api/summarycountries","/home/summary/result","report-month01","opendata-summary"]:
    for m in list(re.finditer(re.escape(k),js))[:3]: out.append(f"## {k}\n"+js[max(0,m.start()-1500):m.end()+1500])
for q in ["/api/summarycountries","/api/summarycountries?year=2026&month=9","/api/summarycountries?year=2569&month=9","/home/summary/result"]:
    try: b,ct=get("https://tradereport.moc.go.th"+q); out.append(f"Q {q} ct={ct} len={len(b)} :: {b[:1500]}")
    except Exception as e:
        try: msg=e.read().decode()[:500]
        except Exception: msg=""
        out.append(f"Q {q} FAIL {e} {msg}")
open(f"{OUT}/probe7.txt","w").write("\n\n".join(out)[:200000]); print("OK")
