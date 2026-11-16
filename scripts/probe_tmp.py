import urllib.request, os, http.cookiejar, json
OUT="data/debug/probe_th"; os.makedirs(OUT, exist_ok=True)
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
B={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36","Accept":"application/json, text/plain, */*",
   "Origin":"https://index.tpso.go.th","Referer":"https://index.tpso.go.th/cpi/index-analysis-report/1"}
def req(url,body=None,h=None):
    hh=dict(B); hh.update(h or {})
    data=None
    if body is not None: data=json.dumps(body).encode(); hh["Content-Type"]="application/json"
    with op.open(urllib.request.Request(url,headers=hh,data=data),timeout=60) as r: return r.read().decode()
base="https://index.tpso.go.th"; out=[]
tok=json.loads(req(base+"/api/csrf-token"))["csrfToken"]
body={"type":"TG","yearBase":2566,"Categories":["00000"],"month":10,"year":2569}
for name,h in [("none",{}),("x-csrf-token",{"x-csrf-token":tok}),("csrf-token",{"csrf-token":tok}),("X-XSRF-TOKEN",{"X-XSRF-TOKEN":tok})]:
    try: t=req(base+"/api/cpig/ChangeRate",body,h); out.append(f"== {name} OK\n{t[:5000]}"); print(name,"OK"); break
    except Exception as e:
        try: msg=e.read().decode()[:300]
        except Exception: msg=""
        out.append(f"== {name} FAIL {e} {msg}"); print(name,"FAIL",e)
open(f"{OUT}/tpso_changerate.txt","w").write("\n".join(out))
