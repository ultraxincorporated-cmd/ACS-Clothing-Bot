import requests
import os
import json

WEBHOOK = os.environ["WEBHOOK"]
GROUP_ID = 15938842
STATE_FILE = "seen.json"
LIMIT = 64

try:
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        seen = set(json.load(f))
except:
    seen = set()

url = (
    f"https://catalog.roblox.com/v1/search/items/details"
    f"?Category=3&CreatorType=2&CreatorTargetId={GROUP_ID}&Limit={LIMIT}"
)

res = requests.get(url, timeout=20)
data = res.json()

new_seen = set(seen)

for item in data.get("data", []):
    item_id = str(item.get("id"))
    name = item.get("name", "New clothing")

    if not item_id or item_id == "None":
        continue

    if item_id not in seen:
        link = f"https://www.roblox.com/catalog/{item_id}"
        requests.post(
            WEBHOOK,
            json={"content": f"NEW RELEASE: {name}\n{link}"},
            timeout=15
        )
        new_seen.add(item_id)

with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(list(new_seen), f)
