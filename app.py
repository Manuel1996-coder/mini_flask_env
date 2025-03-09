from flask import Flask, request, jsonify, render_template, redirect, session
import datetime
import openai
from dotenv import load_dotenv
import os
import requests
from urllib.parse import quote

# ====================
# 🌍 Environment-Variablen laden
# ====================
load_dotenv()

# Flask App konfigurieren
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Shopify API Keys aus der .env Datei
SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPES = os.getenv("SCOPES")

# OpenAI konfigurieren
openai.api_key = os.getenv("OPENAI_API_KEY")

# Tracking-Data für Dashboard
tracking_data = []


# ====================
# 🚀 OAuth Setup
# ====================
@app.route('/install')
def install():
    shop = request.args.get("shop")
    print(f"Shop: {shop}")
    print(f"SHOPIFY_API_KEY: {SHOPIFY_API_KEY}")
    print(f"SCOPES: {SCOPES}")
    print(f"REDIRECT_URI: {REDIRECT_URI}")
    
    if not shop:
        return "Missing shop parameter", 400
    
    install_url = f"https://{shop}/admin/oauth/authorize?client_id={SHOPIFY_API_KEY}&scope={quote(SCOPES)}&redirect_uri={quote(REDIRECT_URI)}"
    print(f"Install URL: {install_url}")
    return redirect(install_url)



@app.route('/auth/callback')
def auth_callback():
    shop = request.args.get("shop")
    code = request.args.get("code")
    print(f"Shop: {shop}, Code: {code}")

    if not shop or not code:
        return "Missing parameters", 400
    
    payload = {
        "client_id": SHOPIFY_API_KEY,
        "client_secret": SHOPIFY_API_SECRET,
        "code": code
    }

    print(f"Sending payload: {payload}")

    response = requests.post(f"https://{shop}/admin/oauth/access_token", json=payload)
    print(f"Response: {response.status_code}, {response.text}")

    if response.status_code != 200:
        return f"Failed to authenticate with Shopify: {response.text}", 400

    access_token = response.json().get("access_token")
    session['shop'] = shop
    session['access_token'] = access_token

    # ✅ Testaufruf zur Shopify-API für Verifizierung
    shop_response = requests.get(
        f"https://{shop}/admin/api/2023-07/shop.json",
        headers={"X-Shopify-Access-Token": access_token}
    )
    print(f"Shopify API Response: {shop_response.status_code}, {shop_response.json()}")

    if shop_response.status_code == 200:
        shop_data = shop_response.json()
        print(f"✅ Erfolgreich mit {shop_data['shop']['name']} verbunden")

    return redirect('/dashboard')



# ====================
# 🚀 Tracking
# ====================
@app.route('/collect', methods=['POST'])
def collect_data():
    data = request.json
    if not data:
        return jsonify({"error": "No data received"}), 400
    
    data['server_timestamp'] = datetime.datetime.utcnow().isoformat()
    tracking_data.append(data)
    
    return jsonify({"status": "success"}), 200


# ====================
# 📊 Dashboard
# ====================
@app.route('/dashboard')
def dashboard():
    total_pageviews = sum(1 for e in tracking_data if e.get('event_type') == 'page_view')
    total_clicks = sum(1 for e in tracking_data if e.get('event_type') == 'click')
    unique_pages = len(set(e.get('page_url') for e in tracking_data))
    click_rate = round((total_clicks / total_pageviews) * 100, 2) if total_pageviews else 0

    return render_template(
        "dashboard.html",
        events=tracking_data,
        total_pageviews=total_pageviews,
        total_clicks=total_clicks,
        unique_pages=unique_pages,
        click_rate=click_rate
    )


# ====================
# 🤖 GPT Empfehlungen
# ====================
def generate_gpt_recommendations(total_pageviews, total_clicks, click_rate):
    prompt = f"""
    Total Pageviews: {total_pageviews}
    Total Clicks: {total_clicks}
    Click Rate: {click_rate}%

    Gib konkrete Handlungsempfehlungen zur Conversion-Optimierung als knappe, klare Stichpunkte aus.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Du bist Experte für Conversion-Optimierung."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("Fehler bei OpenAI API:", e)
        return "Fehler bei der KI-Generierung."


@app.route('/recommendations')
def recommendations():
    total_pageviews = sum(1 for e in tracking_data if e.get('event_type') == 'page_view')
    total_clicks = sum(1 for e in tracking_data if e.get('event_type') == 'click')
    click_rate = round((total_clicks / total_pageviews) * 100, 2) if total_pageviews > 0 else 0

    rec_list = []
    if total_pageviews == 0:
        rec_list.append("🚨 Keine Besucher! Nutze SEO, Social Media oder Ads.")
    elif click_rate < 2:
        rec_list.append("📉 Click Rate niedrig! Optimiere Buttons und CTAs.")
    elif click_rate > 20:
        rec_list.append("🔥 Click Rate top! Optimiere Funnel weiter.")

    # GPT-Call
    gpt_text = generate_gpt_recommendations(total_pageviews, total_clicks, click_rate)

    return render_template(
        "recommendations.html",
        recommendations=rec_list,
        gpt_text=gpt_text,
        click_rate=click_rate,
        total_pageviews=total_pageviews,
        total_clicks=total_clicks
    )


# ====================
# 📦 Webhook Handling
# ====================
@app.route('/webhook/orders/create', methods=['POST'])
def orders_create():
    data = request.json
    print("New order:", data)
    return "", 200


@app.route('/webhook/customers/create', methods=['POST'])
def customers_create():
    data = request.json
    print("New customer:", data)
    return "", 200


# ====================
# 🏡 Home Route
# ====================
@app.route('/')
def home():
    shop = request.args.get('shop')
    if shop:
        return redirect(f'/install?shop={shop}')
    return "Hello, Shopify World! Go to /dashboard or /recommendations."


# ====================
# 🏆 Flask Starten
# ====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

