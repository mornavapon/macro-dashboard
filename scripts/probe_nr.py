import json, urllib.request
for u in ["https://www.thaibma.or.th/nrdaily/GetNR/", "https://www.thaibma.or.th/nrdaily/GetNR/?startDate=2024-11-01&endDate=2026-11-18"]:
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=30))
        print(u, "rows", len(d), "first", d[0]["Asof"], "last", d[-1]["Asof"])
        print(json.dumps(d[-1]))
    except Exception as e:
        print(u, "FAIL", e)
