import requests
import os
import json
from datetime import datetime

WEBHOOK_URL = os.getenv('WEBHOOK_URL')
SENT_DEALS_FILE = "sent_deals.json"

# List updated for 2026 hits & major franchises
AAA_KEYWORDS = [
    "cyberpunk", "baldur", "witcher", "assassin", "far cry", "watch dogs",
    "elden ring", "god of war", "horizon", "spiderman", "call of duty", 
    "battlefield", "gta", "grand theft auto", "red dead", "resident evil", 
    "monster hunter", "halo", "forza", "starfield", "fallout", "doom",
    "final fantasy", "yakuza", "like a dragon", "street fighter", "tekken",
    "hogwarts legacy", "star wars", "helldivers", "black myth", "civilization"
]

def get_gbp_rate():
    # Fallback to a standard rate if the API fails, but usually 0.75-0.80
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD")
        return r.json()["rates"].get("GBP", 0.78)
    except:
        return 0.78

def get_deals():
    # Using the AAA=1 flag from CheapShark to help filter
    url = "https://www.cheapshark.com/api/1.0/deals"
    params = {"storeID": "1", "pageSize": "60", "sortBy": "Recent", "AAA": "1"}
    resp = requests.get(url, params=params)
    return resp.json() if resp.status_code == 200 else []

def is_priority(deal):
    title = deal["title"].lower()
    normal_price = float(deal.get("normalPrice", 0))
    # Check for free games or heavy discount on AAA
    is_free = float(deal["salePrice"]) == 0
    matches_kw = any(kw in title for kw in AAA_KEYWORDS)
    is_high_value = normal_price >= 45.0 # High retail price
    return is_free or matches_kw or is_high_value

def get_already_sent():
    if os.path.exists(SENT_DEALS_FILE):
        with open(SENT_DEALS_FILE, 'r') as f:
            try: return json.load(f)
            except: return []
    return []

def save_sent_deals(deal_ids):
    with open(SENT_DEALS_FILE, 'w') as f:
        json.dump(deal_ids, f, indent=4)

# Execute
rate = get_gbp_rate()
deals = get_deals()
already_sent = get_already_sent()

# Logic: Savings >= 70% OR Price is 0.00
to_notify = []
for d in deals:
    if d["dealID"] not in already_sent:
        if float(d["savings"]) >= 70 or float(d["salePrice"]) == 0:
            if is_priority(d):
                to_notify.append(d)

if to_notify and WEBHOOK_URL:
    embeds = []
    for deal in to_notify:
        price_gbp = float(deal['salePrice']) * rate
        orig_gbp = float(deal['normalPrice']) * rate
        
        # Formatting prices
        price_text = f"£{price_gbp:.2f}" if price_gbp > 0 else "FREE"
        
        steam_id = deal.get('steamAppID')
        url = f"https://store.steampowered.com/app/{steam_id}" if steam_id else f"https://www.cheapshark.com/redirect?dealID={deal['dealID']}"
        thumb = f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{steam_id}/header.jpg" if steam_id else deal.get('thumb')

        embeds.append({
            "title": f"🎁 {deal['title']}",
            "url": url,
            "color": 0x00ff00 if price_gbp == 0 else 0xffd700,
            "thumbnail": {"url": thumb},
            "fields": [
                {"name": "Price (GBP)", "value": f"**{price_text}**", "inline": True},
                {"name": "Savings", "value": f"{round(float(deal['savings']))}% OFF", "inline": True},
                {"name": "RRP", "value": f"£{orig_gbp:.2f}", "inline": True}
            ],
            "footer": {"text": "Steam AAA Tracker • Prices converted from USD"}
        })

    # Discord allows 10 embeds per message
    for i in range(0, len(embeds), 10):
        requests.post(WEBHOOK_URL, json={"embeds": embeds[i:i+10]})

    new_history = list(set(already_sent + [d["dealID"] for d in to_notify]))
    save_sent_deals(new_history[-300:])
    print(f"Success: Sent {len(to_notify)} deals.")
else:
    print("No new deals found.")
