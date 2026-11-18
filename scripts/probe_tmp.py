import urllib.request, re, os, json
OUT="data/debug/probe_u"; os.makedirs(OUT, exist_ok=True)
B={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36","Accept":"text/html"}
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers=B),timeout=60) as r: return r.read().decode("utf-8","replace")
out=[]
for name,url in [("sp500","https://stockanalysis.com/list/sp-500-stocks/"),("nasdaq","https://stockanalysis.com/list/nasdaq-stocks/"),
                 ("nyse","https://stockanalysis.com/list/nyse-stocks/"),("dow","https://stockanalysis.com/list/dow-jones-stocks/"),
                 ("exch_nyse","https://stockanalysis.com/list/exchanges/nyse/"),("exchanges","https://stockanalysis.com/list/exchanges/")]:
    try:
        t=get(url)
        objs=re.findall(r'\{[^{}]*?\bs:"[^"]+"[^{}]*?marketCap:[^{}]*?\}',t)
        txt=re.sub(r"\s+"," ",re.sub(r"(?s)<[^>]+>"," ",re.sub(r"(?is)<(script|style).*?</\1>"," ",t)))
        tot=re.findall(r'.{0,80}(?:[Tt]otal|[Cc]ombined).{0,120}',txt)[:6]
        out.append(f"== {name} len={len(t)} rows={len(objs)}\nSAMPLE {objs[:2]}\nKEYS {sorted(set(re.findall(r'([a-zA-Z_]+):',objs[0])) if objs else [])}\nTOTALS {tot}\nHEAD {txt[:800]}")
    except Exception as e: out.append(f"== {name} FAIL {e}")
for name,url in [("vix","https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?range=2y&interval=1d")]:
    try: t=get(url); out.append(f"== {name} OK len={len(t)}")
    except Exception as e: out.append(f"== {name} FAIL {e}")
open(f"{OUT}/probe.txt","w").write("\n\n".join(out)); print("OK")
