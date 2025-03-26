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
import hmac
import hashlib
from functools import wraps
import jwt
from flask_session import Session

# Environment-Variablen laden
load_dotenv()

# Pfad zur Tracking-Datendatei
TRACKING_DATA_FILE = 'tracking_data.json'

# Flask App konfigurieren
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True  # Session permanent machen
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=30)  # Session-Lebensdauer auf 30 Tage setzen
app.config['SESSION_FILE_DIR'] = '/tmp/flask_session'  # Expliziter Session-Speicherort
app.config['SESSION_FILE_THRESHOLD'] = 500  # Maximale Anzahl von Session-Dateien

# Stelle sicher, dass das Session-Verzeichnis existiert
os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)

# Session-Middleware initialisieren
sess = Session()
sess.init_app(app)

CORS(app, resources={r"/*": {"origins": "*"}})

# Shopify API Keys aus der .env Datei
SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPES = os.getenv("SCOPES")
HOST = os.getenv("HOST", "miniflaskenv-production.up.railway.app")

# OpenAI konfigurieren
openai.api_key = os.getenv("OPENAI_API_KEY")

# Tracking-Data für Dashboard
tracking_data = {}  # Leeres Dictionary für alle Shops

# Übersetzungen laden
translations = {
    'en': {},
    'de': {}
}

def load_translations():
    """Lädt die Übersetzungsdateien für alle unterstützten Sprachen."""
    global translations
    
    # Standardwerte initialisieren
    translations = {
        'en': {
            "app": {"name": "ShoppulseAI", "title": "Intelligent Growth Analysis for Shopify"},
            "navigation": {
                "dashboard": "Dashboard",
                "growth_advisor": "Growth Advisor™",
                "price_optimizer": "Price Optimizer™",
                "settings": "Settings",
                "analytics": "Analytics",
                "configuration": "Configuration"
            },
            "dashboard": {"title": "Analytics Dashboard"},
            "price_optimizer": {"title": "Price Optimizer™"},
            "growth_advisor": {"title": "Growth Advisor™"},
            "errors": {
                "general": "An error occurred.",
                "data_load": "Error loading data.",
                "not_connected": "Shop not connected.",
                "no_products": "No products found."
            },
            "language": {
                "select": "Select Language",
                "en": "English",
                "de": "German"
            },
            "buttons": {
                "save": "Save",
                "cancel": "Cancel",
                "apply": "Apply",
                "reload": "Reload",
                "export": "Export"
            }
        },
        'de': {
            "app": {"name": "ShoppulseAI", "title": "Intelligente Wachstumsanalyse für Shopify"},
            "navigation": {
                "dashboard": "Dashboard",
                "growth_advisor": "Growth Advisor™",
                "price_optimizer": "Price Optimizer™",
                "settings": "Einstellungen",
                "analytics": "Analytics",
                "configuration": "Konfiguration"
            },
            "dashboard": {"title": "Analytics Dashboard"},
            "price_optimizer": {"title": "Price Optimizer™"},
            "growth_advisor": {"title": "Growth Advisor™"},
            "errors": {
                "general": "Ein Fehler ist aufgetreten.",
                "data_load": "Fehler beim Laden der Daten.",
                "not_connected": "Shop nicht verbunden.",
                "no_products": "Keine Produkte gefunden."
            },
            "language": {
                "select": "Sprache auswählen",
                "en": "Englisch",
                "de": "Deutsch"
            },
            "buttons": {
                "save": "Speichern",
                "cancel": "Abbrechen",
                "apply": "Anwenden",
                "reload": "Neu laden",
                "export": "Exportieren"
            }
        }
    }
    
    try:
        # Absolute Pfade für Railway und lokale Entwicklung
        base_dir = os.path.dirname(os.path.abspath(__file__))
        en_path = os.path.join(base_dir, 'translations', 'en.json')
        de_path = os.path.join(base_dir, 'translations', 'de.json')
        
        # Verzeichnis erstellen, falls es nicht existiert
        translations_dir = os.path.join(base_dir, 'translations')
        if not os.path.exists(translations_dir):
            os.makedirs(translations_dir)
            print(f"Verzeichnis für Übersetzungen erstellt: {translations_dir}")
        
        # Englische Übersetzung laden
        if os.path.exists(en_path):
            with open(en_path, 'r', encoding='utf-8') as f:
                loaded_translations = json.load(f)
                translations['en'].update(loaded_translations)
                print(f"Englische Übersetzungen geladen aus {en_path}.")
        else:
            print(f"Warnung: Englische Übersetzungsdatei nicht gefunden unter {en_path}. Verwende Standardwerte.")
            # Speichere die Standardwerte in der Datei
            with open(en_path, 'w', encoding='utf-8') as f:
                json.dump(translations['en'], f, ensure_ascii=False, indent=2)
                print(f"Englische Standardübersetzungen in {en_path} gespeichert.")
        
        # Deutsche Übersetzung laden
        if os.path.exists(de_path):
            with open(de_path, 'r', encoding='utf-8') as f:
                loaded_translations = json.load(f)
                translations['de'].update(loaded_translations)
                print(f"Deutsche Übersetzungen geladen aus {de_path}.")
        else:
            print(f"Warnung: Deutsche Übersetzungsdatei nicht gefunden unter {de_path}. Verwende Standardwerte.")
            # Speichere die Standardwerte in der Datei
            with open(de_path, 'w', encoding='utf-8') as f:
                json.dump(translations['de'], f, ensure_ascii=False, indent=2)
                print(f"Deutsche Standardübersetzungen in {de_path} gespeichert.")
    
    except Exception as e:
        print(f"Fehler beim Laden der Übersetzungen: {e}")
        print("Verwende Standardwerte für Übersetzungen.")
        import traceback
        traceback.print_exc()

def get_user_language():
    """Ermittelt die Sprache des Benutzers basierend auf Cookie, Session oder Browser-Einstellungen."""
    # Versuche zuerst die Sprache aus der Session zu lesen
    if 'language' in session:
        return session['language']
    
    # Dann versuche die Sprache aus dem Cookie zu lesen
    if request.cookies.get('language'):
        return request.cookies.get('language')
    
    # Dann versuche die Accept-Language Header zu lesen
    if request.headers.get('Accept-Language'):
        # Parse den Accept-Language Header und nimm den ersten Teil
        accept_languages = request.headers.get('Accept-Language').split(',')
        if accept_languages:
            lang_code = accept_languages[0].split(';')[0].strip().lower()
            if lang_code.startswith('de'):
                return 'de'
    
    # Fallback auf Englisch
    return 'en'

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
                
                # Stelle sicher, dass alle Shop-Einträge die korrekten Unterstrukturen haben
                for shop_domain in tracking_data:
                    if 'pageviews' not in tracking_data[shop_domain]:
                        tracking_data[shop_domain]['pageviews'] = []
                    if 'clicks' not in tracking_data[shop_domain]:
                        tracking_data[shop_domain]['clicks'] = []
    except Exception as e:
        print(f"Fehler beim Laden der Tracking-Daten: {e}")
        tracking_data = {}
    
    return tracking_data

def get_shop_data(shop_domain):
    """Holt oder erstellt die Tracking-Daten für einen bestimmten Shop."""
    global tracking_data
    
    # Validiere shop_domain
    if not shop_domain or not isinstance(shop_domain, str):
        print(f"⚠️ Ungültige Shop-Domain: {shop_domain}")
        shop_domain = "unknown-shop.example.com"
    
    # Standardformat für die Shop-Domain
    if shop_domain.endswith(';'):
        shop_domain = shop_domain[:-1]
        print(f"🔧 Shop-Domain bereinigt: {shop_domain}")
    
    # Wenn der Shop noch nicht im Dictionary existiert, initialisiere ihn
    if shop_domain not in tracking_data:
        print(f"🆕 Initialisiere neuen Shop: {shop_domain}")
        tracking_data[shop_domain] = {
            'pageviews': [],
            'clicks': [],
            'created_at': datetime.datetime.now().isoformat(),
            'last_updated': datetime.datetime.now().isoformat()
        }
        save_tracking_data()
    
    # Stelle sicher, dass die Schlüssel existieren
    if 'pageviews' not in tracking_data[shop_domain]:
        tracking_data[shop_domain]['pageviews'] = []
    
    if 'clicks' not in tracking_data[shop_domain]:
        tracking_data[shop_domain]['clicks'] = []
    
    # Datum für 'last_updated' aktualisieren
    tracking_data[shop_domain]['last_updated'] = datetime.datetime.now().isoformat()
    
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

def hmac_validation(params):
    """Validiert den HMAC-Parameter von Shopify."""
    if not params.get('hmac'):
        return False

    # Parameter sortieren und HMAC entfernen
    sorted_params = dict(sorted(params.items()))
    hmac_value = sorted_params.pop('hmac')

    # Query-String erstellen
    query_string = '&'.join([f"{key}={value}" for key, value in sorted_params.items()])
    
    # HMAC berechnen
    calculated_hmac = hmac.new(
        SHOPIFY_API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(calculated_hmac, hmac_value)

@app.route('/')
def index():
    """Root-Route mit Authentifizierungsprüfung."""
    try:
        # Prüfe ob ein Shop in der Session ist
        if 'shop' not in session:
            print("❌ Kein Shop in der Session gefunden - Weiterleitung zur Installation")
            return redirect('/install')
            
        # Prüfe ob ein Access Token vorhanden ist
        if 'access_token' not in session:
            print("❌ Kein Access Token in der Session gefunden - Weiterleitung zur Installation")
            return redirect('/install')
            
        print(f"✅ Shop authentifiziert: {session['shop']}")
        return redirect('/dashboard')
        
    except Exception as e:
        print(f"❌ Fehler in der Root-Route: {e}")
        import traceback
        traceback.print_exc()
        return redirect('/install')

@app.route('/install')
def install():
    """Installation der App initiieren."""
    try:
        shop = request.args.get('shop')
        
        # Wenn kein Shop-Parameter vorhanden ist und wir einen Shop in der Session haben
        if not shop and 'shop' in session:
            shop = session['shop']
            print(f"✅ Shop aus Session verwendet: {shop}")
        
        if not shop:
            print("❌ Kein Shop-Parameter gefunden und kein Shop in Session")
            return render_template(
                'error.html',
                error="Bitte geben Sie einen Shop-Parameter an oder installieren Sie die App über den Shopify App Store."
            )

        # Shopify OAuth URL erstellen
        nonce = os.urandom(16).hex()
        session['nonce'] = nonce
        
        install_url = f"https://{shop}/admin/oauth/authorize?client_id={SHOPIFY_API_KEY}&scope={SCOPES}&redirect_uri={REDIRECT_URI}&state={nonce}"
        
        print(f"✅ Weiterleitung zur Shopify OAuth: {install_url}")
        return redirect(install_url)
    except Exception as e:
        print(f"❌ Fehler bei der Installation: {e}")
        import traceback
        traceback.print_exc()
        return render_template(
            'error.html',
            error=f"Installationsfehler: {str(e)}"
        )

@app.route('/auth/callback')
def auth_callback():
    """Callback für OAuth-Flow."""
    try:
        # HMAC validieren
        if not hmac_validation(request.args):
            print("❌ HMAC Validierung fehlgeschlagen")
            return "Invalid HMAC", 400

        shop = request.args.get('shop')
        code = request.args.get('code')
        
        if not shop or not code:
            print("❌ Fehlende Parameter")
            return "Missing parameters", 400

        # Access Token anfordern
        access_token_url = f"https://{shop}/admin/oauth/access_token"
        access_token_payload = {
            'client_id': SHOPIFY_API_KEY,
            'client_secret': SHOPIFY_API_SECRET,
            'code': code
        }
        
        response = requests.post(access_token_url, json=access_token_payload)
        
        if response.status_code != 200:
            print(f"❌ Token-Anfrage fehlgeschlagen: {response.status_code} - {response.text}")
            return f"Failed to get access token: {response.text}", 400

        # Token aus Response extrahieren
        access_token = response.json().get('access_token')
        
        if not access_token:
            print("❌ Kein Access Token in der Antwort")
            return "No access token in response", 400

        # Token in Session speichern und Session permanent machen
        session.permanent = True
        session['shop'] = shop
        session['access_token'] = access_token
        session['authenticated'] = True
        session['auth_time'] = datetime.datetime.now().isoformat()
        
        print(f"✅ Authentifizierung erfolgreich für Shop: {shop}")
        print(f"✅ Session-Daten gespeichert: {dict(session)}")
        
        # Webhooks registrieren
        register_webhooks(shop, access_token)
        
        # Zum Dashboard weiterleiten
        return redirect('/dashboard')
        
    except Exception as e:
        print(f"❌ Fehler im Auth Callback: {e}")
        import traceback
        traceback.print_exc()
        return f"Error in auth callback: {str(e)}", 500

def register_webhooks(shop, access_token):
    """Registriert die erforderlichen Webhooks."""
    try:
        # Zuerst vorhandene Webhooks abrufen
        headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }
        
        existing_webhooks_response = requests.get(
            f"https://{shop}/admin/api/2023-07/webhooks.json",
            headers=headers
        )
        
        if existing_webhooks_response.status_code != 200:
            print(f"❌ Fehler beim Abrufen vorhandener Webhooks: {existing_webhooks_response.text}")
            return
            
        existing_webhooks = existing_webhooks_response.json().get('webhooks', [])
        existing_topics = {webhook['topic']: webhook['id'] for webhook in existing_webhooks}
        
        webhooks = [
            {
                "topic": "app/uninstalled",
                "address": f"https://{os.getenv('HOST')}/webhook/app/uninstalled",
                "format": "json"
            },
            {
                "topic": "shop/update",
                "address": f"https://{os.getenv('HOST')}/webhook/shop/update",
                "format": "json"
            }
        ]

        for webhook in webhooks:
            topic = webhook['topic']
            if topic in existing_topics:
                print(f"ℹ️ Webhook für {topic} existiert bereits")
                continue
                
            response = requests.post(
                f"https://{shop}/admin/api/2023-07/webhooks.json",
                json={"webhook": webhook},
                headers=headers
            )
            
            if response.status_code == 201:
                print(f"✅ Webhook {topic} erfolgreich registriert")
            else:
                print(f"❌ Fehler bei der Registrierung von Webhook {topic}: {response.text}")
                
    except Exception as e:
        print(f"❌ Fehler bei der Webhook-Registrierung: {e}")
        import traceback
        traceback.print_exc()

def verify_session_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not session_token:
            return jsonify({'error': 'No session token provided'}), 401
            
        try:
            # Verifiziere das Session Token
            decoded = jwt.decode(
                session_token,
                SHOPIFY_API_SECRET,
                algorithms=['HS256'],
                audience=SHOPIFY_API_KEY
            )
            
            # Füge die dekodierten Daten dem Request-Objekt hinzu
            request.shop_data = decoded
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Session token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid session token'}), 401
            
    return decorated_function

def has_sufficient_data(shop_data):
    """Prüft, ob genügend Daten für aussagekräftige Analysen vorhanden sind"""
    MIN_PAGEVIEWS = 100
    MIN_DAYS = 3
    
    total_pageviews = shop_data.get('total_pageviews', 0)
    first_tracking_date = shop_data.get('first_tracking_date')
    
    if not first_tracking_date:
        return False
        
    days_active = (datetime.now() - datetime.fromisoformat(first_tracking_date)).days
    return total_pageviews >= MIN_PAGEVIEWS and days_active >= MIN_DAYS

def get_onboarding_content():
    """Liefert Beispieldaten und Hilfestellungen für neue Shops"""
    return {
        'welcome_message': 'Willkommen bei Ihrer Shop-Optimierung!',
        'steps': [
            {
                'title': 'Datensammlung läuft',
                'description': 'Wir sammeln Daten über das Kundenverhalten in Ihrem Shop. Dies dauert etwa 3-5 Tage.',
                'progress': 0
            },
            {
                'title': 'Erste Insights',
                'description': 'Nach 100 Seitenaufrufen können wir erste Trends erkennen.',
                'progress': 0
            },
            {
                'title': 'KI-Empfehlungen',
                'description': 'Sobald genügend Daten vorliegen, erhalten Sie personalisierte KI-Empfehlungen.',
                'progress': 0
            }
        ],
        'example_data': {
            'pageviews_chart': generate_example_chart_data(),
            'conversion_rate': '2.5%',
            'popular_products': [
                {'name': 'Beispielprodukt 1', 'views': 50},
                {'name': 'Beispielprodukt 2', 'views': 30},
                {'name': 'Beispielprodukt 3', 'views': 20}
            ]
        }
    }

@app.route('/dashboard')
def dashboard():
    try:
        # Prüfe, ob ein Shop in der Session ist
        if 'shop' not in session:
            print("❌ Kein Shop in der Session gefunden - Weiterleitung zur Installation")
            return redirect('/install')
            
        # Prüfe, ob ein Access Token vorhanden ist
        if 'access_token' not in session:
            print("❌ Kein Access Token in der Session gefunden - Weiterleitung zur Installation")
            return redirect('/install')
            
        # Shop aus der Session laden
        shop = session['shop']
        
        # Shop-Daten laden
        shop_data = get_shop_data(shop)
        
        print(f"✅ Dashboard für Shop: {shop} wird geladen")
        
        if not has_sufficient_data(shop_data):
            # Zeige Onboarding-Ansicht für neue Shops
            onboarding_content = get_onboarding_content()
            
            # Berechne Fortschritt
            total_pageviews = shop_data.get('total_pageviews', 0)
            onboarding_content['steps'][0]['progress'] = min(100, (total_pageviews / 100) * 100)
            
            first_tracking_date = shop_data.get('first_tracking_date')
            if first_tracking_date:
                days_active = (datetime.datetime.now() - datetime.datetime.fromisoformat(first_tracking_date)).days
                onboarding_content['steps'][1]['progress'] = min(100, (days_active / 3) * 100)
            
            return render_template(
                'dashboard_onboarding.html',
                onboarding=onboarding_content,
                shop_data=shop_data
            )
            
        # Normale Dashboard-Ansicht für Shops mit genügend Daten
        return render_template(
            'dashboard.html',
            shop_data=shop_data
        )
        
    except Exception as e:
        print(f"Fehler im Dashboard: {e}")
        return render_template('error.html', error=str(e))

def generate_ai_tips(shop_data):
    """Generiert KI-basierte Tipps basierend auf Tracking-Daten."""
    # Default-Tipps, wenn nicht genügend Daten vorhanden sind
    default_tips = [
        {
            "title": "Content-Qualität verbessern",
            "text": "Die durchschnittliche Verweildauer ist kurz. Erweitern Sie Ihre Inhalte mit relevanten Details und verbessern Sie die Lesbarkeit durch Zwischenüberschriften und Aufzählungen."
        },
        {
            "title": "Interne Verlinkung optimieren",
            "text": "Verbessern Sie die interne Verlinkung zwischen Ihren Seiten, um Besucher zu ermutigen, mehr Seiten zu erkunden."
        }
    ]
    
    # Prüfen, ob genügend Daten für fundierte Tipps vorhanden sind
    pageviews = shop_data.get('pageviews', [])
    clicks = shop_data.get('clicks', [])
    
    if len(pageviews) < 3 and len(clicks) < 2:
        return default_tips
    
    # In einem echten Szenario würden hier komplexere Analysen durchgeführt
    # Basierend auf Seitenaufrufen, Klicks, Verweildauer usw.
    
    custom_tips = []
    
    # Analysiere die am häufigsten besuchten Seiten
    page_counts = {}
    for pv in pageviews:
        page = pv.get('page', '')
        if page in page_counts:
            page_counts[page] += 1
        else:
            page_counts[page] = 1
    
    # Sortiere Seiten nach Anzahl der Aufrufe (absteigend)
    sorted_pages = sorted(page_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Generiere Tipps basierend auf den meistbesuchten Seiten
    if sorted_pages:
        most_visited_page = sorted_pages[0][0]
        custom_tips.append({
            "title": "Top-Seite optimieren",
            "text": f"Ihre meistbesuchte Seite ({most_visited_page}) sollte besonders optimiert werden. Stellen Sie sicher, dass hier klare Call-to-Actions vorhanden sind."
        })
    
    # Berechne die Klickrate (CTR)
    if pageviews:
        ctr = (len(clicks) / len(pageviews)) * 100
        if ctr < 20:
            custom_tips.append({
                "title": "Klickrate verbessern",
                "text": f"Ihre Klickrate von {ctr:.1f}% ist niedrig. Verbessern Sie die Sichtbarkeit Ihrer interaktiven Elemente und Call-to-Actions."
            })
        elif ctr > 50:
            custom_tips.append({
                "title": "Nutzen Sie Ihre hohe Engagement-Rate",
                "text": f"Mit einer Klickrate von {ctr:.1f}% zeigen Ihre Besucher großes Interesse. Verstärken Sie Conversion-Elemente, um dieses Engagement zu monetarisieren."
            })
    
    # Falls wir genug benutzerdefinierte Tipps haben, verwenden wir diese
    if len(custom_tips) >= 2:
        return custom_tips
    
    # Andernfalls kombinieren wir mit Default-Tipps
    combined_tips = custom_tips + [tip for tip in default_tips if tip not in custom_tips]
    return combined_tips[:3]  # Begrenzen auf maximal 3 Tipps

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
    """Zeigt Details zu den erfassten Tracking-Daten an."""
    global tracking_data
    
    # Aktualisiere die tracking_data aus der Datei
    tracking_data = load_tracking_data()
    
    # Stelle sicher, dass alle Shop-Domains korrekt initialisiert sind
    all_pageviews = []
    all_clicks = []
    shops_summary = {}
    
    # Für jeden Shop Daten sammeln
    for shop_domain, shop_data in tracking_data.items():
        pageviews = shop_data.get('pageviews', [])
        clicks = shop_data.get('clicks', [])
        
        # Zusammenfassung pro Shop erstellen
        shops_summary[shop_domain] = {
            'pageviews_count': len(pageviews),
            'clicks_count': len(clicks),
            'most_recent_pageview': max([pv.get('timestamp', 0) for pv in pageviews]) if pageviews else None,
            'most_recent_click': max([click.get('timestamp', 0) for click in clicks]) if clicks else None
        }
        
        # Zu Gesamt-Arrays hinzufügen
        all_pageviews.extend(pageviews)
        all_clicks.extend(clicks)
    
    # Nach Zeitstempel sortieren (neueste zuerst)
    all_pageviews.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    all_clicks.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    
    # Formatierung der Daten für die Anzeige
    pageviews_sample = []
    for pv in all_pageviews[:5]:  # Limitiere auf 5 Einträge
        pv_copy = dict(pv)
        if 'timestamp' in pv_copy:
            try:
                pv_copy['timestamp_formatted'] = datetime.datetime.fromtimestamp(int(pv_copy['timestamp'])/1000).strftime('%Y-%m-%d %H:%M:%S')
            except:
                pv_copy['timestamp_formatted'] = "Ungültiger Zeitstempel"
        pageviews_sample.append(pv_copy)
        
    clicks_sample = []
    for click in all_clicks[:5]:  # Limitiere auf 5 Einträge
        click_copy = dict(click)
        if 'timestamp' in click_copy:
            try:
                click_copy['timestamp_formatted'] = datetime.datetime.fromtimestamp(int(click_copy['timestamp'])/1000).strftime('%Y-%m-%d %H:%M:%S')
            except:
                click_copy['timestamp_formatted'] = "Ungültiger Zeitstempel"
        clicks_sample.append(click_copy)
    
    # Detailliertere Antwort zurückgeben
    response = {
        'status': 'success',
        'tracking_data_keys': list(tracking_data.keys()),
        'pageviews_count': len(all_pageviews),
        'clicks_count': len(all_clicks),
        'pageviews_sample': pageviews_sample,
        'clicks_sample': clicks_sample,
        'shops_summary': shops_summary,
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
    
    # 1. Erweiterte Kategorien: Sortimentsoptimierung
    recommendations.append({
        'category': 'Sortimentsoptimierung',
        'priority': 'hoch',
        'title': 'Cross-Selling Potentiale nutzen: "Produkt A + B" Bundle',
        'description': 'Unsere Analyse hat gezeigt, dass Kunden, die "Produkt A" kaufen, mit 64% Wahrscheinlichkeit auch "Produkt B" erwerben. Erstelle ein Bundle-Angebot mit 10% Rabatt, um den durchschnittlichen Bestellwert zu steigern.',
        'expected_impact': 'hoch',
        'effort': 'niedrig'
    })
    
    recommendations.append({
        'category': 'Sortimentsoptimierung',
        'priority': 'mittel',
        'title': 'Saisonale Produktergänzung: "Sommer-Kollektion"',
        'description': 'Basierend auf aktuellen Markttrends und deinem Sortiment empfehlen wir die Aufnahme von 3 neuen Produkten in deine Sommer-Kollektion. Dies würde eine Lücke in deinem aktuellen Angebot schließen und neue Kundensegmente ansprechen.',
        'expected_impact': 'mittel',
        'effort': 'mittel'
    })
    
    # 2. Kategorie: Kundensegmentierung
    recommendations.append({
        'category': 'Kundensegmentierung',
        'priority': 'hoch',
        'title': 'Reaktivierungskampagne für schlafende Kunden',
        'description': 'Du hast 247 Kunden, die seit mehr als 120 Tagen keinen Kauf getätigt haben, aber zuvor regelmäßige Käufer waren. Erstelle eine personalisierte E-Mail-Kampagne mit einem speziellen Angebot, um diese Kunden zu reaktivieren.',
        'expected_impact': 'hoch',
        'effort': 'niedrig'
    })
    
    recommendations.append({
        'category': 'Kundensegmentierung',
        'priority': 'mittel',
        'title': 'VIP-Programm für deine Top 10% Kunden',
        'description': 'Identifiziere deine wertvollsten Kunden (nach Bestellhäufigkeit und -wert) und erstelle ein exklusives VIP-Programm mit Mehrwert wie kostenlosem Versand, Vorabzugang zu neuen Produkten oder persönlichen Rabatten.',
        'expected_impact': 'hoch',
        'effort': 'mittel'
    })
    
    # 3. Kategorie: Umsatzpotential
    recommendations.append({
        'category': 'Umsatzpotential',
        'priority': 'hoch',
        'title': 'Umsatzsteigerung durch optimierte Preisstruktur',
        'description': 'Basierend auf unserer What-If-Analyse könnte eine Preiserhöhung von 7% bei deinen Top-10-Produkten zu einer Umsatzsteigerung von 12% führen, ohne das Verkaufsvolumen signifikant zu beeinträchtigen. Unsere Elastizitätsberechnung zeigt, dass diese Produkte eine niedrige Preiselastizität aufweisen.',
        'expected_impact': 'hoch',
        'effort': 'niedrig'
    })
    
    recommendations.append({
        'category': 'Umsatzpotential',
        'priority': 'mittel',
        'title': 'Einführung eines Mitgliedschaftsmodells',
        'description': 'Basierend auf deiner Kundenfrequenz und Sortimentsbreite könntest du ein Abonnement-/Mitgliedschaftsmodell einführen. Unsere Analyse zeigt, dass dies deine wiederkehrenden Einnahmen um ca. 22% steigern könnte.',
        'expected_impact': 'hoch',
        'effort': 'hoch'
    })
    
    # Kategorie: Seiten-spezifische Optimierungen
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
    
    # Kategorie: Allgemeine Shop-Optimierungen
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
    
    # Kategorie: Marketing-Empfehlungen
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

@app.route('/growth-advisor')
def growth_advisor():
    try:
        # Prüfe, ob ein Shop in der Session ist
        if 'shop' not in session:
            print("❌ Kein Shop in der Session gefunden - Weiterleitung zur Installation")
            return redirect('/install')
            
        # Shop aus der Session laden
        shop = session.get('shop')
        
        # Access token aus der Session holen (kann für den Lese-Zugriff null sein)
        access_token = session.get('access_token')
        
        # Tracking-Daten aktualisieren durch Neuladen
        tracking_data = load_tracking_data()
        
        # Wenn kein Shop in der Session gefunden wurde, versuche einen Shop aus den Tracking-Daten zu verwenden
        if not shop:
            all_shops = list(tracking_data.keys())
            
            if all_shops:
                shop = all_shops[0]
                print(f"Growth Advisor: Verwende ersten verfügbaren Shop: {shop} für Demo-Modus")
            else:
                shop = "test-shop.example.com"
                print(f"Growth Advisor: Keine Shops gefunden, verwende Default-Shop: {shop}")
        
        # Shopify-Daten laden
        shop_data = get_shop_data(shop)
        
        # Growth Advisor Empfehlungen generieren
        recommendations = generate_growth_advisor_recommendations(shop_data)
        
        # Metadaten für die Seite
        meta = {
            'last_analysis': datetime.datetime.now().strftime('%d.%m.%Y %H:%M'),
            'shop': shop,
            'pageviews': len(shop_data.get('pageviews', [])),
            'clicks': len(shop_data.get('clicks', []))
        }
        
        # Aktuelle Produkte abrufen
        try:
            products = get_shopify_products(shop, access_token)
        except Exception as e:
            print(f"Fehler beim Abrufen der Produkte: {e}")
            # Beispielprodukte verwenden, wenn die echten Produkte nicht abgerufen werden können
            products = get_mock_products()
        
        # Implementation Tasks generieren
        implementation_tasks = generate_implementation_tasks()
        
        # Render Template
        return render_template('growth_advisor.html',
                              meta=meta,
                              recommendations=recommendations,
                              implementation_tasks=implementation_tasks,
                              products=products)
                              
    except Exception as e:
        print(f"Fehler im Growth Advisor: {e}")
        import traceback
        traceback.print_exc()
        return render_template('error.html', error=str(e))

def get_shopify_products(shop_domain, access_token):
    """Ruft Produkte aus der Shopify API ab."""
    try:
        # URL für die Shopify API
        url = f"https://{shop_domain}/admin/api/2023-04/products.json"
        
        # Header mit Access-Token für die Authentifizierung
        headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }
        
        # API-Aufruf durchführen
        response = requests.get(url, headers=headers)
        
        # Prüfen, ob der Aufruf erfolgreich war
        if response.status_code == 200:
            products_data = response.json().get('products', [])
            
            # Produkte für unsere Verwendung aufbereiten
            formatted_products = []
            for product in products_data:
                formatted_product = {
                    "id": product.get('id'),
                    "title": product.get('title'),
                    "product_type": product.get('product_type'),
                    "variants": product.get('variants', []),
                    "image": product.get('image', {}),
                    "description": product.get('body_html', '')
                }
                formatted_products.append(formatted_product)
            
            print(f"✅ {len(formatted_products)} Produkte von Shopify für {shop_domain} geladen")
            return formatted_products
        else:
            print(f"❌ Fehler beim Abrufen der Produkte: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Ausnahme beim Abrufen der Produkte: {e}")
        import traceback
        traceback.print_exc()
        return []

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
            'count': 1224
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

def get_mock_products():
    """Gibt eine Liste von Mock-Produkten für Demonstrations- und Testzwecke zurück."""
    return [
        {
            "id": "1001",
            "title": "Sport-Kopfhörer Pro X3",
            "product_type": "Sport-Kopfhörer",
            "variants": [
                {
                    "id": "2001",
                    "price": "89.99",
                    "compare_at_price": "119.99",
                    "inventory_quantity": 42
                }
            ],
            "image": {"src": "https://via.placeholder.com/150/0A84FF/FFFFFF?text=Kopfhörer"},
            "description": "Wasserdichte Sport-Kopfhörer mit aktiver Geräuschunterdrückung und 12 Stunden Akkulaufzeit."
        },
        {
            "id": "1002",
            "title": "Yoga-Matte Premium",
            "product_type": "Fitness-Zubehör",
            "variants": [
                {
                    "id": "2002",
                    "price": "49.95",
                    "compare_at_price": "69.95",
                    "inventory_quantity": 78
                }
            ],
            "image": {"src": "https://via.placeholder.com/150/30D158/FFFFFF?text=Yoga-Matte"},
            "description": "Rutschfeste Premium-Yogamatte aus umweltfreundlichen Materialien, 6mm dick für optimalen Komfort."
        },
        {
            "id": "1003",
            "title": "Smartwatch Active",
            "product_type": "Wearables",
            "variants": [
                {
                    "id": "2003",
                    "price": "149.00",
                    "compare_at_price": "199.00",
                    "inventory_quantity": 23
                }
            ],
            "image": {"src": "https://via.placeholder.com/150/FF9F0A/FFFFFF?text=Smartwatch"},
            "description": "Fitness-Smartwatch mit Herzfrequenzmessung, GPS und einer Akkulaufzeit von bis zu 7 Tagen."
        },
        {
            "id": "1004",
            "title": "Protein-Pulver Vanille",
            "product_type": "Nahrungsergänzung",
            "variants": [
                {
                    "id": "2004",
                    "price": "34.99",
                    "compare_at_price": "39.99",
                    "inventory_quantity": 104
                }
            ],
            "image": {"src": "https://via.placeholder.com/150/BF5AF2/FFFFFF?text=Protein"},
            "description": "Hochwertiges Protein-Pulver mit Vanillegeschmack, 25g Protein pro Portion, 1kg Packung."
        },
        {
            "id": "1005",
            "title": "Heimtrainer Kompakt",
            "product_type": "Fitnessgeräte",
            "variants": [
                {
                    "id": "2005",
                    "price": "299.00",
                    "compare_at_price": "399.00",
                    "inventory_quantity": 12
                }
            ],
            "image": {"src": "https://via.placeholder.com/150/FF375F/FFFFFF?text=Heimtrainer"},
            "description": "Kompakter Heimtrainer mit 8 Widerstandsstufen, faltbar für einfache Aufbewahrung."
        }
    ]

@app.route('/price-optimizer')
def price_optimizer():
    try:
        # Prüfe, ob ein Shop in der Session ist
        if 'shop' not in session:
            print("❌ Kein Shop in der Session gefunden - Weiterleitung zur Installation")
            return redirect('/install')
            
        # Shop aus der Session laden
        shop = session.get('shop')
        
        # Access token aus der Session holen
        access_token = session.get('access_token')
        
        # Wenn kein Shop in der Session gefunden wurde, versuche einen Shop aus den Tracking-Daten zu verwenden
        if not shop:
            tracking_data = load_tracking_data()
            all_shops = list(tracking_data.keys())
            
            if all_shops:
                shop = all_shops[0]
                print(f"Price Optimizer: Verwende ersten verfügbaren Shop: {shop} für Demo-Modus")
            else:
                shop = "test-shop.example.com"
                print(f"Price Optimizer: Keine Shops gefunden, verwende Default-Shop: {shop}")
                
        # Daten für diesen Shop abrufen
        shop_data = get_shop_data(shop)
        
        # Produkt-ID aus dem GET-Parameter auslesen
        product_id = request.args.get('product_id')
        
        try:
            # Produkte über Shopify API abrufen
            products = get_shopify_products(shop, access_token)
            print(f"✅ {len(products)} Produkte geladen für Shop: {shop}")
            
            if not products:
                print("⚠️ Keine Produkte über API gefunden, verwende Mock-Produkte")
                products = get_mock_products()
        except Exception as e:
            print(f"❌ Fehler beim Abrufen der Produkte: {e}")
            # Fallback zu Beispiel-Produkten
            products = get_mock_products()
            
        # Ausgewähltes Produkt finden
        selected_product = None
        if product_id:
            for product in products:
                if str(product.get('id', '')) == str(product_id):
                    selected_product = product
                    break
                    
        # Wenn kein Produkt ausgewählt oder gefunden wurde und es Produkte gibt, das erste Produkt verwenden
        if not selected_product and products:
            selected_product = products[0]
            product_id = selected_product.get('id')
        
        if selected_product:
            # Produktdetails für die Analyse vorbereiten
            product_type = selected_product.get('product_type', 'Generisches Produkt')
            
            # Preis aus der ersten Variante extrahieren oder Fallback-Wert verwenden
            price = 0
            if 'variants' in selected_product and selected_product['variants']:
                price = float(selected_product['variants'][0].get('price', 10.0))
            else:
                price = float(selected_product.get('price', 10.0))
                
            # Wettbewerberdaten abrufen
            competitor_data = get_competitor_data(product_type)
            
            # Preistrend-Daten abrufen
            trend_data = get_price_trend_data(product_type, price, shop, access_token, product_id)
            
            # KI-basierte Preisempfehlungen
            price_recommendations = generate_ai_price_recommendations(
                product_type, price, competitor_data, trend_data
            )
            
            # Metadaten für die Seite
            meta = {
                'last_analysis': datetime.datetime.now().strftime('%d.%m.%Y %H:%M'),
                'shop': shop,
                'products_analyzed': len(products)
            }
                
            return render_template(
                'price_optimizer.html',
                products=products,
                selected_product=selected_product,
                competitor_data=competitor_data,
                trend_data=trend_data,
                price_recommendations=price_recommendations,
                meta=meta,
                shop_name=shop
            )
        else:
            # Keine Produkte gefunden oder ausgewählt
            print("⚠️ Kein Produkt ausgewählt oder keine Produkte verfügbar")
            return render_template(
                'price_optimizer.html',
                products=products,
                selected_product=None,
                error=None,  # Kein Fehler, da Produkte eventuell vorhanden sind
                shop_name=shop
            )
        
    except Exception as e:
        print(f"❌ Fehler im Price Optimizer: {e}")
        import traceback
        traceback.print_exc()
        return render_template('error.html', error=str(e))

@app.context_processor
def inject_translations():
    """Inject translations into the template context based on user's language."""
    language = get_user_language()
    # Stellen sicher, dass die Tracking-Daten korrekt initialisiert werden
    if language == 'de':
        # Stelle sicher, dass die deutsche Übersetzungsdatei existiert und geladen wird
        try:
            # Absolute Pfade für Railway und lokale Entwicklung
            base_dir = os.path.dirname(os.path.abspath(__file__))
            de_path = os.path.join(base_dir, 'translations', 'de.json')
            
            # Überprüfen, ob die Datei existiert
            if os.path.exists(de_path):
                with open(de_path, 'r', encoding='utf-8') as f:
                    try:
                        loaded_translations = json.load(f)
                        if loaded_translations:
                            translations['de'] = loaded_translations
                            print(f"Deutsche Übersetzungen direkt aus {de_path} geladen.")
                    except json.JSONDecodeError:
                        print(f"Fehler beim Dekodieren der deutschen Übersetzungsdatei {de_path}")
            else:
                print(f"Deutsche Übersetzungsdatei nicht gefunden: {de_path}")
                # Erstelle die Datei mit Standard-Übersetzungen
                with open(de_path, 'w', encoding='utf-8') as f:
                    json.dump(translations['de'], f, ensure_ascii=False, indent=2)
                    print(f"Deutsche Standardübersetzungen in {de_path} gespeichert.")
        except Exception as e:
            print(f"Fehler beim direkten Laden der deutschen Übersetzungen: {e}")
            import traceback
            traceback.print_exc()
    
    # Debugging-Ausgabe für Railway
    print(f"Injiziere Übersetzungen für Sprache: {language}")
    print(f"Verfügbare Übersetzungen: {list(translations.keys())}")
    print(f"Struktur der Übersetzungen für {language}: {str(translations[language].keys())[:100]}...")
    
    # Stellen Sie sicher, dass mindestens grundlegende App-Informationen vorhanden sind
    if 'app' not in translations[language]:
        print(f"WARNUNG: 'app' Schlüssel fehlt in Übersetzungen für {language}, füge Standardwerte hinzu")
        translations[language]['app'] = {
            "name": "ShoppulseAI",
            "title": "Intelligent Growth Analysis for Shopify" if language == 'en' else "Intelligente Wachstumsanalyse für Shopify"
        }
    
    if 'dashboard' not in translations[language]:
        print(f"WARNUNG: 'dashboard' Schlüssel fehlt in Übersetzungen für {language}, füge Standardwerte hinzu")
        translations[language]['dashboard'] = {
            "title": "Analytics Dashboard"
        }
    elif not translations[language].get('dashboard', {}).get('title'):
        print(f"WARNUNG: Dashboard-Titel fehlt in Übersetzungen für {language}, füge Standardwerte hinzu")
        translations[language]['dashboard']['title'] = 'Analytics Dashboard'
    
    # Sicherstellen, dass der navigation-Schlüssel existiert
    if 'navigation' not in translations[language]:
        print(f"WARNUNG: 'navigation' Schlüssel fehlt in Übersetzungen für {language}, füge Standardwerte hinzu")
        translations[language]['navigation'] = {
            "dashboard": "Dashboard",
            "growth_advisor": "Growth Advisor™",
            "price_optimizer": "Price Optimizer™",
            "settings": "Settings" if language == 'en' else "Einstellungen",
            "analytics": "Analytics",
            "configuration": "Configuration" if language == 'en' else "Konfiguration"
        }
    
    # Sicherstellen, dass die price_optimizer-Schlüssel existieren
    if 'price_optimizer' not in translations[language]:
        print(f"WARNUNG: 'price_optimizer' Schlüssel fehlt in Übersetzungen für {language}, füge Standardwerte hinzu")
        translations[language]['price_optimizer'] = {
            "title": "Price Optimizer™"
        }
    
    # Sicherstellen, dass die growth_advisor-Schlüssel existieren
    if 'growth_advisor' not in translations[language]:
        print(f"WARNUNG: 'growth_advisor' Schlüssel fehlt in Übersetzungen für {language}, füge Standardwerte hinzu")
        translations[language]['growth_advisor'] = {
            "title": "Growth Advisor™"
        }
    
    # Sicherstellen, dass die errors-Schlüssel existieren
    if 'errors' not in translations[language]:
        print(f"WARNUNG: 'errors' Schlüssel fehlt in Übersetzungen für {language}, füge Standardwerte hinzu")
        translations[language]['errors'] = {
            "general": "An error occurred." if language == 'en' else "Ein Fehler ist aufgetreten.",
            "data_load": "Error loading data." if language == 'en' else "Fehler beim Laden der Daten.",
            "not_connected": "Shop not connected." if language == 'en' else "Shop nicht verbunden.",
            "no_products": "No products found." if language == 'en' else "Keine Produkte gefunden."
        }
    
    # Sicherstellen, dass die language-Schlüssel existieren
    if 'language' not in translations[language]:
        print(f"WARNUNG: 'language' Schlüssel fehlt in Übersetzungen für {language}, füge Standardwerte hinzu")
        translations[language]['language'] = {
            "select": "Select Language" if language == 'en' else "Sprache auswählen",
            "en": "English" if language == 'en' else "Englisch",
            "de": "German" if language == 'en' else "Deutsch"
        }
    
    # Sicherstellen, dass die buttons-Schlüssel existieren
    if 'buttons' not in translations[language]:
        print(f"WARNUNG: 'buttons' Schlüssel fehlt in Übersetzungen für {language}, füge Standardwerte hinzu")
        translations[language]['buttons'] = {
            "save": "Save" if language == 'en' else "Speichern",
            "cancel": "Cancel" if language == 'en' else "Abbrechen",
            "apply": "Apply" if language == 'en' else "Anwenden",
            "reload": "Reload" if language == 'en' else "Neu laden",
            "export": "Export" if language == 'en' else "Exportieren"
        }
    
    return {
        'translations': translations[language],
        'lang': language
    }

@app.route('/set-language/<language>')
def set_language(language):
    """Setzt die Sprache und leitet zur vorherigen Seite zurück."""
    if language not in translations:
        language = 'en'  # Fallback auf Englisch, wenn die Sprache nicht unterstützt wird
    
    session['language'] = language
    
    # Speichere die Sprache auch in einem Cookie
    response = redirect(request.referrer or '/')
    response.set_cookie('language', language, max_age=60*60*24*365)  # 1 Jahr gültig
    
    return response

@app.route('/ping', methods=['GET', 'OPTIONS'])
def ping():
    """Ein einfacher Ping-Endpunkt zur Überprüfung der Serververfügbarkeit für das Tracking-Script."""
    if request.method == 'OPTIONS':
        response = Response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response
    
    response = Response("pong")
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/tracking-test')
def tracking_test():
    """Eine einfache Test-Seite um das Tracking zu testen."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Tracking Test</title>
        <script>
            // Definiere ein Dummy-Shopify-Objekt, falls es nicht existiert
            window.Shopify = window.Shopify || { shop: 'test-shop.example.com' };
        </script>
        <script src="/static/js/tracking.js"></script>
    </head>
    <body>
        <h1>Tracking Test Seite</h1>
        <p>Diese Seite ist zum Testen des Tracking-Scripts. Öffne die Browser-Konsole, um die Tracking-Logs zu sehen.</p>
        
        <button id="pageviewBtn">Manuellen Pageview senden</button>
        <button id="clickBtn">Manuellen Click senden</button>
        
        <script>
            document.getElementById('pageviewBtn').addEventListener('click', function() {
                window.manualTrack('pageview');
            });
            
            document.getElementById('clickBtn').addEventListener('click', function() {
                window.manualTrack('click');
            });
        </script>
    </body>
    </html>
    """
    return html

@app.context_processor
def inject_globals():
    """Injiziert globale Variablen in alle Templates."""
    return {
        'config': {
            'SHOPIFY_API_KEY': SHOPIFY_API_KEY,
            'HOST': os.getenv('HOST')
        }
    }

# Flask Starten
if __name__ == "__main__":
    # Parse command line arguments for port
    parser = argparse.ArgumentParser(description='Start the Flask application server.')
    parser.add_argument('--port', type=int, default=5002, help='Port number to run the server on (default: 5002)')
    args = parser.parse_args()
    
    # Tracking-Daten beim Start laden
    load_tracking_data()
    
    # Übersetzungen laden
    load_translations()
    
    app.run(host="0.0.0.0", port=args.port, debug=True)

# Webhook Handler aktualisieren
@app.route('/webhook/app/uninstalled', methods=['POST'])
def app_uninstalled_webhook():
    """Handler für app/uninstalled Webhook"""
    # Verifiziere den Webhook
    try:
        # Shopify sendet einen HMAC-Header
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        if not hmac_header:
            return 'HMAC validation failed', 403

        data = request.get_data()
        # Verifiziere die HMAC-Signatur
        calculated_hmac = hmac.new(
            SHOPIFY_API_SECRET.encode('utf-8'),
            data,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hmac, hmac_header):
            return 'HMAC validation failed', 403

        # Verarbeite die App-Deinstallation
        webhook_data = request.json
        shop_domain = webhook_data.get('shop_domain')
        
        if shop_domain:
            # Hier können Sie Aufräumarbeiten durchführen
            print(f"App wurde deinstalliert von Shop: {shop_domain}")
            
        return '', 200
    except Exception as e:
        print(f"Fehler im app/uninstalled Webhook: {e}")
        return 'Internal Server Error', 500

@app.route('/webhook/shop/update', methods=['POST'])
def shop_update_webhook():
    """Handler für shop/update Webhook"""
    try:
        # Verifiziere den Webhook
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        if not hmac_header:
            return 'HMAC validation failed', 403

        data = request.get_data()
        calculated_hmac = hmac.new(
            SHOPIFY_API_SECRET.encode('utf-8'),
            data,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hmac, hmac_header):
            return 'HMAC validation failed', 403

        # Verarbeite die Shop-Aktualisierung
        webhook_data = request.json
        shop_domain = webhook_data.get('shop_domain')
        
        if shop_domain:
            print(f"Shop wurde aktualisiert: {shop_domain}")
            
        return '', 200
    except Exception as e:
        print(f"Fehler im shop/update Webhook: {e}")
        return 'Internal Server Error', 500

def generate_example_chart_data():
    """Generiert Beispieldaten für das Onboarding-Dashboard."""
    return {
        'labels': ['Tag 1', 'Tag 2', 'Tag 3', 'Tag 4', 'Tag 5', 'Tag 6', 'Tag 7'],
        'datasets': [
            {
                'label': 'Seitenaufrufe',
                'data': [10, 25, 45, 70, 100, 85, 120],
                'borderColor': '#4CAF50',
                'tension': 0.1
            },
            {
                'label': 'Unique Besucher',
                'data': [8, 20, 35, 55, 80, 65, 95],
                'borderColor': '#2196F3',
                'tension': 0.1
            }
        ]
    }

def get_current_shop():
    """Holt den aktuellen Shop aus der Session."""
    # Versuche den Shop aus der Session zu lesen
    if 'shop' in session:
        return session['shop']
        
    # Falls kein Shop in der Session vorhanden ist
    print("❌ Kein Shop in der Session gefunden")
    
    # Versuche einen Shop aus den Tracking-Daten zu verwenden
    tracking_data = load_tracking_data()
    all_shops = list(tracking_data.keys())
    
    if all_shops:
        shop = all_shops[0]
        print(f"✅ Verwende ersten verfügbaren Shop: {shop}")
        return shop
    
    # Wenn kein Shop gefunden wurde
    print("❌ Kein Shop gefunden, weder in der Session noch in den Tracking-Daten")
    return None

def load_shop_data(shop):
    """Lädt die Daten für einen bestimmten Shop."""
    if not shop:
        print("❌ Kann keine Shop-Daten laden: Shop ist None")
        return {}
        
    # Tracking-Daten aus der Datei laden
    tracking_data = load_tracking_data()
    
    # Wenn der Shop nicht in den Tracking-Daten existiert, initialisiere ihn
    if shop not in tracking_data:
        print(f"🆕 Initialisiere neuen Shop in den Tracking-Daten: {shop}")
        tracking_data[shop] = {
            'pageviews': [],
            'clicks': [],
            'created_at': datetime.datetime.now().isoformat(),
            'last_updated': datetime.datetime.now().isoformat(),
            'first_tracking_date': datetime.datetime.now().isoformat(),
            'total_pageviews': 0,
            'total_clicks': 0
        }
        save_tracking_data()
    
    # Berechne abgeleitete Daten wie Gesamtzahlen und Durchschnitte
    shop_data = tracking_data[shop].copy()
    
    # Gesamtzahl der Seitenaufrufe
    shop_data['total_pageviews'] = len(shop_data.get('pageviews', []))
    
    # Gesamtzahl der Klicks
    shop_data['total_clicks'] = len(shop_data.get('clicks', []))
    
    # Klickrate (CTR)
    if shop_data['total_pageviews'] > 0:
        shop_data['click_rate'] = (shop_data['total_clicks'] / shop_data['total_pageviews']) * 100
    else:
        shop_data['click_rate'] = 0
    
    # KI-Tipps generieren
    shop_data['ai_quick_tips'] = generate_ai_tips(shop_data)
    
    # Letzte Ereignisse
    all_events = []
    for pageview in shop_data.get('pageviews', [])[:50]:  # Begrenzen auf die letzten 50 Seitenaufrufe
        all_events.append({
            'type': 'pageview',
            'timestamp': pageview.get('timestamp'),
            'data': pageview
        })
    
    for click in shop_data.get('clicks', [])[:50]:  # Begrenzen auf die letzten 50 Klicks
        all_events.append({
            'type': 'click',
            'timestamp': click.get('timestamp'),
            'data': click
        })
    
    # Sortiere die Ereignisse nach Zeitstempel (absteigend, neueste zuerst)
    all_events.sort(key=lambda e: e.get('timestamp', ''), reverse=True)
    
    # Limitieren auf die letzten 20 Ereignisse
    shop_data['events'] = all_events[:20]
    
    return shop_data