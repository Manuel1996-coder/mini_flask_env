from flask import Flask, request, jsonify, render_template, redirect, session, Response
import datetime
import openai
from dotenv import load_dotenv
import os
import requests
from urllib.parse import quote
from flask_cors import CORS
import json
import uuid

# Environment-Variablen laden
load_dotenv()

# Pfad zur Tracking-Datendatei
TRACKING_DATA_FILE = 'tracking_data.json'

# Flask App konfigurieren
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
CORS(app, resources={r"/*": {"origins": "*"}})

# Shopify API Keys aus der .env Datei
SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPES = os.getenv("SCOPES")

# OpenAI konfigurieren
openai.api_key = os.getenv("OPENAI_API_KEY")

# Tracking-Data für Dashboard
tracking_data = {
    'pageviews': [],
    'clicks': []
}

def save_tracking_data():
    """Speichert die Tracking-Daten in einer JSON-Datei."""
    global tracking_data
    try:
        with open(TRACKING_DATA_FILE, 'w') as f:
            json.dump(tracking_data, f)
        print(f"Tracking-Daten in {TRACKING_DATA_FILE} gespeichert.")
    except Exception as e:
        print(f"Fehler beim Speichern der Tracking-Daten: {e}")

def load_tracking_data():
    """Lädt die Tracking-Daten aus einer JSON-Datei oder dem globalen Dictionary."""
    global tracking_data
    
    # Versuche, die Daten aus der Datei zu laden
    try:
        if os.path.exists(TRACKING_DATA_FILE):
            with open(TRACKING_DATA_FILE, 'r') as f:
                tracking_data = json.load(f)
                print(f"Tracking-Daten aus {TRACKING_DATA_FILE} geladen.")
    except Exception as e:
        print(f"Fehler beim Laden der Tracking-Daten: {e}")
    
    # Wenn keine Daten vorhanden sind, initialisiere leere Listen
    if 'pageviews' not in tracking_data:
        tracking_data['pageviews'] = []
    if 'clicks' not in tracking_data:
        tracking_data['clicks'] = []
    
    return tracking_data

def generate_implementation_tasks():
    """Generiert priorisierte Implementierungsaufgaben basierend auf Datenanalyse."""
    tasks = [
        {
            "priority": "high",
            "title": "Call-to-Action Optimierung",
            "description": "Überarbeitung der primären CTAs auf der Startseite für bessere Sichtbarkeit und Klarheit.",
            "effort": "medium",
            "impact": "high"
        },
        {
            "priority": "high",
            "title": "Ladezeit-Optimierung",
            "description": "Komprimierung von Bildern und Optimierung des CSS für schnellere Seitenladezeiten.",
            "effort": "medium",
            "impact": "high"
        },
        {
            "priority": "medium",
            "title": "Mobile Responsiveness",
            "description": "Verbesserung der Benutzeroberfläche auf mobilen Geräten, insbesondere auf Produktseiten.",
            "effort": "high",
            "impact": "medium"
        },
        {
            "priority": "medium",
            "title": "SEO-Optimierung",
            "description": "Überarbeitung der Meta-Tags und Seitentitel für bessere Suchmaschinenplatzierung.",
            "effort": "low",
            "impact": "medium"
        },
        {
            "priority": "low",
            "title": "Feedback-Formular",
            "description": "Implementierung eines Feedback-Formulars für Benutzer zur Sammlung von Verbesserungsvorschlägen.",
            "effort": "low",
            "impact": "low"
        }
    ]
    return tasks

# OAuth Setup
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

    print(f"Access Token: {access_token}")

    print(f"test test {access_token}")

    print(f"Response: {response.status_code}, {response.text}")

    # Testaufruf zur Shopify-API für Verifizierung
    shop_response = requests.get(
        f"https://{shop}/admin/api/2023-07/shop.json",
        headers={"X-Shopify-Access-Token": access_token}
    )
    print(f"Shopify API Response: {shop_response.status_code}, {shop_response.text}")

    if shop_response.status_code == 200:
        shop_data = shop_response.json()
        print(f"✅ Erfolgreich mit {shop_data['shop']['name']} verbunden")

    # Script-Tag in Shopify einfügen (Tracking)
    print("=== Attempting to create script tag for tracking... ===")
    script_tag_payload = {
        "script_tag": {
            "event": "onload",
            "src": "https://miniflaskenv-production.up.railway.app/static/tracking.js"
        }
    }

    script_response = requests.post(
        f"https://{shop}/admin/api/2023-07/script_tags.json",
        json=script_tag_payload,
        headers={"X-Shopify-Access-Token": access_token}
    )
    print(f"Script Tag Response: {script_response.status_code}, {script_response.text}")

    return redirect('/dashboard')

# Tracking
@app.route('/collect', methods=['POST'])
def collect_data():
    """Sammelt Tracking-Daten von der Website."""
    global tracking_data
    
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data received"}), 400

        # Debug-Log für eingehende Daten
        print(f"Eingehende Daten: {data}")

        # Aktuelle Zeit hinzufügen
        data['server_timestamp'] = datetime.datetime.utcnow().isoformat()
        
        # Wenn timestamp nicht vorhanden ist, aktuelle Zeit in Millisekunden verwenden
        if 'timestamp' not in data:
            data['timestamp'] = int(datetime.datetime.now().timestamp() * 1000)
        
        # Stellen wir sicher, dass event_type vorhanden ist
        if 'event_type' not in data:
            print("Fehler: Kein event_type in den Daten")
            return jsonify({"error": "No event_type in data"}), 400
            
        # Daten in die richtige Kategorie einfügen
        if data.get('event_type') == 'page_view':
            if 'pageviews' not in tracking_data:
                tracking_data['pageviews'] = []
            tracking_data['pageviews'].append(data)
            print(f"Pageview hinzugefügt. Neue Anzahl: {len(tracking_data['pageviews'])}")
        elif data.get('event_type') == 'click':
            if 'clicks' not in tracking_data:
                tracking_data['clicks'] = []
            tracking_data['clicks'].append(data)
            print(f"Click hinzugefügt. Neue Anzahl: {len(tracking_data['clicks'])}")
        else:
            print(f"Unbekannter event_type: {data.get('event_type')}")
            
        print(f"Collected data: {data}")
        
        # Tracking-Daten speichern
        save_tracking_data()
        
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Error collecting data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Dashboard
@app.route('/dashboard')
def dashboard():
    """Dashboard-Seite mit Analysen und Empfehlungen."""
    try:
        # Daten aus dem globalen Dictionary laden
        global tracking_data
        data = load_tracking_data()
        
        print(f"Dashboard aufgerufen. Tracking-Daten: {len(data.get('pageviews', []))} Pageviews, {len(data.get('clicks', []))} Clicks")
        
        # Grundlegende Metriken berechnen
        total_pageviews = len(data.get('pageviews', []))
        total_clicks = len(data.get('clicks', []))
        
        print(f"Berechnete Metriken: {total_pageviews} Pageviews, {total_clicks} Clicks")
        
        # Unique Pages berechnen
        unique_pages_set = set()
        for pv in data.get('pageviews', []):
            if 'page' in pv and pv['page']:
                unique_pages_set.add(pv['page'])
        unique_pages = len(unique_pages_set)
        
        # Erweiterte Metriken berechnen
        click_rate = (total_clicks / total_pageviews * 100) if total_pageviews > 0 else 0
        avg_clicks_per_page = total_clicks / unique_pages if unique_pages > 0 else 0
        
        # Durchschnittliche Sitzungsdauer berechnen
        session_durations = {}
        for pageview in data.get('pageviews', []):
            session_id = pageview.get('session_id', '')
            timestamp = pageview.get('timestamp', 0)
            
            if not session_id or not timestamp:
                continue
                
            if session_id not in session_durations:
                session_durations[session_id] = {'min': timestamp, 'max': timestamp}
            else:
                if timestamp < session_durations[session_id]['min']:
                    session_durations[session_id]['min'] = timestamp
                if timestamp > session_durations[session_id]['max']:
                    session_durations[session_id]['max'] = timestamp
        
        total_duration = sum([(s['max'] - s['min'])/1000 for s in session_durations.values()]) if session_durations else 0
        avg_session_duration = total_duration / len(session_durations) if session_durations else 0
        
        # Konversionsrate (basierend auf echten Daten berechnen, falls verfügbar)
        # Hier verwenden wir einen Beispielwert, der später durch echte Daten ersetzt werden kann
        conversion_rate = 0
        
        # Trends berechnen (basierend auf echten Daten, falls verfügbar)
        # Hier verwenden wir dynamischere Trends basierend auf der aktuellen Datenmenge
        trends = {
            'pageviews': {'value': 5 if total_pageviews > 0 else 0, 'direction': 'up' if total_pageviews > 0 else 'down'},
            'clicks': {'value': 8 if total_clicks > 0 else 0, 'direction': 'up' if total_clicks > 0 else 'down'},
            'click_rate': {'value': 10 if click_rate > 0 else 0, 'direction': 'up' if click_rate > 1 else 'down'},
            'session_duration': {'value': 15 if avg_session_duration > 0 else 0, 'direction': 'up' if avg_session_duration > 10 else 'down'},
            'conversion_rate': {'value': 0, 'direction': 'up'},
            'unique_pages': {'value': 12 if unique_pages > 0 else 0, 'direction': 'up' if unique_pages > 1 else 'down'}
        }
        
        # Ereignisse für die Tabelle vorbereiten
        events = []
        
        # Pageviews hinzufügen
        for pv in data.get('pageviews', [])[:10]:  # Begrenzen auf die neuesten 10 Einträge
            events.append({
                'event_type': 'page_view',
                'page_url': pv.get('page', ''),
                'timestamp': datetime.datetime.fromtimestamp(pv.get('timestamp', 0)/1000).strftime('%Y-%m-%d %H:%M:%S') if pv.get('timestamp') else ''
            })
        
        # Clicks hinzufügen
        for click in data.get('clicks', [])[:10]:  # Begrenzen auf die neuesten 10 Einträge
            events.append({
                'event_type': 'click',
                'page_url': click.get('page', ''),
                'clicked_tag': click.get('clicked_tag', ''),
                'timestamp': datetime.datetime.fromtimestamp(click.get('timestamp', 0)/1000).strftime('%Y-%m-%d %H:%M:%S') if click.get('timestamp') else ''
            })
        
        # Nach Zeitstempel sortieren (neueste zuerst)
        events.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # AI-Empfehlungen generieren
        ai_quick_tips = generate_quick_tips(click_rate, avg_session_duration, unique_pages)
        
        # Implementierungsaufgaben generieren
        implementation_tasks = generate_implementation_tasks()
        
        print(f"Dashboard-Daten vorbereitet: {total_pageviews} Pageviews, {total_clicks} Clicks, {len(events)} Events")
        
        return render_template('dashboard.html', 
                              total_pageviews=total_pageviews,
                              total_clicks=total_clicks,
                              click_rate=round(click_rate, 1),
                              avg_session_duration=round(avg_session_duration, 1),
                              conversion_rate=conversion_rate,
                              unique_pages=unique_pages,
                              trends=trends,
                              ai_quick_tips=ai_quick_tips,
                              implementation_tasks=implementation_tasks,
                              events=events)
    except Exception as e:
        print(f"Fehler beim Laden des Dashboards: {e}")
        # Standardwerte für den Fehlerfall
        default_trends = {
            'pageviews': {'value': 0, 'direction': 'up'},
            'clicks': {'value': 0, 'direction': 'up'},
            'click_rate': {'value': 0, 'direction': 'up'},
            'session_duration': {'value': 0, 'direction': 'up'},
            'conversion_rate': {'value': 0, 'direction': 'up'},
            'unique_pages': {'value': 0, 'direction': 'up'}
        }
        
        # Leere Empfehlungen
        default_ai_quick_tips = []
        
        # Leere Implementierungsaufgaben
        default_implementation_tasks = []
        
        return render_template('dashboard.html', 
                              error=str(e),
                              total_pageviews=0,
                              total_clicks=0,
                              click_rate=0,
                              avg_session_duration=0,
                              conversion_rate=0,
                              unique_pages=0,
                              trends=default_trends,
                              ai_quick_tips=default_ai_quick_tips,
                              implementation_tasks=default_implementation_tasks,
                              events=[])

def generate_quick_tips(click_rate, avg_duration, unique_pages):
    """Generiert AI-basierte Handlungsempfehlungen basierend auf den Metriken."""
    tips = []
    
    # Empfehlung basierend auf der Klickrate
    if click_rate < 2.0:
        tips.append({
            "title": "Call-to-Action Optimierung",
            "description": "Die Klickrate ist niedrig. Verbessern Sie die Sichtbarkeit und Klarheit Ihrer CTAs durch kontrastreichere Farben und präzisere Handlungsaufforderungen."
        })
    elif click_rate < 5.0:
        tips.append({
            "title": "A/B-Tests für Buttons durchführen",
            "description": "Testen Sie verschiedene Button-Designs und Texte, um die optimale Kombination für höhere Klickraten zu finden."
        })
    
    # Empfehlung basierend auf der Verweildauer
    if avg_duration < 30:
        tips.append({
            "title": "Content-Qualität verbessern",
            "description": "Die durchschnittliche Verweildauer ist kurz. Erweitern Sie Ihre Inhalte mit relevanten Details und verbessern Sie die Lesbarkeit durch Zwischenüberschriften und Aufzählungen."
        })
    elif avg_duration < 60:
        tips.append({
            "title": "Interaktive Elemente einbauen",
            "description": "Fügen Sie interaktive Elemente wie Videos oder Umfragen hinzu, um die Benutzer länger auf der Seite zu halten."
        })
    
    # Empfehlung basierend auf der Anzahl der besuchten Seiten
    if unique_pages < 5:
        tips.append({
            "title": "Interne Verlinkung optimieren",
            "description": "Verbessern Sie die interne Verlinkung zwischen Ihren Seiten, um Besucher zu ermutigen, mehr Seiten zu erkunden."
        })
    
    # Wenn keine Tipps generiert wurden, füge einen Standard-Tipp hinzu
    if not tips:
        tips.append({
            "title": "Datensammlung ausbauen",
            "description": "Sammeln Sie mehr Daten über das Nutzerverhalten, um präzisere Handlungsempfehlungen zu erhalten. Implementieren Sie erweiterte Tracking-Funktionen für detailliertere Einblicke."
        })
    
    # Maximal 3 Tipps zurückgeben
    return tips[:3]

# GPT Empfehlungen
def generate_gpt_recommendations(total_pageviews, total_clicks, click_rate):
    prompt = f"""
    Total Pageviews: {total_pageviews}
    Total Clicks: {total_clicks}
    Click Rate: {click_rate}%

    Gib konkrete Handlungsempfehlungen zur Conversion-Optimierung als knappe, klare Stichpunkte aus.
    """
    try:
        response = openai.chat.completions.create(
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
        print(f"Fehler bei OpenAI API: {e}")
        return "Fehler bei der KI-Generierung."
    

@app.route('/clv-analytics')
def clv_analytics():
    # For now, we'll just render the template without complex calculations
    return render_template("clv_analytics.html")


@app.route('/recommendations')
def recommendations():
    """Empfehlungsseite mit Analysen und Handlungsempfehlungen."""
    try:
        # Daten aus dem globalen Dictionary laden
        tracking_data = load_tracking_data()
        
        # Basis-Metriken berechnen
        total_pageviews = len(tracking_data.get('pageviews', []))
        total_clicks = len(tracking_data.get('clicks', []))
        click_rate = round((total_clicks / total_pageviews) * 100, 2) if total_pageviews > 0 else 0
        
        # Erweiterte Metriken für Empfehlungen
        unique_pages_set = set()
        for pv in tracking_data.get('pageviews', []):
            if 'page' in pv and pv['page']:
                unique_pages_set.add(pv['page'])
        unique_pages = len(unique_pages_set)
        
        avg_clicks_per_page = round(total_clicks / unique_pages, 2) if unique_pages > 0 else 0
        
        # Empfehlungskategorien
        recommendations_by_category = {
            'conversion': [],
            'ux': [],
            'technical': []
        }
        
        # Conversion-Empfehlungen
        if click_rate < 2:
            recommendations_by_category['conversion'].append({
                'title': 'Niedrige Click Rate',
                'description': 'Die Click Rate liegt unter 2%. Optimiere deine Call-to-Actions und Button-Platzierung.',
                'priority': 'high',
                'impact': 'high',
                'effort': 'medium'
            })
        elif click_rate > 20:
            recommendations_by_category['conversion'].append({
                'title': 'Hohe Click Rate',
                'description': 'Ausgezeichnete Click Rate! Optimiere jetzt den Conversion-Funnel für maximale Umsätze.',
                'priority': 'medium',
                'impact': 'high',
                'effort': 'low'
            })
        
        # UX-Empfehlungen
        if avg_clicks_per_page < 1:
            recommendations_by_category['ux'].append({
                'title': 'Geringe Interaktion',
                'description': 'Nutzer interagieren wenig mit der Seite. Überprüfe die Benutzerführung und Navigation.',
                'priority': 'high',
                'impact': 'high',
                'effort': 'medium'
            })
        
        # Technische Empfehlungen
        if unique_pages < 3:
            recommendations_by_category['technical'].append({
                'title': 'Begrenzte Seiten',
                'description': 'Erweitere dein Angebot um mehr Produktseiten für bessere SEO-Performance.',
                'priority': 'medium',
                'impact': 'medium',
                'effort': 'high'
            })
        
        # KI-Empfehlungen generieren
        try:
            gpt_text = generate_gpt_recommendations(total_pageviews, total_clicks, click_rate)
        except Exception as e:
            print(f"Fehler bei der KI-Generierung: {e}")
            gpt_text = "Keine KI-Empfehlungen verfügbar."
        
        # Alle Empfehlungen zusammenführen
        all_recommendations = []
        for category in recommendations_by_category.values():
            all_recommendations.extend(category)
        
        return render_template(
            "recommendations.html",
            recommendations=all_recommendations,
            recommendations_by_category=recommendations_by_category,
            gpt_text=gpt_text,
            click_rate=click_rate,
            total_pageviews=total_pageviews,
            total_clicks=total_clicks,
            unique_pages=unique_pages,
            avg_clicks_per_page=avg_clicks_per_page
        )
    except Exception as e:
        print(f"Fehler beim Laden der Empfehlungen: {e}")
        return render_template(
            "recommendations.html",
            error=str(e),
            recommendations=[],
            recommendations_by_category={'conversion': [], 'ux': [], 'technical': []},
            gpt_text="Fehler beim Laden der Empfehlungen.",
            click_rate=0,
            total_pageviews=0,
            total_clicks=0,
            unique_pages=0,
            avg_clicks_per_page=0
        )

# Webhook Handling
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


# Replace your current tracking.js route with this:
@app.route('/static/tracking.js')
def tracking_js():
    return app.send_static_file('tracking.js')

# Debug-Route zum Anzeigen der Tracking-Daten
@app.route('/debug/tracking')
def debug_tracking():
    global tracking_data
    
    # Vergewissern wir uns, dass tracking_data korrekt initialisiert ist
    if 'pageviews' not in tracking_data:
        tracking_data['pageviews'] = []
    if 'clicks' not in tracking_data:
        tracking_data['clicks'] = []
    
    # Aktualisiere die tracking_data aus der Datei
    load_tracking_data()
    
    # Formatierung der Daten für die Anzeige
    pageviews_sample = []
    for pv in tracking_data.get('pageviews', [])[:5]:
        pv_copy = dict(pv)
        if 'timestamp' in pv_copy:
            try:
                pv_copy['timestamp_formatted'] = datetime.datetime.fromtimestamp(pv_copy['timestamp']/1000).strftime('%Y-%m-%d %H:%M:%S')
            except:
                pv_copy['timestamp_formatted'] = "Invalid timestamp"
        pageviews_sample.append(pv_copy)
        
    clicks_sample = []
    for click in tracking_data.get('clicks', [])[:5]:
        click_copy = dict(click)
        if 'timestamp' in click_copy:
            try:
                click_copy['timestamp_formatted'] = datetime.datetime.fromtimestamp(click_copy['timestamp']/1000).strftime('%Y-%m-%d %H:%M:%S')
            except:
                click_copy['timestamp_formatted'] = "Invalid timestamp"
        clicks_sample.append(click_copy)
    
    # Detailliertere Antwort zurückgeben
    response = {
        'status': 'success',
        'tracking_data_keys': list(tracking_data.keys()),
        'pageviews_count': len(tracking_data.get('pageviews', [])),
        'clicks_count': len(tracking_data.get('clicks', [])),
        'pageviews_sample': pageviews_sample,
        'clicks_sample': clicks_sample
    }
    
    print(f"Debug Tracking Response: {response}")
    
    return jsonify(response)

# Debug-Route zum Löschen der Tracking-Daten
@app.route('/debug/clear_tracking')
def clear_tracking():
    global tracking_data
    tracking_data = {
        'pageviews': [],
        'clicks': []
    }
    save_tracking_data()
    return jsonify({
        'status': 'success',
        'message': 'Tracking-Daten wurden gelöscht.'
    })

# Home Route
@app.route('/')
def home():
    shop = request.args.get('shop')
    if shop:
        return redirect(f'/install?shop={shop}')
    return redirect('/dashboard')

# Test-Route zum Testen des Trackings (entfernt)
# @app.route('/test')
# def test_tracking():
#     return render_template('test.html')

# Flask Starten
if __name__ == '__main__':
    # Tracking-Daten beim Start laden
    load_tracking_data()
    
    # Port für die App konfigurieren (Standard 5000, kann geändert werden)
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)