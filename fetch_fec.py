import json, os, sys, time, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone

KEY = os.environ.get("FEC_API_KEY") or "DEMO_KEY"
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

def num(v):
    return v if isinstance(v, (int, float)) else 0

def pull(cycle):
    rows, shown = [], False
    for office in ("H", "S"):
        for party in ("DEM", "REP"):
            page = 1
            while True:
                d = get(dict(api_key=KEY, cycle=cycle, election_year=cycle,
                             office=office, party=party, per_page=100, page=page))
                results = d.get("results", [])
                pages = d.get("pagination", {}).get("pages", 0)
                print(cycle, office, party, "page", page, "of", pages, "-", len(results), "results")
                if results and not shown:
                    print("Example record fields:", sorted(results[0].keys()))
                    shown = True
                for c in results:
                    unit = num(c.get("individual_unitemized_contributions"))
                    item = num(c.get("individual_itemized_contributions"))
                    total = num(c.get("individual_contributions")) or (unit + item)
                    if total <= 0:
                        continue
                    rows.append({
                        "id": c["candidate_id"], "name": c["name"].title(),
                        "party": party, "state": c["state"], "office": office,
                        "district": c.get("district"),
                        "inc": c.get("incumbent_challenge"),
                        "ind": total, "unit": unit,
                    })
                if page >= pages:
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
    if not rows:
        raise SystemExit("No candidates found for " + str(cy) + ". See the log lines above.")
    json.dump(rows, open("data/" + str(cy) + ".json", "w"), separators=(",", ":"))
    cycles.add(cy)
    print("Saved", len(rows), "candidates for", cy)
json.dump({"cycles": sorted(cycles, reverse=True),
           "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d")},
          open("data/manifest.json", "w"))
