#!/usr/bin/env python3
"""
Bot cập nhật driver thị trường cho Freight Rate Monitor.
Nguồn: EIA Open Data API v2 (miễn phí). Ghi ra data.json để website đọc.
Cần biến môi trường EIA_API_KEY (đăng ký free tại https://www.eia.gov/opendata/register.php).
"""
import os, json, urllib.request, datetime, sys

KEY = os.environ.get("EIA_API_KEY", "").strip()
if not KEY:
    print("Thiếu EIA_API_KEY", file=sys.stderr); sys.exit(1)

# (series_id EIA, tên hiển thị, đơn vị)
SERIES = [
    ("RWTC", "Dầu thô WTI (giao ngay)", "$/bbl"),
    ("RBRTE", "Dầu Brent (giao ngay)", "$/bbl"),
    ("EER_EPMRU_PF4_Y35NY_DPG", "Xăng RBOB (NY Harbor)", "$/gal"),
    ("EER_EPD2DXL0_PF4_Y35NY_DPG", "Diesel ULSD (NY Harbor)", "$/gal"),
    ("WCESTUS1", "Tồn kho dầu thô Mỹ", "nghìn bbl"),
    ("WGTSTUS1", "Tồn kho xăng Mỹ", "nghìn bbl"),
    ("WPRSTUS1", "Tồn kho propane Mỹ", "nghìn bbl"),
    ("WCREXUS2", "Xuất khẩu dầu thô Mỹ", "nghìn bbl/ngày"),
]

def fetch(series_id):
    url = f"https://api.eia.gov/v2/seriesid/{series_id}?api_key={KEY}"
    req = urllib.request.Request(url, headers={"User-Agent": "freight-bot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    rows = d["response"]["data"]
    rows = [x for x in rows if x.get("value") is not None]
    rows.sort(key=lambda x: x["period"])
    return rows

out = {"updated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "series": []}
for sid, name, unit in SERIES:
    try:
        rows = fetch(sid)
        last, prev = rows[-1], (rows[-2] if len(rows) > 1 else rows[-1])
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
