import json
import os
import time
from datetime import datetime
from pathlib import Path

import requests

GROUP_ID = str(os.getenv("GROUP_ID", "15938842"))
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
SEEN_PATH = Path("seen.json")

CATALOG_URL = (
    "https://catalog.roblox.com/v1/search/items/details"
    f"?Category=3&CreatorType=2&CreatorTargetId={GROUP_ID}&Limit=120&SortType=3"
)

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 ACS-Clothing-Bot"})


def load_seen():
    if not SEEN_PATH.exists():
        return set()
    try:
        data = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {str(x) for x in data}
    except Exception:
        pass
    return set()


def save_seen(seen_ids):
    SEEN_PATH.write_text(
        json.dumps(sorted(seen_ids, key=lambda x: int(x) if str(x).isdigit() else x), indent=2),
        encoding="utf-8",
    )


def get_json(url, tries=3):
    last_err = None
    for _ in range(tries):
        try:
            r = session.get(url, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = e
            time.sleep(2)
    raise last_err


def is_group_item(item):
    creator_id = (
        item.get("creatorTargetId")
        or item.get("creatorId")
        or (item.get("creator") or {}).get("id")
        or (item.get("creator") or {}).get("creatorTargetId")
    )
    return str(creator_id) == GROUP_ID


def item_type_name(item):
    return str(item.get("assetTypeName") or item.get("itemType") or "").strip()


def is_clothing(item):
    name = item_type_name(item).lower()
    asset_type_id = str(item.get("assetType") or item.get("assetTypeId") or "").strip()

    return (
        "shirt" in name
        or "pants" in name
        or "t-shirt" in name
        or "tshirt" in name
        or asset_type_id in {"2", "11", "12"}
    )


def item_id(item):
    return str(item.get("id") or item.get("itemId") or item.get("assetId") or "")


def item_name(item):
    return item.get("name") or item.get("itemName") or "Unnamed item"


def item_url(item):
    return f"https://www.roblox.com/catalog/{item_id(item)}"


def item_thumb(item):
    iid = item_id(item)
    return (
        "https://thumbnails.roblox.com/v1/assets"
        f"?assetIds={iid}&returnPolicy=PlaceHolder&size=420x420&format=Png&isCircular=false"
    )


def item_time(item):
    for key in ("created", "updated"):
        value = item.get(key)
        if value:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
            except Exception:
                pass
    iid = item_id(item)
    return float(iid) if iid.isdigit() else 0.0


def fetch_items():
    data = get_json(CATALOG_URL)
    items = data.get("data", [])
    if not isinstance(items, list):
        return []

    filtered = []
    for item in items:
        iid = item_id(item)
        if not iid:
            continue
        if not is_group_item(item):
            continue
        if not is_clothing(item):
            continue
        filtered.append(item)

    filtered.sort(key=item_time, reverse=True)
    return filtered


def post_to_discord(item):
    thumb_url = None
    try:
        thumb_data = get_json(item_thumb(item))
        thumb_url = ((thumb_data.get("data") or [{}])[0]).get("imageUrl")
    except Exception:
        thumb_url = None

    payload = {
        "embeds": [
            {
                "title": item_name(item),
                "url": item_url(item),
                "description": f"New clothing upload from group {GROUP_ID}",
                "fields": [
                    {"name": "Type", "value": item_type_name(item) or "Clothing", "inline": True},
                    {"name": "Item ID", "value": item_id(item), "inline": True},
                ],
                **({"thumbnail": {"url": thumb_url}} if thumb_url else {}),
            }
        ]
    }

    r = session.post(WEBHOOK_URL, json=payload, timeout=20)
    r.raise_for_status()


def main():
    if not WEBHOOK_URL:
        raise RuntimeError("Missing DISCORD_WEBHOOK_URL")

    seen = load_seen()
    items = fetch_items()

    current_ids = {item_id(x) for x in items}

    # First run bootstrap:
    # mark everything current as seen so it only posts future uploads
    if not seen:
        save_seen(current_ids)
        print("Initialized seen.json with current clothing items. Future uploads will post.")
        return

    new_items = [x for x in items if item_id(x) not in seen]

    if not new_items:
        print("No new clothing items found.")
        return

    # Oldest first so Discord posts in upload order
    new_items.reverse()

    for item in new_items:
        post_to_discord(item)
        seen.add(item_id(item))
        print(f"Posted: {item_name(item)} ({item_id(item)})")
        time.sleep(1)

    # Keep current known IDs too
    seen.update(current_ids)
    save_seen(seen)


if __name__ == "__main__":
    main()
