import urllib.request, urllib.parse, re, os, http.cookiejar, json
OUT="data/debug/probe_th"; os.makedirs(OUT, exist_ok=True)
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
B={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36","Accept":"*/*","Accept-Language":"th,en"}
def get(url):
    with op.open(urllib.request.Request(url,headers=B),timeout=60) as r: return r.read().decode("utf-8","replace")
out=[]
W="https://www.nesdc.go.th/wp-json/wp/v2"
for name,url in [
  ("posts_search", W+"/posts?per_page=20&search="+urllib.parse.quote("ไตรมาส")),
  ("posts_gdp", W+"/posts?per_page=20&search=GDP"),
  ("media_pdf", W+"/media?per_page=30&mime_type=application/pdf&search="+urllib.parse.quote("ไตรมาส")),
  ("media_gdp", W+"/media?per_page=30&search=GDP"),
  ("types", W+"/types"),
]:
    try:
        t=get(url)
        try:
            j=json.loads(t)
            if isinstance(j,list):
                lines=[f"{x.get('date')} | {(x.get('title') or {}).get('rendered')} | {x.get('link')} | {x.get('source_url','')}" for x in j]
                out.append(f"== {name} ({len(j)})\n"+"\n".join(lines))
            else: out.append(f"== {name}\n"+t[:3000])
        except ValueError: out.append(f"== {name} NOT JSON\n"+t[:500])
    except Exception as e: out.append(f"== {name} FAIL {e}")
open(f"{OUT}/nesdc_wp.txt","w").write("\n\n".join(out)); print("OK")
