#!/usr/bin/env python3
"""
Bot cập nhật driver thị trường cho Freight Rate Monitor.
Nguồn: EIA Open Data API v2 (miễn phí) — dùng route có cấu trúc /v2/<route>/data/.
Cần biến môi trường EIA_API_KEY (đăng ký free: https://www.eia.gov/opendata/register.php).
"""
import os, json, urllib.request, urllib.error, datetime, sys

KEY = os.environ.get("EIA_API_KEY", "").strip()
if not KEY:
    print("Thiếu EIA_API_KEY", file=sys.stderr); sys.exit(1)

# (route v2, frequency, series_id, tên hiển thị, đơn vị)
SERIES = [
    ("petroleum/pri/spt",  "daily",  "RWTC",     "Dầu thô WTI (giao ngay)",      "$/bbl"),
    ("petroleum/pri/spt",  "daily",  "RBRTE",    "Dầu Brent (giao ngay)",        "$/bbl"),
    ("petroleum/stoc/wstk","weekly", "WCESTUS1", "Tồn kho dầu thô Mỹ",           "nghìn bbl"),
    ("petroleum/stoc/wstk","weekly", "WGTSTUS1", "Tồn kho xăng Mỹ",              "nghìn bbl"),
    ("petroleum/stoc/wstk","weekly", "WDISTUS1", "Tồn kho diesel/distillate Mỹ", "nghìn bbl"),
    ("petroleum/stoc/wstk","weekly", "WPRSTUS1", "Tồn kho propane Mỹ",           "nghìn bbl"),
    ("petroleum/move/wkly","weekly", "WCREXUS2", "Xuất khẩu dầu thô Mỹ",         "nghìn bbl/ngày"),
]

def fetch(route, freq, sid):
    url = (f"https://api.eia.gov/v2/{route}/data/?api_key={KEY}"
           f"&frequency={freq}&data[0]=value&facets[series][0]={sid}"
           f"&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=6")
    req = urllib.request.Request(url, headers={"User-Agent": "freight-bot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    rows = [x for x in d["response"]["data"] if x.get("value") is not None]
    if not rows:
        raise ValueError("không có dữ liệu")
    return rows  # đã sắp xếp mới -> cũ

out = {"updated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "series": []}
for route, freq, sid, name, unit in SERIES:
    try:
        rows = fetch(route, freq, sid)
        last, prev = rows[0], (rows[1] if len(rows) > 1 else rows[0])
        v, pv = float(last["value"]), float(prev["value"])
        chg = v - pv
        pct = (chg / pv * 100) if pv else 0.0
        out["series"].append({
            "key": sid.lower(), "name": name, "unit": unit,
            "value": round(v, 2), "date": last["period"],
            "chg": round(chg, 2), "chgPct": round(pct, 2),
        })
        print(f"OK {sid}: {v} ({last['period']})")
    except Exception as e:
        out["series"].append({"key": sid.lower(), "name": name, "unit": unit, "error": str(e)})
        print(f"ERR {sid}: {e}", file=sys.stderr)

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("Đã ghi data.json")
