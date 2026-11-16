import urllib.request, re, os, http.cookiejar, json
OUT="data/debug/probe_ex"; os.makedirs(OUT, exist_ok=True)
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
B={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36","Accept":"*/*","Accept-Language":"th,en"}
def get(url):
    with op.open(urllib.request.Request(url,headers=B),timeout=60) as r: return r.read().decode("utf-8","replace")
out=[]
# 1) www.tpso.go.th JS api strings
base="https://www.tpso.go.th"
try:
    raw=get(base+"/"); out.append("TPSO HOME "+raw[:1500])
    bm=re.search(r'src="(/_next/static/[^"]+_buildManifest\.js)"',raw)
    chunks=set(re.findall(r'src="(/_next/[^"]+\.js)"',raw))
    if bm:
        man=get(base+bm.group(1)); chunks|={"/_next/"+x for x in re.findall(r'"(static/chunks/[^"]+\.js)"',man)}
    hits=set()
    for c in sorted(chunks):
        try: js=get(base+c)
        except Exception: continue
        for m in re.finditer(r'["\'`]((?:https?://[^"\'`\s]{0,60})?/api/[^"\'`\s]{0,80})["\'`]',js): hits.add(m.group(1))
        for m in re.finditer(r'https?://[a-z0-9.\-]*tpso[a-z0-9.\-]*[^"\'`\s]{0,60}',js): hits.add(m.group(0))
    out.append("TPSO WWW API HITS\n"+"\n".join(sorted(hits)[:300]))
except Exception as e: out.append(f"tpso www FAIL {e}")
# 2) tradereport
for u in ["https://tradereport.moc.go.th/","https://tradereport.moc.go.th/th/stat/reportcommodity","https://www.ops3.moc.go.th/"]:
    try: t=get(u); out.append(f"== {u} len={len(t)}\n"+re.sub(r'\s+',' ',re.sub(r'(?s)<[^>]+>',' ',t))[:1500]+"\nAPIS "+str(sorted(set(re.findall(r'["\']([^"\']*(?:api|Api)[^"\']*)["\']',t)))[:60]))
    except Exception as e: out.append(f"== {u} FAIL {e}")
open(f"{OUT}/probe.txt","w").write("\n\n".join(out)[:120000]); print("OK")
