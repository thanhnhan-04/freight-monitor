#!/usr/bin/env python3
"""
Fetch recent public RSS items for the Freight Rate Monitor news tab.

This intentionally uses only Python stdlib so it can run inside GitHub Actions
without package installs. It does not generate analyst commentary; it keeps the
source title and a short RSS-provided excerpt, then tags each item by segment.
"""
import datetime as dt
import email.utils
import html
import json
import re
import ssl
import sys
import urllib.request
import xml.etree.ElementTree as ET


FEEDS = [
    ("Hellenic Shipping News", "https://www.hellenicshippingnews.com/feed/"),
    ("Splash247", "https://splash247.com/feed/"),
    ("gCaptain", "https://gcaptain.com/feed/"),
]

SEGMENT_KEYWORDS = {
    "lpg": [
        "lpg", "vlgc", "propane", "butane", "ammonia", "gas carrier",
        "gas carriers", "gas shipping", "exmar",
    ],
    "dry": [
        "dry bulk", "capesize", "panamax", "supramax", "handysize", "bdi",
        "coal", "iron ore", "grain", "bauxite", "bulker", "bulk carrier",
    ],
    "product": [
        "clean tanker", "clean tankers", "product tanker", "product tankers",
        "mr tanker", "lr2", "lr1", "tc1", "tc2", "tc14", "diesel",
        "gasoil", "gasoline", "jet fuel", "naphtha",
    ],
    "crude": [
        "dirty tanker", "dirty tankers", "vlcc", "suezmax", "aframax",
        "td3c", "crude", "oil tanker", "oil tankers", "cpc", "hormuz",
    ],
    "macro": [
        "freight", "rates", "red sea", "bab el-mandeb", "suez", "panama",
        "black sea", "chokepoint", "tariff", "sanction", "reroute",
        "rerouting", "port", "ports", "shipping disruption",
    ],
}

RELEVANCE_KEYWORDS = sorted({
    kw for kws in SEGMENT_KEYWORDS.values() for kw in kws
} | {
    "tanker", "tankers", "commodity", "commodities", "ton-mile",
    "tonne-mile", "vessel", "vessels", "fixture", "fixtures", "charter",
    "chartering", "spot rate", "spot rates", "fleet", "orderbook",
})


def fetch_xml(url):
    req = urllib.request.Request(url, headers={"User-Agent": "freight-news-bot"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if not isinstance(reason, ssl.SSLCertVerificationError):
            raise
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=30, context=context) as resp:
            return resp.read()


def text_of(node, tag):
    found = node.find(tag)
    if found is not None and found.text:
        return found.text.strip()
    return ""


def strip_html(value):
    value = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def truncate(value, limit=220):
    if len(value) <= limit:
        return value
    clipped = value[:limit].rsplit(" ", 1)[0].rstrip(".,;:")
    return clipped + "..."


def parse_date(value):
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except Exception:
        return None


def classify(title, desc):
    title_hay = title.lower()
    desc_hay = desc.lower()
    title_scores = {}
    scores = {}
    for seg, keywords in SEGMENT_KEYWORDS.items():
        title_score = sum(1 for kw in keywords if kw in title_hay)
        score = title_score * 3
        score += sum(1 for kw in keywords if kw in desc_hay)
        if title_score:
            title_scores[seg] = title_score
        if score:
            scores[seg] = score
    if not scores:
        return None
    title_commodity = {k: v for k, v in title_scores.items() if k != "macro"}
    if title_commodity:
        return max(title_commodity.items(), key=lambda kv: kv[1])[0]
    commodity_scores = {k: v for k, v in scores.items() if k != "macro"}
    if commodity_scores:
        return max(commodity_scores.items(), key=lambda kv: kv[1])[0]
    if scores.get("macro", 0) >= 2:
        return "macro"
    return None


def relevance(title, desc):
    hay = f"{title} {desc}".lower()
    return sum(1 for kw in RELEVANCE_KEYWORDS if kw in hay)


def parse_feed(source, xml_bytes):
    root = ET.fromstring(xml_bytes)
    items = []
    for item in root.findall(".//item"):
        title = strip_html(text_of(item, "title"))
        link = text_of(item, "link")
        desc = strip_html(text_of(item, "description"))
        pub = parse_date(text_of(item, "pubDate"))
        if not title or not link:
            continue
        seg = classify(title, desc)
        score = relevance(title, desc)
        if not seg or score < 2:
            continue
        items.append({
            "published": pub.isoformat() if pub else "",
            "sort_ts": pub.timestamp() if pub else 0,
            "d": pub.strftime("%d/%m") if pub else "",
            "s": seg,
            "t": truncate(title, 120),
            "x": truncate(desc, 220),
            "su": source,
            "url": link,
            "score": score,
        })
    return items


def main():
    all_items = []
    errors = []
    for source, url in FEEDS:
        try:
            all_items.extend(parse_feed(source, fetch_xml(url)))
        except Exception as exc:
            errors.append(f"{source}: {exc}")

    seen = set()
    source_counts = {}
    segment_counts = {}
    unique = []
    for item in sorted(all_items, key=lambda x: (x["sort_ts"], x["score"]), reverse=True):
        key = item["url"].split("?")[0].rstrip("/")
        if key in seen:
            continue
        if source_counts.get(item["su"], 0) >= 6:
            continue
        if item["s"] == "macro" and segment_counts.get("macro", 0) >= 4:
            continue
        seen.add(key)
        source_counts[item["su"]] = source_counts.get(item["su"], 0) + 1
        segment_counts[item["s"]] = segment_counts.get(item["s"], 0) + 1
        item.pop("sort_ts", None)
        item.pop("score", None)
        unique.append(item)
        if len(unique) >= 12:
            break

    if not unique:
        print("No relevant news items fetched", file=sys.stderr)
        for err in errors:
            print("ERR", err, file=sys.stderr)
        return 1

    out = {
        "date": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
        "items": unique,
    }
    if errors:
        out["errors"] = errors

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote news.json with {len(unique)} items")
    for item in unique[:5]:
        print(f"OK {item['d']} {item['s']}: {item['t']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
