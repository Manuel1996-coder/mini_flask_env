from flask import Flask, request, jsonify, render_template
import datetime
import openai
from dotenv import load_dotenv
import os

app = Flask(__name__)




load_dotenv()  # Lädt die .env Datei
openai.api_key = os.getenv("OPENAI_API_KEY")


tracking_data = []

@app.route('/collect', methods=['POST'])
def collect_data():
    data = request.json
    if not data:
        return jsonify({"error": "No data received"}), 400
    
    data['server_timestamp'] = datetime.datetime.utcnow().isoformat()
    tracking_data.append(data)
    
    return jsonify({"status": "success"}), 200

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

@app.route('/')
def home():
    return "Hello, Shopify World! Go to /dashboard or /recommendations."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)



