import urllib.request, re, os
OUT="data/debug/probe_th"; os.makedirs(OUT, exist_ok=True)
B = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
     "Accept":"text/html,application/xhtml+xml,application/json,*/*;q=0.8","Accept-Language":"th,en;q=0.9"}
C = {"User-Agent":"curl/8.5.0"}
tests = [
 ("bot_mpc", "https://www.bot.or.th/th/our-roles/monetary-policy/mpc-meeting.html", B),
 ("bot_rate", "https://www.bot.or.th/th/our-roles/monetary-policy/mpc-publication/policy-interest-rate.html", B),
 ("bot_rate_en", "https://www.bot.or.th/en/our-roles/monetary-policy/mpc-publication/policy-interest-rate.html", B),
 ("fred_th_cpi_yoy", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPALTT01THM659N", C),
 ("fred_th_cpi_idx", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=THACPIALLMINMEI", C),
 ("fred_th_gdp_real_sa", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=NGDPRSAXDCTHQ", C),
 ("fred_th_gdp_nom_sa", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=NGDPSAXDCTHQ", C),
 ("tpso_home", "https://www.tpso.go.th/", B),
 ("tpso_cpi", "https://index.tpso.go.th/", B),
 ("nesdc_gdp", "https://www.nesdc.go.th/info/economic-aspect/", B),
 ("nesdc_home", "https://www.nesdc.go.th/", B),
]
for name,url,h in tests:
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=40) as r:
            raw=r.read().decode("utf-8","replace")
        txt=re.sub(r"\s+"," ",re.sub(r"(?s)<[^>]+>"," ",re.sub(r"(?is)<(script|style).*?</\1>"," ",raw)))
        links=sorted(set(re.findall(r'href="([^"]+\.(?:xlsx?|csv|pdf)[^"]*)"',raw)))[:80]
        apis=sorted(set(re.findall(r'https?://[a-z0-9.\-]*(?:api|gateway)[a-z0-9.\-]*/[^"\'\s<>]+',raw)))[:40]
        open(f"{OUT}/{name}.txt","w").write(f"URL {url}\nLEN {len(raw)}\nLINKS {links}\nAPIS {apis}\n\n{txt[:30000]}\n\nTAIL {txt[-3000:] if 'fred' in name else ''}")
        print(f"{name}: OK {len(raw)}")
    except Exception as e:
        print(f"{name}: FAIL {e}")
