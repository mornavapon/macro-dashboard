import urllib.request, re, os, http.cookiejar, json, io, zipfile
OUT="data/debug/probe_th"; os.makedirs(OUT, exist_ok=True)
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
B={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36","Accept":"*/*"}
def get(url,binary=False):
    with op.open(urllib.request.Request(url,headers=B),timeout=60) as r:
        b=r.read(); return b if binary else b.decode("utf-8","replace")
out=[]
base="https://index.tpso.go.th"
raw=get(base+"/"); man=get(base+re.search(r'src="(/_next/static/[^"]+_buildManifest\.js)"',raw).group(1))
for c in re.findall(r'"(static/chunks/pages/cpi/dissemination-process[^"]*\.js)"',man):
    js=get(base+"/_next/"+c)
    for m in re.finditer(r'/api/[A-Za-z/]+',js): out.append(f"{c} {m.group(0)} :: {js[max(0,m.start()-300):m.end()+300]}")
for p in ["/api/Calendar","/api/calendar","/api/Dissemination","/api/dissemination/cpi"]:
    try: out.append(f"== {p}\n"+get(base+p)[:2000])
    except Exception as e: out.append(f"== {p} FAIL {e}")
# xlsx rows with numeric H
page=get("https://www.bot.or.th/th/our-roles/monetary-policy/mpc-publication/policy-interest-rate.html")
link=re.search(r'(/content/dam/[^"]*table-mpc-[^"]*\.xlsx)',page).group(1)
z=zipfile.ZipFile(io.BytesIO(get("https://www.bot.or.th"+link,binary=True)))
ss=[re.sub(r"<[^>]+>","",x) for x in re.findall(r"<si>(.*?)</si>",z.read("xl/sharedStrings.xml").decode(),re.S)]
sh=z.read("xl/worksheets/sheet1.xml").decode()
rows=[]
for r in re.findall(r'<row [^>]*>(.*?)</row>',sh,re.S):
    d={}
    for col,attrs,v in re.findall(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(?:<f>.*?</f>)?(?:<v>([^<]*)</v>)?</c>)',r):
        if v=="" : continue
        d[col]=ss[int(v)] if 't="s"' in attrs else v
    rows.append(d)
out.append("HEAD "+json.dumps(rows[:4],ensure_ascii=False))
out.append("TAIL "+json.dumps([r for r in rows if r.get("H")][-10:],ensure_ascii=False))
open(f"{OUT}/probe7.txt","w").write("\n\n".join(out)[:60000]); print("OK")
