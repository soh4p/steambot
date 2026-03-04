import requests, os, json, time
from datetime import datetime


WEBHOOK = os.getenv('WEBHOOK_URL')
DB_FILE = "sent_deals.json"
ROLE_ID = "1478500037955948624"
STORES = {"1": "Steam", "7": "GOG", "25": "Epic"}

def get_rate():
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        return r.json()["rates"].get("GBP", 0.78)
    except:
        return 0.78

def fetch_deals():
    params = {
        "storeID": "1,7,25",
        "upperPrice": "50",
        "metacritic": "70",
        "steamRating": "75",
        "minimumReviewCount": "500",
        "onSale": "1",
        "AAA": "1"
    }
    try:
        r = requests.get("https://www.cheapshark.com/api/1.0/deals", params=params, timeout=15)
        return r.json() if r.status_code == 200 else []
    except:
        return []


history = []
if os.path.exists(DB_FILE):
    with open(DB_FILE, 'r') as f:
        try: history = json.load(f)
        except: pass

fx = get_rate()
deals = fetch_deals()
new_items = []

for d in deals:
    if d['dealID'] not in history:
        
        if float(d['savings']) >= 70 or float(d['salePrice']) == 0:
            new_items.append(d)

if new_items and WEBHOOK:
    embeds = []
    for d in new_items:
        now_p = float(d['salePrice']) * fx
        old_p = float(d['normalPrice']) * fx
        tag = f"£{now_p:.2f}" if now_p > 0 else "FREE"

        embeds.append({
            "title": f"🎁 {d['title']}",
            "url": f"https://www.cheapshark.com/redirect?dealID={d['dealID']}",
            "description": f"On **{STORES.get(d['storeID'], 'Store')}**",
            "color": 0x00ff00 if now_p == 0 else 0xffd700,
            "thumbnail": {"url": d.get('thumb')},
            "fields": [
                {"name": "Price", "value": f"**{tag}**", "inline": True},
                {"name": "Off", "value": f"{round(float(d['savings']))}%", "inline": True},
                {"name": "RRP", "value": f"£{old_p:.2f}", "inline": True}
            ],
            "footer": {"text": f"Rate: {fx:.2f}"}
        })

   
    for i in range(0, len(embeds), 10):
        payload = {"embeds": embeds[i:i+10]}
        if i == 0:
            payload["content"] = f"<@&{ROLE_ID}> New AAA Deals!"
        
        requests.post(WEBHOOK, json=payload, timeout=10)
        time.sleep(1) 

    
    history = list(set(history + [x['dealID'] for x in new_items]))[-500:]
    with open(DB_FILE, 'w') as f:
        json.dump(history, f, indent=4)
    print(f"Sent {len(new_items)} deals.")

elif WEBHOOK:
    
    ts = datetime.now().strftime('%H:%M')
    requests.post(WEBHOOK, json={
        "embeds": [{"description": f"🔍 Scan complete at {ts}. No new deals.", "color": 0x2b2d31}]
    }, timeout=10)
