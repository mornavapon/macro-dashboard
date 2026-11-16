import urllib.request, time
tests = [
 ("fred_curl_ua", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDP", {"User-Agent":"curl/8.5.0"}),
 ("fred_no_ua", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDP", {}),
 ("fred_api_nokey", "https://api.stlouisfed.org/fred/series/observations?series_id=GDP&file_type=json", {"User-Agent":"curl/8.5.0"}),
 ("nyfed_effr", "https://markets.newyorkfed.org/api/rates/unsecured/effr/last/2.json", {"User-Agent":"curl/8.5.0"}),
 ("bls_v1", "https://api.bls.gov/publicAPI/v1/timeseries/data/CUUR0000SA0", {"User-Agent":"curl/8.5.0"}),
 ("bea_schedule", "https://www.bea.gov/news/schedule", {"User-Agent":"Mozilla/5.0"}),
 ("bls_cpi_sched", "https://www.bls.gov/schedule/news_release/cpi.htm", {"User-Agent":"Mozilla/5.0"}),
 ("dbnomics_gdp", "https://api.db.nomics.world/v22/series/BEA/NIPA-T10101?observations=1&limit=5&q=gross%20domestic%20product", {}),
]
for name,url,h in tests:
    t=time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=40) as r:
            b=r.read()
        print(f"{name}: OK {r.status} {len(b)}B {time.time()-t:.1f}s :: {b[:300]!r}")
    except Exception as e:
        print(f"{name}: FAIL {type(e).__name__} {e} {time.time()-t:.1f}s")
