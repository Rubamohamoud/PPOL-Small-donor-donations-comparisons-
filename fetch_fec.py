"""Pull House and Senate candidate totals (Democrats and Republicans) from
the OpenFEC API and save them for the website.

Usage:  FEC_API_KEY=yourkey python fetch_fec.py 2026 2022
Writes data/<cycle>.json for each cycle and updates data/manifest.json.
Free key: https://api.open.fec.gov/developers/  (DEMO_KEY works but is slow)
"""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone

KEY = os.environ.get("FEC_API_KEY", "DEMO_KEY")
CYCLES = [int(c) for c in sys.argv[1:]] or [2026]
URL = "https://api.open.fec.gov/v1/candidates/totals/"

def get(params):
    for _ in range(6):
        try:
            with urllib.request.urlopen(URL + "?" + urllib.parse.urlencode(params)) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            time.sleep(60)  # rate limited: wait, then retry
    raise RuntimeError("Too many rate-limit retries")

def pull(cycle):
    rows = []
    for office in ("H", "S"):
        for party in ("DEM", "REP"):
            page = 1
            while True:
                d = get(dict(api_key=KEY, cycle=cycle, election_year=cycle,
                             election_full="true", office=office, party=party,
                             per_page=100, page=page))
                for c in d["results"]:
                    total = c.get("individual_contributions") or 0
                    if total <= 0:
                        continue
                    rows.append({
                        "id": c["candidate_id"], "name": c["name"].title(),
                        "party": party, "state": c["state"], "office": office,
                        "district": c.get("district"),
                        "inc": c.get("incumbent_challenge"),  # I, C or O (open seat)
                        "ind": total,
                        "unit": c.get("individual_unitemized_contributions") or 0,
                    })
                print(cycle, office, party, "page", page, "of", d["pagination"]["pages"])
                if page >= d["pagination"]["pages"]:
                    break
                page += 1
                time.sleep(1)
    return rows

os.makedirs("data", exist_ok=True)
try:
    cycles = set(json.load(open("data/manifest.json"))["cycles"])
except Exception:
    cycles = set()
for cy in CYCLES:
    rows = pull(cy)
    json.dump(rows, open(f"data/{cy}.json", "w"), separators=(",", ":"))
    cycles.add(cy)
    print("Saved", len(rows), "candidates for", cy)
json.dump({"cycles": sorted(cycles, reverse=True),
           "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d")},
          open("data/manifest.json", "w"))
