const fs = require("fs");

const WEBHOOK = process.env.DISCORD_WEBHOOK_URL;
const GROUP_ID = String(process.env.GROUP_ID || "15938842");

// change this if your current endpoint is different
const CATALOG_API =
  `https://catalog.roblox.com/v1/search/items/details?Category=3&CreatorType=2&CreatorTargetId=${GROUP_ID}&Limit=120&SortType=3`;

if (!WEBHOOK) {
  throw new Error("Missing DISCORD_WEBHOOK_URL secret");
}

const SEEN_FILE = "seen.json";

function loadSeen() {
  try {
    const raw = fs.readFileSync(SEEN_FILE, "utf8");
    const parsed = JSON.parse(raw);
    return new Set(Array.isArray(parsed) ? parsed.map(String) : []);
  } catch {
    return new Set();
  }
}

function saveSeen(seen) {
  fs.writeFileSync(SEEN_FILE, JSON.stringify([...seen], null, 2));
}

async function fetchJson(url) {
  const res = await fetch(url, {
    headers: {
      "User-Agent": "Mozilla/5.0"
    }
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Request failed ${res.status}: ${text}`);
  }

  return res.json();
}

function isClothing(item) {
  const t = String(item.assetTypeName || item.itemType || "").toLowerCase();
  return (
    t.includes("shirt") ||
    t.includes("pants") ||
    t.includes("t-shirt") ||
    t.includes("tshirt")
  );
}

function isFromTargetGroup(item) {
  const creatorId =
    item.creatorTargetId ??
    item.creatorId ??
    item.creator?.id ??
    item.creator?.creatorTargetId;

  const creatorType =
    String(item.creatorType ?? item.creator?.type ?? "").toLowerCase();

  return String(creatorId) === GROUP_ID && (creatorType === "group" || creatorType === "2" || creatorType === "");
}

function getItemId(item) {
  return String(item.id ?? item.itemId ?? item.assetId);
}

function getItemName(item) {
  return item.name ?? item.itemName ?? "Unnamed item";
}

function getItemUrl(item) {
  const id = getItemId(item);
  return `https://www.roblox.com/catalog/${id}`;
}

function getThumbUrl(item) {
  const id = getItemId(item);
  return `https://thumbnails.roblox.com/v1/assets?assetIds=${id}&returnPolicy=PlaceHolder&size=420x420&format=Png&isCircular=false`;
}

async function postToDiscord(item) {
  const thumbApi = await fetchJson(getThumbUrl(item)).catch(() => null);
  const imageUrl = thumbApi?.data?.[0]?.imageUrl || null;

  const body = {
    embeds: [
      {
        title: getItemName(item),
        url: getItemUrl(item),
        description: `New clothing upload from group ${GROUP_ID}`,
        fields: [
          {
            name: "Type",
            value: String(item.assetTypeName || item.itemType || "Clothing"),
            inline: true
          },
          {
            name: "Item ID",
            value: getItemId(item),
            inline: true
          }
        ],
        image: imageUrl ? { url: imageUrl } : undefined
      }
    ]
  };

  const res = await fetch(WEBHOOK, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Discord webhook failed ${res.status}: ${text}`);
  }
}

async function main() {
  const seen = loadSeen();
  const json = await fetchJson(CATALOG_API);

  const items = Array.isArray(json.data) ? json.data : [];

  const filtered = items
    .filter(isClothing)
    .filter(isFromTargetGroup)
    .sort((a, b) => {
      const ad = new Date(a.created || a.updated || a.lowestPrice || 0).getTime();
      const bd = new Date(b.created || b.updated || b.lowestPrice || 0).getTime();
      return bd - ad;
    });

  const fresh = filtered.filter((item) => !seen.has(getItemId(item)));

  if (fresh.length === 0) {
    console.log("No new clothing items found.");
    return;
  }

  // oldest first so Discord posts in upload order
  fresh.reverse();

  for (const item of fresh) {
    await postToDiscord(item);
    seen.add(getItemId(item));
    console.log(`Posted: ${getItemName(item)} (${getItemId(item)})`);
  }

  saveSeen(seen);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
