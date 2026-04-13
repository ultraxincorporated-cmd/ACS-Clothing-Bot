import requests
import os
import json

WEBHOOK = os.environ["WEBHOOK"]
GROUP_ID = 15938842
STATE_FILE = "seen.json"

try:
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        seen = set(json.load(f))
except:
    seen = set()

new_seen = set(seen)

def fetch_all_items():
    items = []
    cursor = None

    while True:
        url = (
            f"https://catalog.roblox.com/v1/search/items/details"
            f"?Category=3&CreatorType=2&CreatorTargetId={GROUP_ID}&Limit=30"
        )

        if cursor:
            url += f"&Cursor={cursor}"

        res = requests.get(url, timeout=15)
        data = res.json()

        items.extend(data.get("data", []))
        cursor = data.get("nextPageCursor")

        if not cursor:
            break

    return items

all_items = fetch_all_items()

for item in all_items:
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
