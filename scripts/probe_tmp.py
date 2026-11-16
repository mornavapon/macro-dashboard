import urllib.request, re, os, http.cookiejar, json
OUT="data/debug/probe_ex"; os.makedirs(OUT, exist_ok=True)
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
B={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36","Accept":"*/*","Accept-Language":"th,en"}
def get(url):
    with op.open(urllib.request.Request(url,headers=B),timeout=60) as r: return r.read().decode("utf-8","replace")
out=[]
for page in ["https://tradereport.moc.go.th/opendata/summarycountries","https://tradereport.moc.go.th/th/stat/reportmonth01"]:
    t=get(page)
    scripts=re.findall(r"(?is)<script(?![^>]*src)[^>]*>(.*?)</script>",t)
    big=[s for s in scripts if len(s)>200]
    out.append(f"== {page} inline scripts: "+"\n---\n".join(s.strip()[:3500] for s in big[:6]))
    i=t.find("<main"); j=t.find("</main>")
    out.append("MAIN "+re.sub(r"\s+"," ",t[i:j])[:6000] if i>0 else "NO MAIN")
js=get("https://tradereport.moc.go.th/js/app.js")
out.append("APPJS "+str(sorted(set(re.findall(r'["\'`](/[a-z][^"\'`\s]{3,80})["\'`]',js)))[:200]))
open(f"{OUT}/probe6.txt","w").write("\n\n".join(out)[:150000]); print("OK")
