import urllib.request, re, os, io, zipfile, http.cookiejar, html as H
OUT="data/debug/probe_th"; os.makedirs(OUT, exist_ok=True)
B = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
     "Accept":"text/html,application/xhtml+xml,application/json,*/*;q=0.8","Accept-Language":"th,en;q=0.9"}
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def get(url,h=B,binary=False):
    with op.open(urllib.request.Request(url,headers=h),timeout=40) as r:
        b=r.read(); return (b if binary else b.decode("utf-8","replace")), r.geturl()
def save(name,txt): open(f"{OUT}/{name}.txt","w").write(txt[:40000])
def clean(raw): return re.sub(r"\s+"," ",re.sub(r"(?s)<[^>]+>"," ",re.sub(r"(?is)<(script|style).*?</\1>"," ",raw)))
# 1 BOT xlsx
try:
    page,_=get("https://www.bot.or.th/th/our-roles/monetary-policy/mpc-publication/policy-interest-rate.html")
    link=re.search(r'(/content/dam/[^"]*table-mpc-[^"]*\.xlsx)',page).group(1)
    b,_=get("https://www.bot.or.th"+link,binary=True)
    z=zipfile.ZipFile(io.BytesIO(b)); out=[link,str(z.namelist())]
    for n in z.namelist():
        if n.endswith("sharedStrings.xml") or n.endswith("sheet1.xml"): out.append(n+"\n"+z.read(n).decode("utf-8","replace")[:12000])
    save("bot_xlsx","\n".join(out)); print("bot_xlsx OK")
except Exception as e: print("bot_xlsx FAIL",e)
# 2 TPSO SPA scripts
for site in ["https://index.tpso.go.th/","https://www.tpso.go.th/"]:
    try:
        raw,_=get(site); srcs=re.findall(r'<script[^>]+src="([^"]+)"',raw)
        out=[raw[:3000],str(srcs)]
        for s in srcs[:8]:
            u=s if s.startswith("http") else site.rstrip("/")+"/"+s.lstrip("/")
            try:
                js,_=get(u); urls=sorted(set(re.findall(r'["\'`](https?://[^"\'`\s]+|/api/[^"\'`\s]+)["\'`]',js)))
                out.append(f"--- {u} ({len(js)})\n"+"\n".join(urls[:150]))
            except Exception as e: out.append(f"--- {u} FAIL {e}")
        save("tpso_js_"+site.split("//")[1].split(".")[0],"\n".join(out)); print("tpso js OK",site)
    except Exception as e: print("tpso FAIL",site,e)
# 3 NESDC with cookies
for name,url in [("nesdc_home","https://www.nesdc.go.th/"),("nesdc_eco","https://www.nesdc.go.th/info/economic-aspect/"),
                 ("nesdc_qgdp_old","https://www.nesdc.go.th/main.php?filename=qgdp_page")]:
    try:
        raw,final=get(url); links=sorted(set(re.findall(r'href="([^"]+\.(?:xlsx?|csv|pdf|zip)[^"]*)"',raw)))
        save(name,f"FINAL {final}\nLINKS {links[:120]}\n\n"+clean(raw)); print(name,"OK",len(raw),final)
    except Exception as e: print(name,"FAIL",e)
