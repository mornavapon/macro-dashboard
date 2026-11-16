import urllib.request, re, os, http.cookiejar, json
OUT="data/debug/probe_ex"; os.makedirs(OUT, exist_ok=True)
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
B={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36","Accept":"*/*","Accept-Language":"th,en"}
def get(url):
    with op.open(urllib.request.Request(url,headers=B),timeout=60) as r: return r.read().decode("utf-8","replace")
out=[]
for pid in ["tradethexportmonthly","dataset_31_02"]:
    try:
        j=json.loads(get(f"https://data.go.th/api/3/action/package_show?id={pid}"))
        res=j["result"].get("resources",[])
        out.append(f"== CKAN {pid}: "+json.dumps([{k:r.get(k) for k in ("name","url","format","last_modified","description")} for r in res],ensure_ascii=False)[:4000])
    except Exception as e: out.append(f"== CKAN {pid} FAIL {e}")
t=get("https://tradereport.moc.go.th/opendata/summarycountries")
i=t.find("API ภาพรวม", t.find("<main") if "<main" in t else 0)
for m in list(re.finditer(r'(?i)(api/|apiurl|endpoint|parameter|year|month)',t))[:0]: pass
body=re.findall(r'(?is)<div class="content-wrapper.*',t)
out.append("RAW MAIN "+ (t[t.find('id="content"'):t.find('id="content"')+8000] if 'id="content"' in t else t[-12000:]))
open(f"{OUT}/probe4.txt","w").write("\n\n".join(out)[:150000]); print("OK")
