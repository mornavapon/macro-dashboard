import urllib.request, urllib.parse, re, os, http.cookiejar, json, io, zipfile
OUT="data/debug/probe_th"; os.makedirs(OUT, exist_ok=True)
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
B={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36","Accept":"*/*"}
def get(url,binary=False):
    with op.open(urllib.request.Request(url,headers=B),timeout=120) as r:
        b=r.read(); return b if binary else b.decode("utf-8","replace")
url=json.loads(get("https://www.nesdc.go.th/wp-json/wp/v2/media?per_page=5&orderby=date&order=desc&search="+urllib.parse.quote("All Tables QGDP")))[0]["source_url"]
z=zipfile.ZipFile(io.BytesIO(get(url,binary=True)))
wb=z.read("xl/workbook.xml").decode(); rels=z.read("xl/_rels/workbook.xml.rels").decode()
sheets=re.findall(r'<sheet [^>]*name="([^"]+)"[^>]*r:id="([^"]+)"',wb)
relmap=dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"',rels)); relmap.update({a:b for b,a in re.findall(r'Target="([^"]+)"[^>]*Id="([^"]+)"',rels)})
ss=[re.sub(r"<[^>]+>","",x) for x in re.findall(r"<si>(.*?)</si>",z.read("xl/sharedStrings.xml").decode(),re.S)]
out=[url, "SHEETS "+str([s[0] for s in sheets])]
for name,rid in sheets[:40]:
    path="xl/"+relmap[rid].lstrip("/").replace("xl/","")
    sh=z.read(path).decode()
    rows=[]
    for r in re.findall(r'<row [^>]*>(.*?)</row>',sh,re.S)[:60]:
        cells=[]
        for col,attrs,v in re.findall(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(?:<f>.*?</f>)?(?:<v>([^<]*)</v>)?</c>)',r):
            if v: cells.append(f"{col}={ss[int(v)] if 't=\"s\"' in attrs else v}")
        if cells: rows.append(" | ".join(cells)[:400])
    out.append(f"##### {name}\n"+"\n".join(rows[:14]))
open(f"{OUT}/qgdp.txt","w").write("\n".join(out)[:200000]); print("OK")
