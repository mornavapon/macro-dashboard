import urllib.request, urllib.parse, re, os, http.cookiejar, json
OUT="data/debug/probe_ex"; os.makedirs(OUT, exist_ok=True)
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
B={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36","Accept":"application/json, text/plain, */*","Accept-Language":"th,en","X-Requested-With":"XMLHttpRequest","Referer":"https://tradereport.moc.go.th/th"}
def req(url,data=None,h=None):
    hh=dict(B); hh.update(h or {})
    with op.open(urllib.request.Request(url,headers=hh,data=data),timeout=60) as r: return r.read().decode("utf-8","replace"), r.headers.get("Content-Type")
out=[]
home,_=req("https://tradereport.moc.go.th/th")
tok=re.search(r'name="csrf-token" content="([^"]+)"',home); tok=tok.group(1) if tok else ""
out.append("TOKEN "+tok[:10]+" homecomp "+str(re.findall(r'<(home-[a-z\-]+|summary[a-z\-]*)[^>]*>',home)[:10]))
for q in ["?year=2026&month=9&limit=0","?year=2026&month=9&limit=5","?year=2026&month=8&limit=5","?year=2025&month=12&limit=5"]:
    try: b,ct=req("https://tradereport.moc.go.th/api/summarycountries"+q); out.append(f"GET {q} len={len(b)} :: {b[:800]}")
    except Exception as e: out.append(f"GET {q} FAIL {e}")
js,_=req("https://tradereport.moc.go.th/js/app.js")
for m in list(re.finditer(r'/home/summary/result',js))[:2]: out.append("JS SUMMARY "+js[max(0,m.start()-1200):m.end()+800])
for body in [{"year":2026,"month":9},{"year":"2026","month":"9"}]:
    try:
        b,ct=req("https://tradereport.moc.go.th/home/summary/result",json.dumps(body).encode(),{"Content-Type":"application/json","X-CSRF-TOKEN":tok})
        out.append(f"POST {body} len={len(b)} :: {b[:1500]}")
    except Exception as e:
        try: msg=e.read().decode()[:300]
        except Exception: msg=""
        out.append(f"POST {body} FAIL {e} {msg}")
open(f"{OUT}/probe8.txt","w").write("\n\n".join(out)[:200000]); print("OK")
