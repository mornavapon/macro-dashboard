import urllib.request, re, os, http.cookiejar, json
OUT="data/debug/probe_ex"; os.makedirs(OUT, exist_ok=True)
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
B={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36","Accept":"*/*","Accept-Language":"th,en"}
def get(url):
    with op.open(urllib.request.Request(url,headers=B),timeout=60) as r: return r.read().decode("utf-8","replace")
def clean(t): return re.sub(r"\s+"," ",re.sub(r"(?s)<[^>]+>"," ",re.sub(r"(?is)<(script|style).*?</\1>"," ",t)))
out=[]
t=get("https://tradereport.moc.go.th/")
out.append("TRADEREPORT TEXT "+clean(t)[:5000])
out.append("LINKS "+str(sorted(set(re.findall(r'href="([^"#]+)"',t)))[:150]))
out.append("SCRIPTS "+str(re.findall(r'<script[^>]*src="([^"]+)"',t)))
inline=" ".join(re.findall(r"(?is)<script[^>]*>(.*?)</script>",t))
out.append("INLINE AJAX "+str(re.findall(r'(?:url\s*:\s*|fetch\(|\.get\(|\.post\()\s*["\']([^"\']+)["\']',inline)[:60]))
# tpso fms usage
base="https://www.tpso.go.th"; raw=get(base+"/")
bm=re.search(r'src="(/_next/static/[^"]+_buildManifest\.js)"',raw)
chunks=set(re.findall(r'src="(/_next/[^"]+\.js)"',raw))
if bm:
    man=get(base+bm.group(1)); chunks|={"/_next/"+x for x in re.findall(r'"(static/chunks/[^"]+\.js)"',man)}
for c in sorted(chunks):
    try: js=get(base+c)
    except Exception: continue
    for m in re.finditer(r'fms\.tpso\.go\.th/api/v2/',js):
        out.append(f"FMS {c}: {js[max(0,m.start()-200):m.end()+400]}")
    for m in re.finditer(r'["\'`](/[a-zA-Z\-]+(?:/[a-zA-Z\-]+)*\?(?:[^"\'`]{0,80}))["\'`]',js):
        if 'populate' in m.group(1) or 'filters' in m.group(1): out.append(f"Q {c}: {m.group(1)}")
open(f"{OUT}/probe2.txt","w").write("\n\n".join(out)[:150000]); print("OK")
