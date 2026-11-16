import urllib.request, re, os, http.cookiejar, json
OUT="data/debug/probe_ex"; os.makedirs(OUT, exist_ok=True)
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
B={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36","Accept":"*/*","Accept-Language":"th,en"}
def get(url):
    with op.open(urllib.request.Request(url,headers=B),timeout=60) as r: return r.read().decode("utf-8","replace")
def clean(t): return re.sub(r"\s+"," ",re.sub(r"(?s)<[^>]+>"," ",re.sub(r"(?is)<(script|style).*?</\1>"," ",t)))
out=[]
for u in ["https://tradereport.moc.go.th/opendata/summarycountries","https://tradereport.moc.go.th/th/stat/reportmonth01"]:
    try:
        t=get(u); c=clean(t); i=c.find("Thailand's Trade Statistic")
        body=c[c.find("ติดต่อเรา"):][:200]
        out.append(f"== {u}\n"+c[-6000:]+"\nURLS "+str(sorted(set(re.findall(r'https?://[^"\'\s<>]+',t)))[:80])+"\nFORMS "+str(re.findall(r'<form[^>]*>',t))+"\nINLINE "+" ".join(re.findall(r"(?is)<script[^>]*>(.*?)</script>",t))[-5000:])
    except Exception as e: out.append(f"== {u} FAIL {e}")
open(f"{OUT}/probe3.txt","w").write("\n\n".join(out)[:150000]); print("OK")
