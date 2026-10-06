import json, re, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "opportunities.json"

FEEDS = [
    ("Opportunity Desk", "https://opportunitydesk.org/feed/"),
    ("After School Africa", "https://www.afterschoolafrica.com/feed/"),
    ("Opportunities for Africans", "https://www.opportunitiesforafricans.com/feed/"),
]
KEYWORDS = (
    "scholarship", "fellowship", "internship", "competition", "challenge",
    "conference", "summer", "youth", "student", "coding", "stem",
    "exchange", "leadership", "training", "program"
)

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "EthioOpportunityHub/1.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()

def clean_html(s):
    return re.sub(r"<[^>]+>", " ", s or "")

def child_text(el, tag):
    x = el.find(tag)
    return (x.text or "").strip() if x is not None else ""

def parse_feed(xml, source):
    root = ET.fromstring(xml)
    found = []
    for item in root.findall(".//item"):
        title = child_text(item, "title")
        link = child_text(item, "link")
        desc = clean_html(child_text(item, "description"))
        if title and link and any(k in (title + " " + desc).lower() for k in KEYWORDS):
            found.append((title, link, source))
    return found

data = json.loads(DATA.read_text(encoding="utf-8"))
today = datetime.now(timezone.utc).date().isoformat()

# 1. AUTOMATICALLY DELETE EXPIRED OPPORTUNITIES.
# Only ISO dates are treated as deadlines. "Rolling" and blank deadlines are kept.
before = len(data["opportunities"])
active = []
for item in data["opportunities"]:
    deadline = str(item.get("deadline", "")).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", deadline) and deadline < today:
        continue
    active.append(item)
data["opportunities"] = active
print(f"Removed {before - len(active)} expired opportunities.")

# 2. ADD NEW DISCOVERIES FROM RSS FEEDS.
existing = {x.get("url") for x in data["opportunities"] + data.get("sources", [])}
for source, feed in FEEDS:
    try:
        for title, link, provider in parse_feed(fetch(feed), source):
            if link in existing:
                continue
            data["opportunities"].append({
                "title": title[:180],
                "category": "New / Needs Review",
                "country": "International",
                "funding": "Check official page",
                "age": "Check official page",
                "deadline": "",
                "url": link,
                "source": provider,
                "verified": today
            })
            existing.add(link)
    except Exception as exc:
        print(f"Skipped {feed}: {exc}")

data["lastUpdated"] = today
DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Finished: {len(data['opportunities'])} active opportunity cards.")
