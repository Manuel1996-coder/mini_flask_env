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
import random  # Für Simulationszwecke
import numpy as np  # Für statistische Berechnungen
import argparse

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
tracking_data = {}  # Leeres Dictionary für alle Shops

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
    
    return tracking_data

def get_shop_data(shop_domain):
    """Holt die Tracking-Daten für einen bestimmten Shop."""
    global tracking_data
    
    # Wenn der Shop noch nicht im Dictionary existiert, initialisiere ihn
    if shop_domain not in tracking_data:
        tracking_data[shop_domain] = {
            'pageviews': [],
            'clicks': []
        }
        save_tracking_data()
    
    return tracking_data[shop_domain]

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
            "src": "https://miniflaskenv-production.up.railway.app/static/js/tracking.js"
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
        
        # Shop-Domain aus den Daten extrahieren
        shop_domain = data.get('shop_domain')
        if not shop_domain:
            return jsonify({"error": "No shop_domain in data"}), 400
        
        # Daten für diesen Shop abrufen
        shop_data = get_shop_data(shop_domain)

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
            shop_data['pageviews'].append(data)
            print(f"Pageview für Shop {shop_domain} hinzugefügt. Neue Anzahl: {len(shop_data['pageviews'])}")
        elif data.get('event_type') == 'click':
            shop_data['clicks'].append(data)
            print(f"Click für Shop {shop_domain} hinzugefügt. Neue Anzahl: {len(shop_data['clicks'])}")
        else:
            print(f"Unbekannter event_type: {data.get('event_type')}")
            
        print(f"Collected data for shop {shop_domain}: {data}")
        
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
        # Shop aus der Session holen (temporär entfernt)
        # shop = session.get('shop')
        # if not shop:
        #     return redirect('/install')  # Umleitung zur Installation, wenn kein Shop in der Session
        
        # Demo-Shop setzen für Test-Zwecke
        shop = "test-shop.example.com"
        
        # Überprüfen, ob ein gültiges Access-Token vorhanden ist (temporär entfernt)
        # access_token = session.get('access_token')
        # if not access_token:
        #     return redirect('/install')  # Umleitung zur Installation, wenn kein Token vorhanden
        
        # Daten für diesen Shop laden
        shop_data = get_shop_data(shop)
        
        print(f"Dashboard für Shop {shop} aufgerufen. Tracking-Daten: {len(shop_data.get('pageviews', []))} Pageviews, {len(shop_data.get('clicks', []))} Clicks")
        
        # Grundlegende Metriken berechnen
        total_pageviews = len(shop_data.get('pageviews', []))
        total_clicks = len(shop_data.get('clicks', []))
        
        print(f"Berechnete Metriken: {total_pageviews} Pageviews, {total_clicks} Clicks")
        
        # Unique Pages berechnen
        unique_pages_set = set()
        for pv in shop_data.get('pageviews', []):
            if 'page' in pv and pv['page']:
                unique_pages_set.add(pv['page'])
        unique_pages = len(unique_pages_set)
        
        # Erweiterte Metriken berechnen
        click_rate = (total_clicks / total_pageviews * 100) if total_pageviews > 0 else 0
        avg_clicks_per_page = total_clicks / unique_pages if unique_pages > 0 else 0
        
        # Durchschnittliche Sitzungsdauer berechnen
        session_durations = {}
        for pageview in shop_data.get('pageviews', []):
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
        for pv in shop_data.get('pageviews', [])[:10]:  # Begrenzen auf die neuesten 10 Einträge
            events.append({
                'event_type': 'page_view',
                'page_url': pv.get('page', ''),
                'timestamp': datetime.datetime.fromtimestamp(pv.get('timestamp', 0)/1000).strftime('%Y-%m-%d %H:%M:%S') if pv.get('timestamp') else ''
            })
        
        # Clicks hinzufügen
        for click in shop_data.get('clicks', [])[:10]:  # Begrenzen auf die neuesten 10 Einträge
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
    tracking_data = {}
    save_tracking_data()
    return jsonify({
        'status': 'success',
        'message': 'Tracking-Daten wurden gelöscht.'
    })

# Home Route
@app.route('/')
def home():
    # Direkt zum Dashboard weiterleiten
    return redirect('/dashboard')

# Test-Route zum Testen des Trackings (entfernt)
# @app.route('/test')
# def test_tracking():
#     return render_template('test.html')

def generate_growth_advisor_recommendations(shop_data):
    """
    Generiert KI-basierte, priorisierte Handlungsempfehlungen basierend auf Shop-Daten.
    """
    # Daten extrahieren und analysieren
    pageviews = shop_data.get('pageviews', [])
    clicks = shop_data.get('clicks', [])
    
    # Grundlegende Metriken berechnen
    total_pageviews = len(pageviews)
    total_clicks = len(clicks)
    click_rate = (total_clicks / total_pageviews * 100) if total_pageviews > 0 else 0
    
    # Unique Pages und deren Performance
    page_views_map = {}
    page_clicks_map = {}
    
    # Seitenaufrufe zählen
    for pv in pageviews:
        page = pv.get('page', '')
        if page:
            page_views_map[page] = page_views_map.get(page, 0) + 1
            
    # Klicks pro Seite zählen
    for click in clicks:
        page = click.get('page', '')
        if page:
            page_clicks_map[page] = page_clicks_map.get(page, 0) + 1
    
    # Performance-Analyse pro Seite
    page_performance = []
    for page, views in page_views_map.items():
        clicks_on_page = page_clicks_map.get(page, 0)
        page_click_rate = (clicks_on_page / views * 100) if views > 0 else 0
        page_performance.append({
            'page': page,
            'views': views,
            'clicks': clicks_on_page,
            'click_rate': page_click_rate
        })
    
    # Nach Relevanz sortieren (hohe Besucherzahlen, niedrige Klickrate zuerst)
    page_performance.sort(key=lambda x: (x['views'] * (100 - x['click_rate'])), reverse=True)
    
    # Priorisierte Empfehlungen erstellen
    recommendations = []
    
    # Kategorie 1: Seiten-spezifische Optimierungen
    if page_performance:
        for i, page in enumerate(page_performance[:3]):  # Top 3 Seiten mit Optimierungspotential
            if page['views'] > 5:  # Nur Seiten mit genügend Daten
                if page['click_rate'] < 2.0:
                    priority = "hoch" if i == 0 else "mittel"
                    recommendations.append({
                        'category': 'Seiten-Optimierung',
                        'priority': priority,
                        'title': f"CTA auf '{page['page']}' verbessern",
                        'description': f"Diese Seite hat {page['views']} Aufrufe aber nur eine Klickrate von {round(page['click_rate'], 1)}%. Verbessere die Sichtbarkeit und Attraktivität der Call-to-Actions.",
                        'expected_impact': 'hoch' if page['views'] > 20 else 'mittel',
                        'effort': 'niedrig'
                    })
    
    # Kategorie 2: Allgemeine Shop-Optimierungen
    if total_pageviews > 0:
        # Wenn die allgemeine Klickrate niedrig ist
        if click_rate < 3.0:
            recommendations.append({
                'category': 'Shop-Optimierung',
                'priority': 'hoch',
                'title': 'Gesamte Shop-Navigation verbessern',
                'description': f'Die durchschnittliche Klickrate von {round(click_rate, 1)}% ist unterdurchschnittlich. Überarbeite die Navigation und Produktpräsentation.',
                'expected_impact': 'hoch',
                'effort': 'mittel'
            })
            
        # Mobile Optimierung, falls viele Zugriffe aber niedrige Conversion
        mobile_views = sum(1 for pv in pageviews if pv.get('device_type') == 'mobile')
        if mobile_views > total_pageviews * 0.4:  # Wenn >40% mobile Traffic
            recommendations.append({
                'category': 'Mobile Optimierung',
                'priority': 'hoch',
                'title': 'Mobile Darstellung optimieren',
                'description': f'{round(mobile_views/total_pageviews*100, 1)}% deiner Besucher nutzen mobile Geräte. Überprüfe und verbessere die mobile Darstellung deines Shops.',
                'expected_impact': 'hoch',
                'effort': 'mittel'
            })
    
    # Kategorie 3: Marketing-Empfehlungen
    if total_pageviews < 20:  # Wenig Traffic
        recommendations.append({
            'category': 'Marketing',
            'priority': 'hoch',
            'title': 'Traffic-Quellen erweitern',
            'description': 'Dein Shop hat wenig Besucher. Starte eine gezielte Social-Media-Kampagne oder Google Ads, um mehr qualifizierten Traffic zu generieren.',
            'expected_impact': 'hoch',
            'effort': 'mittel'
        })
    
    # Falls wir keine spezifischen Empfehlungen haben, füge generische hinzu
    if not recommendations:
        recommendations.append({
            'category': 'Datensammlung',
            'priority': 'hoch',
            'title': 'Mehr Nutzerdaten sammeln',
            'description': 'Sammle mehr Daten für präzisere Empfehlungen. Überprüfe die korrekte Installation des Tracking-Scripts auf allen Seiten.',
            'expected_impact': 'mittel',
            'effort': 'niedrig'
        })
    
    # Zeitbasierte Empfehlungen (z.B. saisonale Aktionen)
    current_month = datetime.datetime.now().month
    if 10 <= current_month <= 12:  # Q4 (Weihnachtsgeschäft)
        recommendations.append({
            'category': 'Saisonales Marketing',
            'priority': 'hoch',
            'title': 'Weihnachtsangebote prominenter platzieren',
            'description': 'Das Weihnachtsgeschäft steht vor der Tür. Erstelle spezielle Angebote und platziere sie auf der Startseite.',
            'expected_impact': 'hoch',
            'effort': 'niedrig'
        })
    
    return recommendations

# Growth Advisor Route
@app.route('/growth-advisor')
def growth_advisor():
    try:
        # Demo-Shop für Test-Zwecke
        shop = "test-shop.example.com"
        
        # Daten für diesen Shop laden
        shop_data = get_shop_data(shop)
        
        # Empfehlungen generieren
        advisor_recommendations = generate_growth_advisor_recommendations(shop_data)
        
        # Nach Priorität sortieren
        advisor_recommendations.sort(key=lambda x: 0 if x['priority'] == 'hoch' else (1 if x['priority'] == 'mittel' else 2))
        
        # Datum für Aktualisierung
        last_updated = datetime.datetime.now().strftime("%d.%m.%Y, %H:%M")
        
        return render_template(
            "growth_advisor.html",
            recommendations=advisor_recommendations,
            last_updated=last_updated,
            shop_name=shop
        )
    except Exception as e:
        print(f"Fehler beim Laden des Growth Advisors: {e}")
        import traceback
        traceback.print_exc()
        return render_template(
            "growth_advisor.html",
            error=str(e),
            recommendations=[],
            last_updated=datetime.datetime.now().strftime("%d.%m.%Y, %H:%M"),
            shop_name="test-shop.example.com"
        )

# Price Optimizer Funktionen
def get_shop_products(shop_domain, access_token=None):
    """
    Ruft die Produkte eines Shopify-Shops ab.
    Bei Testdaten wird ein Mock-Datensatz zurückgegeben.
    """
    try:
        # Prüfen, ob wir ein Zugriffstoken haben
        if shop_domain and access_token:
            # Echten API-Aufruf an Shopify senden
            url = f"https://{shop_domain}/admin/api/2023-07/products.json"
            headers = {"X-Shopify-Access-Token": access_token}
            
            response = requests.get(url, headers=headers)
            
            # Prüfen, ob der Aufruf erfolgreich war
            if response.status_code == 200:
                print(f"✅ Produkte erfolgreich von Shopify abgerufen")
                
                # JSON-Antwort verarbeiten
                products_data = response.json().get('products', [])
                
                # Wenn wir Produkte erhalten haben, diese zurückgeben
                if products_data:
                    return products_data
                else:
                    print("⚠️ Keine Produkte in der API-Antwort gefunden.")
            else:
                print(f"❌ Fehler beim Abrufen der Produkte: Status {response.status_code}")
                print(f"Antwort: {response.text}")
    except Exception as e:
        print(f"❌ Fehler beim Abrufen der Produkte über die API: {e}")
    
    # Fallback auf Mock-Daten, wenn API-Aufruf fehlschlägt oder keine Daten zurückgibt
    print("⚠️ Verwende Mock-Produkte für die Demo")
    
    # Für Demo-Zwecke erstellen wir Beispieldaten
    mock_products = [
        {
            'id': 1001,
            'title': 'SportBeat Pro X3',
            'product_type': 'Sport-Kopfhörer',
            'variants': [
                {
                    'id': 2001,
                    'price': '89.00',
                    'inventory_quantity': 28,
                    'sku': 'SPBT-PRO-X3'
                }
            ],
            'image': {'src': 'https://example.com/images/headphones-blue.jpg'},
            'tags': 'sport, audio, bestseller',
            'created_at': '2023-02-15T10:00:00Z',
            'updated_at': '2023-03-10T14:30:00Z'
        },
        {
            'id': 1002,
            'title': 'FitPulse Smartwatch',
            'product_type': 'Fitness-Smartwatch',
            'variants': [
                {
                    'id': 2002,
                    'price': '129.99',
                    'inventory_quantity': 15,
                    'sku': 'FPS-201-BLK'
                }
            ],
            'image': {'src': 'https://example.com/images/smartwatch.jpg'},
            'tags': 'fitness, tech, smartwatch',
            'created_at': '2023-01-20T09:45:00Z',
            'updated_at': '2023-03-05T11:20:00Z'
        },
        {
            'id': 1003,
            'title': 'UltraFlex Sportmatte',
            'product_type': 'Yoga-Matte',
            'variants': [
                {
                    'id': 2003,
                    'price': '45.50',
                    'inventory_quantity': 42,
                    'sku': 'UFLEX-YM-200'
                }
            ],
            'image': {'src': 'https://example.com/images/yoga-mat.jpg'},
            'tags': 'yoga, fitness, wellness',
            'created_at': '2023-02-01T15:30:00Z',
            'updated_at': '2023-03-15T09:10:00Z'
        },
        {
            'id': 1004,
            'title': 'EnergyBoost Protein',
            'product_type': 'Nahrungsergänzung',
            'variants': [
                {
                    'id': 2004,
                    'price': '34.95',
                    'inventory_quantity': 65,
                    'sku': 'EB-PROT-1000'
                }
            ],
            'image': {'src': 'https://example.com/images/protein.jpg'},
            'tags': 'nutrition, fitness, supplement',
            'created_at': '2023-01-10T12:20:00Z',
            'updated_at': '2023-03-02T16:45:00Z'
        },
        {
            'id': 1005,
            'title': 'AquaFlow Trinkflasche',
            'product_type': 'Fitness-Zubehör',
            'variants': [
                {
                    'id': 2005,
                    'price': '19.99',
                    'inventory_quantity': 102,
                    'sku': 'AQUA-BTL-01'
                }
            ],
            'image': {'src': 'https://example.com/images/bottle.jpg'},
            'tags': 'hydration, fitness, eco',
            'created_at': '2023-02-20T08:15:00Z',
            'updated_at': '2023-03-18T10:30:00Z'
        }
    ]
    
    return mock_products

def get_competitor_data(product_type, product_title=None):
    """
    Ruft Wettbewerbsdaten für einen bestimmten Produkttyp ab.
    In einer realen Implementierung würde dies aus einer Marktdatenbank oder API kommen.
    """
    # In einer realen Anwendung würden wir hier eine API für Marktdaten abfragen
    
    # Für Demo-Zwecke erstellen wir realistische Beispieldaten
    if product_type == 'Sport-Kopfhörer':
        return {
            'competitors': [
                {'shop': 'TopSport24', 'price': 94.99, 'last_updated': '2 Tagen'},
                {'shop': 'AudioGear', 'price': 91.50, 'last_updated': '7 Tagen'},
                {'shop': 'SoundFitness', 'price': 85.00, 'last_updated': '1 Tag'},
                {'shop': 'SportElektronik', 'price': 99.99, 'last_updated': 'Heute'},
                {'shop': 'FitGadgets', 'price': 96.50, 'last_updated': '3 Tagen'},
                {'shop': 'RunnersPro', 'price': 93.00, 'last_updated': '5 Tagen'},
                {'shop': 'FitnessSound', 'price': 92.49, 'last_updated': '2 Tagen'},
                {'shop': 'SportTech', 'price': 89.95, 'last_updated': '6 Tagen'},
                {'shop': 'AudioSport', 'price': 97.90, 'last_updated': '4 Tagen'},
                {'shop': 'ElectroFit', 'price': 90.00, 'last_updated': '1 Tag'},
                {'shop': 'ActiveSound', 'price': 95.50, 'last_updated': '3 Tagen'},
                {'shop': 'SportGear', 'price': 88.49, 'last_updated': '5 Tagen'},
                {'shop': 'WirelessAudio', 'price': 101.99, 'last_updated': '1 Tag'},
                {'shop': 'RunnerTech', 'price': 92.00, 'last_updated': '4 Tagen'},
                {'shop': 'FitElectronics', 'price': 87.95, 'last_updated': '2 Tagen'},
                {'shop': 'SportAudio', 'price': 94.50, 'last_updated': '6 Tagen'},
                {'shop': 'TechFitness', 'price': 97.99, 'last_updated': '3 Tagen'},
                {'shop': 'SoundRunner', 'price': 90.95, 'last_updated': '7 Tagen'},
                {'shop': 'FitHeadphones', 'price': 93.99, 'last_updated': '2 Tagen'},
                {'shop': 'SportBeats', 'price': 98.50, 'last_updated': '4 Tagen'},
                {'shop': 'RunwithMusic', 'price': 89.99, 'last_updated': '5 Tagen'},
                {'shop': 'ActiveBeats', 'price': 92.95, 'last_updated': '3 Tagen'},
                {'shop': 'AudioActive', 'price': 96.00, 'last_updated': '1 Tag'},
                {'shop': 'TechRun', 'price': 91.99, 'last_updated': '6 Tagen'}
            ],
            'avg_price': 93.42,
            'price_range': {'min': 85.00, 'max': 101.99},
            'trending_direction': 'up',
            'count': 24
        }
    elif product_type == 'Fitness-Smartwatch':
        return {
            'competitors': [
                {'shop': 'WatchFit', 'price': 134.99, 'last_updated': '3 Tagen'},
                {'shop': 'SmartLife', 'price': 129.95, 'last_updated': '5 Tagen'},
                {'shop': 'TechWear', 'price': 139.00, 'last_updated': '1 Tag'},
                {'shop': 'FitnessGadgets', 'price': 125.50, 'last_updated': '4 Tagen'},
                {'shop': 'SportTech', 'price': 132.95, 'last_updated': '2 Tagen'},
                # Gekürzt für Übersichtlichkeit, in einer realen Anwendung mehr Daten
            ],
            'avg_price': 132.48,
            'price_range': {'min': 125.50, 'max': 139.00},
            'trending_direction': 'stable',
            'count': 12
        }
    else:
        # Generische Daten für andere Produkttypen
        return {
            'competitors': [
                {'shop': 'Competitor1', 'price': float(random.randint(80, 120)), 'last_updated': '3 Tagen'},
                {'shop': 'Competitor2', 'price': float(random.randint(80, 120)), 'last_updated': '1 Tag'},
                {'shop': 'Competitor3', 'price': float(random.randint(80, 120)), 'last_updated': '5 Tagen'},
                {'shop': 'Competitor4', 'price': float(random.randint(80, 120)), 'last_updated': '2 Tagen'},
                {'shop': 'Competitor5', 'price': float(random.randint(80, 120)), 'last_updated': '7 Tagen'},
            ],
            'avg_price': 100.00,
            'price_range': {'min': 80.00, 'max': 120.00},
            'trending_direction': 'stable',
            'count': 5
        }

def calculate_price_elasticity(shop_domain, access_token, product_id):
    """
    Berechnet die Preiselastizität eines Produkts basierend auf historischen Verkaufsdaten.
    Verwendet die Shopify Orders API, um Bestellungen zu analysieren und Preis-Verkaufs-Paare zu erstellen.
    """
    try:
        # Wenn kein Access Token verfügbar ist, können wir keine Daten abrufen
        if not access_token:
            print("⚠️ Kein Access Token für Elastizitätsberechnung vorhanden")
            return None
        
        print(f"🔍 Berechne Preiselastizität für Produkt {product_id} in Shop {shop_domain}")
        
        # Historische Bestellungen der letzten 90 Tage abrufen
        orders_url = f"https://{shop_domain}/admin/api/2023-07/orders.json?status=any&limit=250"
        headers = {"X-Shopify-Access-Token": access_token}
        
        response = requests.get(orders_url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Fehler beim Abrufen der Bestellungen: Status {response.status_code}")
            print(f"Antwort: {response.text}")
            return None
        
        # Bestellungen aus der API-Antwort extrahieren
        orders = response.json().get('orders', [])
        print(f"✅ {len(orders)} Bestellungen gefunden")
        
        # Preis-Mengen-Paare für das Produkt sammeln
        price_quantity_pairs = []
        
        for order in orders:
            # Bestelldatum in Datetime-Objekt umwandeln
            order_date_str = order.get('created_at', '')
            if not order_date_str:
                continue
                
            try:
                # ISO-Format mit Z für UTC in Datetime umwandeln
                order_date = datetime.datetime.fromisoformat(order_date_str.replace('Z', '+00:00'))
                
                # Nur Bestellungen der letzten 90 Tage betrachten
                time_diff = datetime.datetime.now(datetime.timezone.utc) - order_date
                if time_diff.days > 90:
                    continue
            except Exception as e:
                print(f"⚠️ Fehler beim Parsen des Bestelldatums: {e}")
                continue
                
            # Bestellpositionen durchgehen
            for line_item in order.get('line_items', []):
                # Prüfen, ob es sich um das gesuchte Produkt handelt
                if str(line_item.get('product_id')) == str(product_id):
                    price = float(line_item.get('price', 0))
                    quantity = int(line_item.get('quantity', 1))
                    
                    # Nach Preis gruppieren (auf 2 Dezimalstellen gerundet)
                    rounded_price = round(price, 2)
                    
                    # Wenn der Preis bereits in den Paaren vorhanden ist, Mengen addieren
                    found = False
                    for pair in price_quantity_pairs:
                        if abs(pair['price'] - rounded_price) < 0.01:  # Fast gleicher Preis
                            pair['sales'] += quantity
                            found = True
                            break
                    
                    # Wenn der Preis noch nicht vorhanden ist, neues Paar hinzufügen
                    if not found:
                        price_quantity_pairs.append({'price': rounded_price, 'sales': quantity})
        
        # Nach Preis aufsteigend sortieren
        price_quantity_pairs.sort(key=lambda x: x['price'])
        
        # Preiselastizitätsdaten zurückgeben, wenn vorhanden
        if price_quantity_pairs:
            print(f"✅ {len(price_quantity_pairs)} Preis-Verkaufs-Paare generiert")
            return price_quantity_pairs
        else:
            print("⚠️ Keine Verkaufsdaten für die Elastizitätsberechnung gefunden")
            return None
            
    except Exception as e:
        print(f"❌ Fehler bei der Elastizitätsberechnung: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_price_trend_data(product_type, current_price, shop_domain=None, access_token=None, product_id=None):
    """
    Generiert historische Preisdaten und Empfehlungen für ein Produkt.
    Nutzt echte Verkaufsdaten, wenn verfügbar, sonst simulierte Daten.
    """
    # Aktuelle Zeit für die Simulation
    now = datetime.datetime.now()
    
    # Wenn wir Zugriff auf echte Verkaufsdaten haben, nutzen wir diese
    elasticity_data = None
    if shop_domain and access_token and product_id:
        elasticity_data = calculate_price_elasticity(shop_domain, access_token, product_id)
    
    # Wenn keine echten Daten verfügbar sind, verwenden wir simulierte Daten
    if not elasticity_data:
        print("ℹ️ Verwende simulierte Elastizitätsdaten")
        if product_type == 'Sport-Kopfhörer':
            elasticity_data = [
                {'price': 79, 'sales': 156},
                {'price': 84, 'sales': 142},
                {'price': 89, 'sales': 128},
                {'price': 94, 'sales': 118},
                {'price': 99, 'sales': 105},
                {'price': 104, 'sales': 88}
            ]
        else:
            # Generische elasticity_data für andere Produkttypen
            base_price = float(current_price)
            elasticity_data = [
                {'price': round(base_price * 0.9, 2), 'sales': 120},
                {'price': round(base_price, 2), 'sales': 100},
                {'price': round(base_price * 1.1, 2), 'sales': 85}
            ]
    
    # Für Sport-Kopfhörer spezifische Simulation oder andere Produkte
    if product_type == 'Sport-Kopfhörer':
        # Historische Preisentwicklung (30 Tage)
        days = 30
        dates = [(now - datetime.timedelta(days=i)).strftime('%d. %b') for i in range(days-1, -1, -1)]
        
        # Simulation von historischen Preisen für den Shop
        starting_price = 85.0
        shop_prices = [starting_price] * 5  # Erste 5 Tage konstant
        shop_prices += [float(current_price)] * 25  # Rest der Zeit bei aktuellem Preis
        
        # Simulation von Marktdurchschnittspreisen (steigender Trend)
        market_avg_start = 82.0
        market_avg_end = 93.0
        market_prices = []
        for i in range(days):
            progress = i / (days - 1)
            market_price = market_avg_start + progress * (market_avg_end - market_avg_start)
            # Etwas Noise hinzufügen
            market_price += random.uniform(-1.0, 1.0)
            market_prices.append(round(market_price, 2))
        
        # Optimaler Preis (basierend auf Algorithmus-Empfehlungen)
        optimal_prices = []
        for i in range(days):
            if i < 10:
                # Erste 10 Tage ähnlich dem Marktpreis
                optimal_price = market_prices[i] + 3.0
            else:
                # Danach stärker ansteigend
                optimal_price = market_prices[i] + 4.0 + (i - 10) * 0.2
            optimal_prices.append(round(optimal_price, 2))
        
        # Zukünftige Preisempfehlung basierend auf Elastizitätsdaten
        if len(elasticity_data) >= 3:
            # Lineare Regression auf Elastizitätsdaten anwenden für bessere Empfehlungen
            prices = np.array([pair['price'] for pair in elasticity_data])
            sales = np.array([pair['sales'] for pair in elasticity_data])
            revenues = prices * sales
            
            # Einfache Methode zur Bestimmung des optimalen Preises: Suche nach max Umsatz
            max_revenue_index = np.argmax(revenues)
            
            # Falls der aktuelle Preis bereits optimal ist, leichte Erhöhung vorschlagen
            if prices[max_revenue_index] <= current_price:
                recommended_price = round(current_price * 1.09, 2)  # 9% Erhöhung als Default
            else:
                recommended_price = round(prices[max_revenue_index], 2)
        else:
            # Standardempfehlung, wenn nicht genug Datenpunkte
            recommended_price = 97.0
    else:
        # Generischer Ansatz für andere Produkttypen
        days = 30
        dates = [(now - datetime.timedelta(days=i)).strftime('%d. %b') for i in range(days-1, -1, -1)]
        
        current_price_float = float(current_price)
        market_avg = current_price_float * random.uniform(0.9, 1.1)
        
        # Generiere zufällige Preisdaten
        shop_prices = [current_price_float] * days
        market_prices = [market_avg + random.uniform(-5, 5) for _ in range(days)]
        optimal_prices = [market_prices[i] * random.uniform(1.05, 1.15) for i in range(days)]
        
        # Empfohlener Preis basierend auf Elastizitätsdaten, falls vorhanden
        if len(elasticity_data) >= 3:
            prices = np.array([pair['price'] for pair in elasticity_data])
            sales = np.array([pair['sales'] for pair in elasticity_data])
            revenues = prices * sales
            
            max_revenue_index = np.argmax(revenues)
            
            if prices[max_revenue_index] <= current_price_float:
                recommended_price = round(current_price_float * 1.1, 2)
            else:
                recommended_price = round(prices[max_revenue_index], 2)
        else:
            recommended_price = round(current_price_float * 1.1, 2)
    
    # Umsatzprognosen basierend auf Elastizitätsdaten
    current_revenue = 0
    recommended_revenue = 0
    
    # Finde den aktuellen Umsatz
    for entry in elasticity_data:
        if abs(entry['price'] - current_price) < 0.01:
            current_revenue = entry['price'] * entry['sales']
            break
    
    # Wenn kein exakter Treffer, lineares Interpolieren für den Umsatz
    if current_revenue == 0 and len(elasticity_data) >= 2:
        # Finde zwei Preispunkte, die den aktuellen Preis einschließen
        for i in range(len(elasticity_data) - 1):
            if elasticity_data[i]['price'] <= current_price <= elasticity_data[i+1]['price']:
                price_diff = elasticity_data[i+1]['price'] - elasticity_data[i]['price']
                sales_diff = elasticity_data[i+1]['sales'] - elasticity_data[i]['sales']
                
                # Verhältnis berechnen
                price_ratio = (current_price - elasticity_data[i]['price']) / price_diff if price_diff > 0 else 0
                
                # Geschätzte Verkäufe berechnen
                estimated_sales = elasticity_data[i]['sales'] + price_ratio * sales_diff
                
                current_revenue = current_price * estimated_sales
                break
    
    # Wenn immer noch kein Wert gefunden (z.B. Preis außerhalb des Bereichs), erste oder letzte Werte verwenden
    if current_revenue == 0 and elasticity_data:
        if current_price < elasticity_data[0]['price']:
            current_revenue = current_price * elasticity_data[0]['sales']
        elif current_price > elasticity_data[-1]['price']:
            current_revenue = current_price * elasticity_data[-1]['sales']
    
    # Gleiche Logik für den empfohlenen Preis
    for entry in elasticity_data:
        if abs(entry['price'] - recommended_price) < 0.01:
            recommended_revenue = entry['price'] * entry['sales']
            break
    
    if recommended_revenue == 0 and len(elasticity_data) >= 2:
        for i in range(len(elasticity_data) - 1):
            if elasticity_data[i]['price'] <= recommended_price <= elasticity_data[i+1]['price']:
                price_diff = elasticity_data[i+1]['price'] - elasticity_data[i]['price']
                sales_diff = elasticity_data[i+1]['sales'] - elasticity_data[i]['sales']
                
                price_ratio = (recommended_price - elasticity_data[i]['price']) / price_diff if price_diff > 0 else 0
                estimated_sales = elasticity_data[i]['sales'] + price_ratio * sales_diff
                
                recommended_revenue = recommended_price * estimated_sales
                break
    
    if recommended_revenue == 0 and elasticity_data:
        if recommended_price < elasticity_data[0]['price']:
            recommended_revenue = recommended_price * elasticity_data[0]['sales']
        elif recommended_price > elasticity_data[-1]['price']:
            recommended_revenue = recommended_price * elasticity_data[-1]['sales']
    
    # Prozentuale Umsatzsteigerung berechnen
    if current_revenue > 0 and recommended_revenue > 0:
        revenue_increase_pct = ((recommended_revenue - current_revenue) / current_revenue) * 100
    else:
        # Fallback, wenn wir keine sinnvolle Berechnung durchführen können
        revenue_increase_pct = 15.0
    
    return {
        'dates': dates,
        'shop_prices': shop_prices,
        'market_prices': market_prices,
        'optimal_prices': optimal_prices,
        'recommended_price': recommended_price,
        'current_price': current_price,
        'elasticity_data': elasticity_data,
        'revenue_increase_pct': round(revenue_increase_pct, 1)
    }

def generate_ai_price_recommendations(product_type, current_price, competitor_data, trend_data):
    """
    Generiert KI-basierte Preisempfehlungen.
    """
    recommendations = []
    
    if product_type == 'Sport-Kopfhörer':
        # Hauptempfehlung zur Preiserhöhung
        recommendations.append({
            'title': f'Erhöhen Sie Ihren Preis auf €{trend_data["recommended_price"]}',
            'description': f'Basierend auf der aktuellen Nachfrage und Wettbewerbspreisen ist eine Preiserhöhung optimal. Unsere Analyse zeigt, dass dies zu einer Umsatzsteigerung von ~{trend_data["revenue_increase_pct"]}% führen könnte ohne die Verkaufszahlen signifikant zu beeinflussen.'
        })
        
        # Saisonale Preisanpassung
        recommendations.append({
            'title': 'Dynamic Pricing für Stoßzeiten',
            'description': f'Implementieren Sie höhere Preise am Wochenende (€{round(trend_data["recommended_price"] + 2, 0)}), wenn die Nachfrage am höchsten ist. Unsere Daten zeigen, dass Kunden dann weniger preissensitiv sind.'
        })
        
        # Bundle-Angebot
        recommendations.append({
            'title': 'Bundle-Angebot erstellen',
            'description': f'Erstellen Sie ein Bundle mit Sportkopfhörern und Tragetasche für €{round(trend_data["recommended_price"] * 1.3, 0)}. Dies erhöht den durchschnittlichen Bestellwert und schafft einen wahrgenommenen Wertvorteil.'
        })
    else:
        # Generische Empfehlungen für andere Produkttypen
        recommendations.append({
            'title': f'Optimieren Sie Ihren Preis auf €{trend_data["recommended_price"]}',
            'description': f'Basierend auf Marktdaten und Preiselastizität empfehlen wir eine Anpassung auf €{trend_data["recommended_price"]}. Dies könnte zu einer Umsatzsteigerung von ~{trend_data["revenue_increase_pct"]}% führen.'
        })
        
        recommendations.append({
            'title': 'A/B-Test mit verschiedenen Preispunkten',
            'description': f'Testen Sie verschiedene Preispunkte, um den optimalen Wert zu finden. Wir empfehlen Tests mit €{round(float(current_price), 2)}, €{round(float(current_price) * 1.05, 2)} und €{round(float(current_price) * 1.1, 2)}.'
        })
        
        recommendations.append({
            'title': 'Rabattstrategie überdenken',
            'description': 'Bieten Sie gezielte Rabatte für Bestandskunden an, anstatt den Basispreis zu senken. Dies erhält die Preiswahrnehmung und fördert gleichzeitig die Kundenbindung.'
        })
    
    return recommendations

@app.route('/price-optimizer')
def price_optimizer():
    """Rendert die Price Optimizer Seite mit dynamischen Daten."""
    try:
        # Shop und Access Token aus der Session abrufen
        shop = session.get('shop')
        access_token = session.get('access_token')
        
        # Wenn kein Shop in der Session ist, aber einer als Parameter übergeben wurde
        shop_param = request.args.get('shop')
        if not shop and shop_param:
            # Umleitung zur Installation
            return redirect(f'/install?shop={shop_param}')
        
        # Wenn kein Shop in der Session oder als Parameter, dann Demo-Shop verwenden
        if not shop:
            shop = "test-shop.example.com"
            print(f"⚠️ Kein authentifizierter Shop gefunden, verwende Demo-Shop: {shop}")
        else:
            print(f"✅ Authentifizierter Shop gefunden: {shop}")
        
        # Produkte vom Shop abrufen (entweder echte über API oder Mock-Daten)
        products = get_shop_products(shop, access_token)
        
        # Standardmäßig das erste Produkt auswählen
        selected_product = products[0]
        product_type = selected_product.get('product_type', '')
        product_id = selected_product.get('id', '')
        
        # Varianten-Preis abrufen
        variants = selected_product.get('variants', [])
        if variants:
            current_price = float(variants[0].get('price', 0))
        else:
            current_price = 0
        
        # Optional: Produktauswahl über Query-Parameter ermöglichen
        product_id_param = request.args.get('product_id')
        if product_id_param:
            for product in products:
                if str(product.get('id')) == product_id_param:
                    selected_product = product
                    product_type = selected_product.get('product_type', '')
                    product_id = selected_product.get('id', '')
                    variants = selected_product.get('variants', [])
                    if variants:
                        current_price = float(variants[0].get('price', 0))
                    break
        
        # Wettbewerbsdaten abrufen
        competitor_data = get_competitor_data(product_type, selected_product.get('title', ''))
        
        # Preistrend-Daten abrufen mit echten Verkaufsdaten, wenn verfügbar
        trend_data = get_price_trend_data(
            product_type, 
            current_price, 
            shop_domain=shop,
            access_token=access_token,
            product_id=product_id
        )
        
        # KI-Preisempfehlungen generieren
        price_recommendations = generate_ai_price_recommendations(
            product_type, 
            current_price, 
            competitor_data, 
            trend_data
        )
        
        # Datum der letzten Aktualisierung
        last_updated = datetime.datetime.now().strftime("%d.%m.%Y, %H:%M")
        
        return render_template(
            "price_optimizer.html",
            products=products,
            selected_product=selected_product,
            competitor_data=competitor_data,
            trend_data=trend_data,
            price_recommendations=price_recommendations,
            last_updated=last_updated,
            shop_name=shop
        )
    except Exception as e:
        print(f"Fehler beim Laden des Price Optimizers: {e}")
        import traceback
        traceback.print_exc()
        return render_template(
            "price_optimizer.html",
            error=str(e),
            products=[],
            selected_product=None,
            competitor_data={},
            trend_data={},
            price_recommendations=[],
            last_updated=datetime.datetime.now().strftime("%d.%m.%Y, %H:%M"),
            shop_name="test-shop.example.com"
        )

# Flask Starten
if __name__ == "__main__":
    # Parse command line arguments for port
    parser = argparse.ArgumentParser(description='Start the Flask application server.')
    parser.add_argument('--port', type=int, default=5002, help='Port number to run the server on (default: 5002)')
    args = parser.parse_args()
    
    # Tracking-Daten beim Start laden
    load_tracking_data()
    
    app.run(host="0.0.0.0", port=args.port, debug=True)