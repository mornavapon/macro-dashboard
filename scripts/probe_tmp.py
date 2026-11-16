import urllib.request, re, os, http.cookiejar, json, io, subprocess, sys
OUT="data/debug/probe_fill"; os.makedirs(OUT, exist_ok=True)
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
B={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
   "Accept":"text/html,application/json,*/*;q=0.8","Accept-Language":"en-US,en;q=0.9"}
def get(url,binary=False,h=None):
    hh=dict(B); hh.update(h or {})
    with op.open(urllib.request.Request(url,headers=hh),timeout=45) as r:
        b=r.read(); return b if binary else b.decode("utf-8","replace")
def clean(t): return re.sub(r"\s+"," ",re.sub(r"(?s)<[^>]+>"," ",re.sub(r"(?is)<(script|style).*?</\1>"," ",t)))
KW=r"(P/E|PE Ratio|P/B|Price.to.Book|Price/Book|PB Ratio|Market Cap|Market Capitali[sz]ation|市净率|市盈率|总市值|vốn hóa|Vốn hóa|P/BV)"
tests=[
 ("wpr_spx","https://worldperatio.com/index/sp-500/",{}),
 ("wpr_ndx","https://worldperatio.com/index/nasdaq-100/",{}),
 ("wpr_ixic","https://worldperatio.com/index/nasdaq-composite/",{}),
 ("wpr_hk","https://worldperatio.com/area/hong-kong/",{}),
 ("wpr_cn","https://worldperatio.com/area/china/",{}),
 ("wpr_vn","https://worldperatio.com/area/vietnam/",{}),
 ("sa_spy","https://stockanalysis.com/etf/spy/",{}),
 ("sa_oneq","https://stockanalysis.com/etf/oneq/",{}),
 ("sa_qqq","https://stockanalysis.com/etf/qqq/",{}),
 ("siblis_spx_mcap","https://siblisresearch.com/data/us-sp-500-market-cap/",{}),
 ("siblis_spx_pb","https://siblisresearch.com/data/price-to-book-sp-500/",{}),
 ("gurufocus_spx","https://www.gurufocus.com/economic_indicators/56/sp-500-pb-ratio",{}),
 ("csi_000001","https://www.csindex.com.cn/csindex-home/perf/index-perf-oneday?indexCode=000001",{"Referer":"https://www.csindex.com.cn/"}),
 ("sse_pb","https://query.sse.com.cn/commonQuery.do?jsonCallBack=&isPagination=false&sqlId=COMMON_SSE_SJ_GPSJ_GPSJZM_TJSJ_L&PRODUCT_NAME=%E8%82%A1%E7%A5%A8&type=inParams",{"Referer":"https://www.sse.com.cn/"}),
 ("legulegu_pb","https://legulegu.com/stockdata/shanghaiPB",{}),
 ("hsi_hscei_page","https://www.hsi.com.hk/en/indexes/all-indexes/hscei",{}),
 ("vn_simplize_api","https://api.simplize.vn/api/historical/index/VNINDEX",{}),
 ("vn_cafef","https://s.cafef.vn/Ajax/PageNew/DataHistory/PriceHistory.ashx?Symbol=VNINDEX&PageIndex=1&PageSize=1",{}),
 ("vn_vietstock","https://finance.vietstock.vn/ket-qua-giao-dich?tab=thong-ke-gia",{}),
 ("vn_fireant","https://restv2.fireant.vn/symbols/VNINDEX/fundamental",{}),
 ("vn_ssi_index","https://iboard-query.ssi.com.vn/exchange-index/VNINDEX?hasHistory=false",{"Origin":"https://iboard.ssi.com.vn","Referer":"https://iboard.ssi.com.vn/"}),
 ("vn_vndirect_ratio","https://api-finfo.vndirect.com.vn/v4/ratios/latest?filter=itemCode:51003,51004,51006,51007&where=code:VNINDEX",{}),
]
summary=[]
for name,url,h in tests:
    try:
        t=get(url,h=h); c=clean(t)
        hits=[c[max(0,m.start()-120):m.end()+160] for m in list(re.finditer(KW,c))[:8]]
        open(f"{OUT}/{name}.txt","w").write(f"URL {url}\nLEN {len(t)}\n\n"+"\n---\n".join(hits)+"\n\nHEAD "+c[:3000])
        summary.append(f"{name}: OK len={len(t)} hits={len(hits)}")
    except Exception as e: summary.append(f"{name}: FAIL {e}")
# HSCEI factsheet pdf
try:
    subprocess.run([sys.executable,"-m","pip","install","-q","pypdf"],check=True)
    from pypdf import PdfReader
    for name,url in [("hscei_fs","https://www.hsi.com.hk/static/uploads/contents/en/dl_centre/factsheets/hsceie.pdf")]:
        try:
            b=get(url,binary=True); txt="\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(b)).pages)
            open(f"{OUT}/{name}.txt","w").write(txt[:20000]); summary.append(f"{name}: OK pdf {len(b)}")
        except Exception as e: summary.append(f"{name}: FAIL {e}")
except Exception as e: summary.append(f"pypdf FAIL {e}")
open(f"{OUT}/_summary.txt","w").write("\n".join(summary)); print("\n".join(summary))
