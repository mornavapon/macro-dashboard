import urllib.request, urllib.parse, re
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
def get(u):
    r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "*/*"}), timeout=40)
    return r.read()
for u in ["https://www.boi.go.th/upload/content/FDI%20Report%20Q269%20Final_6a8d4b517b226.pdf"]:
    try:
        d = get(u); print("PDF", len(d), d[:8])
    except Exception as e: print("PDF x", e)
for q in ["BOI ยอดขอรับส่งเสริมการลงทุน", "บีโอไอ ขอรับการส่งเสริมการลงทุน 9 เดือน"]:
    u = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q) + "&hl=th&gl=TH&ceid=TH:th"
    try:
        x = get(u).decode("utf-8", "replace")
        items = re.findall(r"<item><title>(.*?)</title>.*?<pubDate>(.*?)</pubDate>", x)
        print("NEWS", q, len(items))
        for t, d in items[:8]: print("   ", d, "|", t[:120])
    except Exception as e: print("NEWS x", e)
