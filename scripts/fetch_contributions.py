#!/usr/bin/env python3
"""Write data/contributions.json from the GitHub GraphQL API (last 365 days).
Env: GH_TOKEN (required), GH_USER (default: buildwithpriince).
Use a PAT with read:user as GH_TOKEN to include private contributions."""
import json, os, sys, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

user = os.environ.get("GH_USER", "buildwithpriince")
token = os.environ.get("GH_TOKEN") or sys.exit("GH_TOKEN is not set")
now = datetime.now(timezone.utc)
q = """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){
contributionsCollection(from:$from,to:$to){contributionCalendar{totalContributions
weeks{contributionDays{date contributionCount}}}}}}"""
req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": q, "variables": {
        "login": user, "from": (now - timedelta(days=364)).strftime("%Y-%m-%dT00:00:00Z"),
        "to": now.strftime("%Y-%m-%dT%H:%M:%SZ")}}).encode(),
    headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"})
res = json.load(urllib.request.urlopen(req))
if "errors" in res or not res.get("data", {}).get("user"):
    sys.exit(f"GraphQL error: {res}")
cal = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]
days = [{"date": d["date"], "count": d["contributionCount"]}
        for w in cal["weeks"] for d in w["contributionDays"]]
out = Path(__file__).resolve().parent.parent / "data" / "contributions.json"
out.write_text(json.dumps({"username": user, "total": cal["totalContributions"], "days": days}, separators=(",", ":")))
print(f"{len(days)} days, {cal['totalContributions']} contributions -> {out}")
