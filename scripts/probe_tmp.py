import urllib.request, re, os, http.cookiejar, json
OUT="data/debug/probe_th"; os.makedirs(OUT, exist_ok=True)
B = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36","Accept":"*/*"}
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def get(url):
    with op.open(urllib.request.Request(url,headers=B),timeout=60) as r: return r.read().decode("utf-8","replace")
base="https://index.tpso.go.th"; out=[]
raw=get(base+"/"); man=get(base+re.search(r'src="(/_next/static/[^"]+_buildManifest\.js)"',raw).group(1))
chunks=sorted(set(re.findall(r'"(static/chunks/[^"]+\.js)"',man)))
seen=set()
for c in chunks:
    try: js=get(base+"/_next/"+c)
    except Exception as e: continue
    for m in re.finditer(r'/api/cpig/[A-Za-z]+',js):
        key=(m.group(0),js[m.start()-150:m.start()])
        if m.group(0) in seen and len(seen)>40: continue
        seen.add(m.group(0))
        out.append(f"### {c} {m.group(0)}\n{js[max(0,m.start()-500):m.end()+500]}")
m=json.loads(get(base+"/api/cpig/master")); out.insert(0,"MASTER keys "+str({k:(v if k!='categories' else '...') for k,v in m.items()}))
open(f"{OUT}/tpso_cpig.txt","w").write("\n\n".join(out)[:80000]); print("OK",len(out))
