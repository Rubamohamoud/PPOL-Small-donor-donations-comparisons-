import json, os, sys, time, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone

KEY = os.environ.get("FEC_API_KEY") or "DEMO_KEY"
CYCLES = [int(c) for c in sys.argv[1:]] or [2026]
BASE = "https://api.open.fec.gov/v1"
MIN_RECEIPTS = 10000  # campaigns that raised less than this are left out

def num(v):
    return v if isinstance(v, (int, float)) else 0

def get(path, params, tries=60):
    params = dict(params, api_key=KEY)
    for _ in range(tries):
        try:
            url = BASE + path + "?" + urllib.parse.urlencode(params)
            with urllib.request.urlopen(url, timeout=60) as r:
                data = json.load(r)
            time.sleep(1)
            return data
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(90)  # rate limited or busy: wait and retry
            else:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(30)
    raise RuntimeError("FEC API kept failing: " + path)

def list_candidates(cycle):
    found = {}
    for office in ("H", "S"):
        for party in ("DEM", "REP"):
            page = 1
            while True:
                d = get("/candidates/totals/", dict(cycle=cycle, election_year=cycle,
                        office=office, party=party, per_page=100, page=page))
                for c in d.get("results", []):
                    if num(c.get("receipts")) >= MIN_RECEIPTS:
                        found[c["candidate_id"]] = (c, party, office)
                print(cycle, office, party, "list page", page)
                if page >= d.get("pagination", {}).get("pages", 0):
                    break
                page += 1
    return found

def pull(cycle):
    cands = list_candidates(cycle)
    print(cycle, ":", len(cands), "candidates raised at least", MIN_RECEIPTS)
    rows = []
    for i, (cid, (c, party, office)) in enumerate(cands.items(), 1):
        d = get("/candidate/" + cid + "/totals/",
                dict(cycle=cycle, election_full="false", per_page=20))
        results = d.get("results", [])
        res = [r for r in results if r.get("cycle") == cycle] or results
        if not res:
            continue
        t = res[0]
        unit = num(t.get("individual_unitemized_contributions"))
        item = num(t.get("individual_itemized_contributions"))
        total = num(t.get("individual_contributions")) or (unit + item)
        if total <= 0:
            continue
        rows.append({"id": cid, "name": c["name"].title(), "party": party,
                     "state": c["state"], "office": office,
                     "district": c.get("district"),
                     "inc": c.get("incumbent_challenge"),
                     "ind": total, "unit": unit})
        if i % 100 == 0:
            print(cycle, "details", i, "of", len(cands))
    return rows

def good(path):
    try:
        return any(r["unit"] > 0 for r in json.load(open(path)))
    except Exception:
        return False

os.makedirs("data", exist_ok=True)
try:
    cycles = set(json.load(open("data/manifest.json"))["cycles"])
except Exception:
    cycles = set()
newest = max(CYCLES)
for cy in CYCLES:
    path = "data/" + str(cy) + ".json"
    if cy != newest and good(path):
        print("Keeping existing", path)
        cycles.add(cy)
        continue
    rows = pull(cy)
    if not rows:
        raise SystemExit("No candidates found for " + str(cy))
    if not any(r["unit"] > 0 for r in rows):
        raise SystemExit("No unitemized amounts came back. Check the field names.")
    json.dump(rows, open(path, "w"), separators=(",", ":"))
    cycles.add(cy)
    print("Saved", len(rows), "candidates for", cy)
json.dump({"cycles": sorted(cycles, reverse=True),
           "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d")},
          open("data/manifest.json", "w"))
