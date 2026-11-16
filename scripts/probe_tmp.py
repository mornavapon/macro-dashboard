import urllib.request, re, os
os.makedirs("probe_out", exist_ok=True)
B = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
     "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","Accept-Language":"en-US,en;q=0.9","Accept-Encoding":"identity"}
tests = [
 ("bea", "https://www.bea.gov/news/schedule", B),
 ("bls_page_full", "https://www.bls.gov/schedule/news_release/cpi.htm", B),
 ("bls_page_contact", "https://www.bls.gov/schedule/news_release/cpi.htm", {"User-Agent":"macro-dashboard/1.0 (contact: mornavapon@users.noreply.github.com)"}),
 ("bls_ics", "https://www.bls.gov/schedule/news_release/bls.ics", {"User-Agent":"macro-dashboard/1.0 (contact: mornavapon@users.noreply.github.com)"}),
 ("bls_api_v1", "https://api.bls.gov/publicAPI/v1/timeseries/data/CUUR0000SA0", {}),
]
for name,url,h in tests:
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=40) as r:
            t=r.read().decode("utf-8","replace")
        txt=re.sub(r"\s+"," ",re.sub(r"(?s)<[^>]+>"," ",re.sub(r"(?is)<(script|style).*?</\1>"," ",t)))
        open(f"probe_out/{name}.txt","w").write(txt[:60000])
        print(f"{name}: OK {len(t)}")
        for kw in ("GDP","Consumer Price","CPI"):
            for m in list(re.finditer(kw, txt))[:4]:
                print("   ",kw,"::",txt[max(0,m.start()-150):m.start()+150])
    except Exception as e:
        print(f"{name}: FAIL {e}")
