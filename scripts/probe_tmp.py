import urllib.request, re, os, io, zipfile, http.cookiejar
OUT="data/debug/probe_th"; os.makedirs(OUT, exist_ok=True)
B = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
     "Accept":"text/html,application/xhtml+xml,application/json,*/*;q=0.8","Accept-Language":"th,en;q=0.9"}
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def get(url,binary=False):
    with op.open(urllib.request.Request(url,headers=B),timeout=60) as r:
        b=r.read(); return b if binary else b.decode("utf-8","replace")
def save(name,txt): open(f"{OUT}/{name}.txt","w").write(txt[:60000])
# NESDC: find any file links / data near GDP keywords in raw html
try:
    raw=get("https://www.nesdc.go.th/info/economic-aspect/")
    files=sorted(set(re.findall(r'(https?:[\\/]+[^"\'\s<>]+?\.(?:xlsx?|zip|csv))',raw)))
    near=[]
    for kw in ["GDP","QGDP","ผลิตภัณฑ์มวลรวม","บัญชีประชาชาติ","ไตรมาส"]:
        for m in list(re.finditer(kw,raw))[:5]: near.append(f"[{kw}] "+raw[max(0,m.start()-300):m.start()+300].replace("\n"," "))
    save("nesdc_files","\n".join(files[:300])+"\n\n=== NEAR\n"+"\n".join(near))
    print("nesdc OK",len(files))
except Exception as e: print("nesdc FAIL",e)
# TPSO all chunks: look for api hosts
try:
    raw=get("https://index.tpso.go.th/")
    srcs=re.findall(r'src="(/_next/[^"]+)"',raw); hits=[]
    bm=re.search(r'src="(/_next/static/[^"]+_buildManifest\.js)"',raw)
    if bm:
        man=get("https://index.tpso.go.th"+bm.group(1)); srcs+= ["/_next/"+x for x in re.findall(r'"static/chunks/[^"]+\.js"',man) for x in [x.strip('"')]]
    for s in sorted(set(srcs)):
        try:
            js=get("https://index.tpso.go.th"+s)
            for m in re.findall(r'["\'`]([^"\'`]{0,80}(?:api|Api|API)[^"\'`]{0,120})["\'`]',js):
                if "/" in m: hits.append(f"{s}: {m}")
        except Exception as e: hits.append(f"{s} FAIL {e}")
    save("tpso_api_hits","\n".join(sorted(set(hits))[:400])); print("tpso OK",len(hits))
except Exception as e: print("tpso FAIL",e)
# BOT xlsx full
try:
    page=get("https://www.bot.or.th/th/our-roles/monetary-policy/mpc-publication/policy-interest-rate.html")
    link=re.search(r'(/content/dam/[^"]*table-mpc-[^"]*\.xlsx)',page).group(1)
    z=zipfile.ZipFile(io.BytesIO(get("https://www.bot.or.th"+link,binary=True)))
    ss=re.findall(r"<si>(.*?)</si>",z.read("xl/sharedStrings.xml").decode())
    ss=[re.sub(r"<[^>]+>","",x) for x in ss]
    sh=z.read("xl/worksheets/sheet1.xml").decode()
    rows=re.findall(r'<row [^>]*>(.*?)</row>',sh)
    out=[]
    for r in rows[:3]+rows[-12:]:
        cells=re.findall(r'<c r="([A-Z]+)\d+"([^>]*)>(?:<f>[^<]*</f>)?<v>([^<]*)</v>',r)
        out.append(" | ".join(f"{c}={ss[int(v)] if 't=\"s\"' in a else v}" for c,a,v in cells))
    save("bot_xlsx_rows","\n".join(out)); print("bot OK")
except Exception as e: print("bot FAIL",e)
