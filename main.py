import requests
import os
import json
from datetime import datetime


WEBHOOK_URL = os.getenv('WEBHOOK_URL')
SENT_DEALS_FILE = "sent_deals.json"
PINGME_ROLE_ID = "1478500037955948624" 

STORE_NAMES = {
    "1": "Steam",
    "7": "GOG",
    "25": "Epic Games Store"
}

def get_gbp_rate():
    """Fetch real-time USD to GBP exchange rate."""
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD")
        return r.json()["rates"].get("GBP", 0.78)
    except:
        return 0.78

def get_deals():
    """Fetch deals specifically for Steam, GOG, and Epic."""
    url = "https://www.cheapshark.com/api/1.0/deals"
    params = {
        "storeID": "1,7,25",
        "upperPrice": "50",
        "metacritic": "70",
        "steamRating": "75",
        "minimumReviewCount": "500",
        "onSale": "1",
        "AAA": "1"
    }
    resp = requests.get(url, params=params)
    return resp.json() if resp.status_code == 200 else []

def get_already_sent():
    """Load history of sent deals to avoid duplicates."""
    if os.path.exists(SENT_DEALS_FILE):
        with open(SENT_DEALS_FILE, 'r') as f:
            try: 
                return json.load(f)
            except: 
                return []
    return []

def save_sent_deals(deal_ids):
    """Save updated deal history (limited to last 300)."""
    with open(SENT_DEALS_FILE, 'w') as f:
        json.dump(deal_ids[-300:], f, indent=4)


rate = get_gbp_rate()
deals = get_deals()
already_sent = get_already_sent()

to_notify = []
for d in deals:
    if d["dealID"] not in already_sent:
       
        if float(d["savings"]) >= 70 or float(d["salePrice"]) == 0:
            to_notify.append(d)

if to_notify and WEBHOOK_URL:
    embeds = []
    for deal in to_notify:
        price_gbp = float(deal['salePrice']) * rate
        orig_gbp = float(deal['normalPrice']) * rate
        store_id = deal.get('storeID')
        store_name = STORE_NAMES.get(store_id, "Retailer")
        
        price_text = f"£{price_gbp:.2f}" if price_gbp > 0 else "FREE"
        url = f"https://www.cheapshark.com/redirect?dealID={deal['dealID']}"
        thumb = deal.get('thumb')

        embeds.append({
            "title": f"🎁 {deal['title']}",
            "url": url,
            "description": f"Available on **{store_name}**",
            "color": 0x00ff00 if price_gbp == 0 else 0xffd700,
            "thumbnail": {"url": thumb},
            "fields": [
                {"name": "Sale Price", "value": f"**{price_text}**", "inline": True},
                {"name": "Discount", "value": f"{round(float(deal['savings']))}% OFF", "inline": True},
                {"name": "RRP (GBP)", "value": f"£{orig_gbp:.2f}", "inline": True}
            ],
            "footer": {"text": f"Global Game Tracker | GBP Rate: {rate:.2f}"}
        })

   
    for i in range(0, len(embeds), 10):
        payload = {"embeds": embeds[i:i+10]}
        
       
        if i == 0:
            payload["content"] = f"<@&{PINGME_ROLE_ID}> New AAA Deals Detected!"
            
        requests.post(WEBHOOK_URL, json=payload)

    
    new_history = list(set(already_sent + [d["dealID"] for d in to_notify]))
    save_sent_deals(new_history)
    print(f"Success: Sent {len(to_notify)} deals.")

elif WEBHOOK_URL:
   
    now = datetime.now().strftime("%H:%M")
    payload = {
        "embeds": [{
            "description": f"🔍 Scan complete at **{now}**. No new AAA deals found on Steam, GOG, or Epic.",
            "color": 0x2b2d31 
        }]
    }
    requests.post(WEBHOOK_URL, json=payload)
    print("Logged: No new deals found.")
