import urllib.request, re, os, http.cookiejar, json
OUT="data/debug/probe_inv"; os.makedirs(OUT, exist_ok=True)
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
B={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36","Accept":"text/html,application/json,*/*","Accept-Language":"th,en;q=0.9"}
def get(url,h=None):
    hh=dict(B); hh.update(h or {})
    with op.open(urllib.request.Request(url,headers=hh),timeout=60) as r: return r.read().decode("utf-8","replace")
out=[]
for site,page in [("set","https://www.set.or.th/th/market/statistics/investor-type"),("settrade","https://www.settrade.com/th/equities/market-data/historical-report/investor-type?market=SET")]:
    try:
        t=get(page); out.append(f"== {site} page len={len(t)}")
        apis=sorted(set(re.findall(r'(/api/[A-Za-z0-9/_\-{}$.]*investor[A-Za-z0-9/_\-{}$.?=&]*)',t)))
        out.append("APIS in html "+str(apis[:50]))
        base=page.split("/th/")[0]
        srcs=sorted(set(re.findall(r'(?:src|href)="(/_nuxt/[^"]+\.js)"',t)))
        hits=set()
        for s in srcs[:80]:
            try: js=get(base+s)
            except Exception: continue
            for m in re.finditer(r'["\'`]([^"\'`]{0,60}investor[^"\'`]{0,100})["\'`]',js):
                if "/" in m.group(1): hits.add(m.group(1))
        out.append(f"JS HITS ({len(srcs)} chunks) "+"\n".join(sorted(hits)[:80]))
    except Exception as e: out.append(f"== {site} FAIL {e}")
for u in ["https://www.set.or.th/api/set/market/SET/investor-type/trading?period=M&lang=th",
          "https://www.set.or.th/api/set/investor-type/trading?market=SET&period=M",
          "https://www.settrade.com/api/set/market/SET/investor-type-trading?period=M",
          "https://www.set.or.th/api/set/market/investor-type?market=SET"]:
    try: t=get(u,{"Referer":"https://www.set.or.th/"}); out.append(f"TRY {u} OK :: {t[:800]}")
    except Exception as e: out.append(f"TRY {u} FAIL {e}")
open(f"{OUT}/probe.txt","w").write("\n\n".join(out)[:100000]); print("OK")
