import urllib.request, re, os, http.cookiejar, json
OUT="data/debug/probe_ex"; os.makedirs(OUT, exist_ok=True)
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
B={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36","Accept":"*/*","Accept-Language":"th,en"}
def get(url):
    with op.open(urllib.request.Request(url,headers=B),timeout=60) as r: return r.read().decode("utf-8","replace"), r.headers.get("Content-Type")
out=[]
t,_=get("https://tradereport.moc.go.th/opendata/summarycountries")
c=re.sub(r"\s+"," ",re.sub(r"(?s)<[^>]+>"," ",re.sub(r"(?is)<style.*?</style>"," ",t)))
for k in ["GET","Method","URL","year","month","Parameter","ปี","เดือน","Response","Example","json"]:
    for m in list(re.finditer(k,c))[:3]: out.append(f"[{k}] "+c[max(0,m.start()-200):m.start()+400])
for q in ["?year=2569&month=10","?year=2026&month=10","?Year=2569&Month=10","?year=2569","?y=2569&m=10"]:
    try:
        b,ct=get("https://tradereport.moc.go.th/opendata/summarycountries"+q); out.append(f"Q {q} ct={ct} len={len(b)} :: {b[:600]}")
    except Exception as e: out.append(f"Q {q} FAIL {e}")
open(f"{OUT}/probe5.txt","w").write("\n\n".join(out)[:150000]); print("OK")
