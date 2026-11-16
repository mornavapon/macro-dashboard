import urllib.request, re, os, io, zipfile, http.cookiejar, json
OUT="data/debug/probe_th"; os.makedirs(OUT, exist_ok=True)
B = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
     "Accept":"application/json,text/html,*/*;q=0.8","Accept-Language":"th,en;q=0.9"}
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def get(url,binary=False,h=None,data=None):
    hh=dict(B); hh.update(h or {})
    with op.open(urllib.request.Request(url,headers=hh,data=data),timeout=60) as r:
        b=r.read(); return b if binary else b.decode("utf-8","replace")
def save(name,txt): open(f"{OUT}/{name}.txt","w").write(txt[:60000])
out=[]
# BOT xlsx raw
try:
    page=get("https://www.bot.or.th/th/our-roles/monetary-policy/mpc-publication/policy-interest-rate.html")
    link=re.search(r'(/content/dam/[^"]*table-mpc-[^"]*\.xlsx)',page).group(1)
    z=zipfile.ZipFile(io.BytesIO(get("https://www.bot.or.th"+link,binary=True)))
    ssx=z.read("xl/sharedStrings.xml").decode(); sh=z.read("xl/worksheets/sheet1.xml").decode()
    save("bot_ss",ssx[:20000]); save("bot_sheet_tail",sh[-15000:]); print("bot OK")
except Exception as e: print("bot FAIL",e)
# TPSO API candidates
base="https://index.tpso.go.th"
for p in ["/api/csrf-token","/api/cpig/master","/api/cpig/master?lang=th","/api/ReportAll/"]:
    try:
        t=get(base+p, h={"Referer":base+"/"}); out.append(f"== {p}\n{t[:6000]}"); print("tpso OK",p,len(t))
    except Exception as e: out.append(f"== {p} FAIL {e}"); print("tpso FAIL",p,e)
# grep the cpi page chunk for how /api/cpig is called
try:
    raw=get(base+"/"); bm=re.search(r'src="(/_next/static/[^"]+_buildManifest\.js)"',raw)
    man=get(base+bm.group(1))
    cpi_pages=[x for x in re.findall(r'"(static/chunks/pages/[^"]*cpi[^"]*\.js)"',man)]
    out.append("CPI PAGES "+str(cpi_pages))
    for c in sorted(set(cpi_pages))[:6]:
        js=get(base+"/_next/"+c)
        for m in re.finditer(r'/api/[A-Za-z]+/[A-Za-z]+',js):
            out.append(f"{c}: ...{js[max(0,m.start()-250):m.end()+250]}")
    print("tpso js OK")
except Exception as e: print("tpso js FAIL",e)
save("tpso_api2","\n\n".join(out))
