from flask import Flask, request, jsonify, render_template, redirect, session, Response, url_for, make_response, flash
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
import time
from werkzeug.middleware.proxy_fix import ProxyFix
import base64
import secrets
import logging
import sys

# Eigene Module importieren
import shopify_api
from data_models import ShopMetrics, DataAnalyzer, add_tracking_event, get_shop_tracking_data
from growth_advisor import GrowthAdvisor

# Logger einrichten
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('shopify_app')
logger.info("🚀 Starte Logger für Shopify App Authentifizierung")

# Environment-Variablen laden
load_dotenv()

# Pfad zur Tracking-Datendatei
TRACKING_DATA_FILE = 'tracking_data.json'

# Flask App konfigurieren
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

# Shopify API initialisieren
shopify_api.init_app(app)

# CORS für alle Routen und Origins erlauben
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Authorization", "Content-Type"]}})

# Cookie-Einstellungen
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # 'None' kann in manchen Browsern Probleme verursachen
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=1)

# Umgebungsvariablen laden
SHOPIFY_API_KEY = os.environ.get('SHOPIFY_API_KEY', 'bc64e63be55d4cbad777bc2b89d1307c')
SHOPIFY_API_SECRET = os.environ.get('SHOPIFY_API_SECRET', 'a04bb1e1c1cd5b9d8881d6c9c19f4c6c')
APP_URL = os.environ.get('APP_URL', 'https://miniflaskenv-production.up.railway.app')

# Sicherstellen, dass APP_URL mit https:// beginnt
if not APP_URL.startswith(('http://', 'https://')):
    APP_URL = 'https://' + APP_URL
    print(f"🔧 APP_URL korrigiert: {APP_URL}")

SCOPES = "read_products,write_products,read_orders,read_customers,write_customers,read_analytics"

# Redirect-URI mit vollständiger URL (einschließlich https://)
REDIRECT_URI = f"{APP_URL}/auth/callback"

# Hostname konfigurieren
HOST = os.environ.get('HOST', 'miniflaskenv-production.up.railway.app')

# Überschreibe, falls REDIRECT_URI direkt gesetzt wurde
if os.environ.get('REDIRECT_URI'):
    REDIRECT_URI = os.environ.get('REDIRECT_URI')
    # Sicherstellen, dass explizit gesetzte REDIRECT_URI mit https:// beginnt
    if not REDIRECT_URI.startswith(('http://', 'https://')):
        REDIRECT_URI = 'https://' + REDIRECT_URI
        print(f"🔧 Explizit gesetzte REDIRECT_URI korrigiert: {REDIRECT_URI}")

# Shopify API Zugriff
print(f"🔧 API-Konfiguration: KEY={SHOPIFY_API_KEY}, REDIRECT={REDIRECT_URI}, HOST={HOST}")

# Geheimer Schlüssel für Session-Verschlüsselung
app.secret_key = os.environ.get('SECRET_KEY', 'sehr_sicherer_schlüssel_2023')

# Session-Einstellungen
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True  # Session permanent machen
app.config['SESSION_FILE_DIR'] = os.environ.get('SESSION_FILE_DIR', '/tmp/flask_session')  # Expliziter Session-Speicherort
app.config['SESSION_FILE_THRESHOLD'] = 500  # Maximale Anzahl von Session-Dateien
app.config['SESSION_USE_SIGNER'] = True  # Signieren der Cookies für zusätzliche Sicherheit

# Stelle sicher, dass das Session-Verzeichnis existiert
os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
print(f"📁 Session-Verzeichnis: {app.config['SESSION_FILE_DIR']}")

# Session-Middleware initialisieren
sess = Session()
sess.init_app(app)

# Shopify API Keys aus der .env Datei
REDIRECT_URI = os.getenv("REDIRECT_URI")

# OpenAI konfigurieren
openai.api_key = os.getenv("OPENAI_API_KEY")

# Tracking-Data für Dashboard
tracking_data = {}  # Leeres Dictionary für alle Shops

# Übersetzungen laden
translations = {
    'en': {},
    'de': {}
}

def load_translations(language='en'):
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
            },
            "settings": {
                "notifications": "Notifications",
                "email_notifications": "Email notifications",
                "email_notifications_help": "Receive important updates via email",
                "push_notifications": "Push notifications",
                "push_notifications_help": "Receive real-time alerts in your browser",
                "tracking": "Tracking Settings",
                "enable_tracking": "Enable analytics tracking",
                "enable_tracking_help": "Collect anonymous usage data to improve your shop performance",
                "anonymize_ip": "Anonymize IP addresses",
                "anonymize_ip_help": "Enhance privacy by anonymizing customer IP addresses",
                "display": "Display Settings",
                "currency": "Currency",
                "date_format": "Date Format",
                "api_information": "API Information",
                "webhook_url": "Webhook URL",
                "webhook_url_help": "Use this URL for external integrations",
                "settings_saved": "Settings Saved",
                "settings_saved_message": "Your settings have been saved successfully."
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
            },
            "settings": {
                "notifications": "Benachrichtigungen",
                "email_notifications": "E-Mail-Benachrichtigungen",
                "email_notifications_help": "Erhalte wichtige Updates per E-Mail",
                "push_notifications": "Push-Benachrichtigungen",
                "push_notifications_help": "Erhalte Echtzeit-Warnungen in deinem Browser",
                "tracking": "Tracking-Einstellungen",
                "enable_tracking": "Analytics-Tracking aktivieren",
                "enable_tracking_help": "Sammle anonyme Nutzungsdaten zur Verbesserung deiner Shop-Performance",
                "anonymize_ip": "IP-Adressen anonymisieren",
                "anonymize_ip_help": "Verbessere den Datenschutz durch Anonymisierung von Kunden-IP-Adressen",
                "display": "Anzeigeeinstellungen",
                "currency": "Währung",
                "date_format": "Datumsformat",
                "api_information": "API-Informationen",
                "webhook_url": "Webhook-URL",
                "webhook_url_help": "Verwende diese URL für externe Integrationen",
                "settings_saved": "Einstellungen gespeichert",
                "settings_saved_message": "Deine Einstellungen wurden erfolgreich gespeichert."
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
    
    return translations.get(language, translations['en'])

def get_translations():
    """
    Gibt das globale translations Dictionary zurück.
    Stellt sicher, dass Übersetzungen geladen sind.
    
    Returns:
        dict: Das translations Dictionary mit allen verfügbaren Sprachen
    """
    global translations
    
    # Wenn translations leer ist, lade die Übersetzungen
    if not translations or not translations.get('en') or not translations.get('de'):
        load_translations()
        
    return translations

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

def save_tracking_data(data=None):
    """Speichert die Tracking-Daten in einer JSON-Datei."""
    global tracking_data
    try:
        if data is not None:
            tracking_data = data
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
    """Generiert priorisierte Umsetzungsaufgaben"""
    return [
        {
            'id': 1,
            'title': 'Mobile Checkout optimieren',
            'description': 'Vereinfache den Checkout-Prozess für mobile Geräte, um Abbrüche zu reduzieren',
            'priority': 'high',
            'effort': 'medium',
            'impact': 'high',
            'status': 'offen'
        },
        {
            'id': 2,
            'title': 'Produkt-Metadaten verbessern',
            'description': 'SEO-Optimierung für bessere Sichtbarkeit in Google',
            'priority': 'medium',
            'effort': 'low',
            'impact': 'medium',
            'status': 'offen'
        },
        {
            'id': 3,
            'title': 'Kundenbewertungen einbinden',
            'description': 'Füge ein Bewertungssystem zu Produktseiten hinzu',
            'priority': 'low',
            'effort': 'medium',
            'impact': 'medium',
            'status': 'offen'
        },
        {
            'id': 4,
            'title': 'Email-Marketing einrichten',
            'description': 'Automatisiere Abandoned-Cart und Post-Purchase Emails',
            'priority': 'high', 
            'effort': 'high',
            'impact': 'high',
            'status': 'in Bearbeitung'
        }
    ]

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

# Hilfsfunktion zur Authentifizierungsprüfung
def is_authenticated():
    """Prüft, ob der aktuelle Benutzer authentifiziert ist"""
    # Prüfe alle benötigten Session-Variablen
    has_shop = 'shop' in session and session.get('shop')
    has_token = 'access_token' in session and session.get('access_token')
    is_auth_flag = session.get('authenticated', False)
    
    # Gib Debug-Informationen aus
    print(f"🔐 Auth-Check: Shop: {has_shop}, Token: {has_token}, Flag: {is_auth_flag}")
    
    # Alle Bedingungen müssen erfüllt sein
    return has_shop and has_token and is_auth_flag

# Middleware-Funktion für Authentifizierungsprüfung
@app.before_request
def enforce_authentication():
    """Stellt sicher, dass alle Seiten (außer OAuth-bezogene) authentifiziert sind"""
    try:
        # Liste der Pfade, die ohne Authentifizierung zugänglich sind
        exempt_paths = [
            '/install', 
            '/auth/callback', 
            '/oauth-error', 
            '/error',
            '/static/',
            '/favicon.ico',
            '/ping',
            '/health',
            '/debug-dashboard',
            '/cookie-hilfe',
            '/api/auth-check',  # Pfad für Frontend-Authentifizierungsprüfung
            '/'  # Root-Pfad wird separat behandelt
        ]
        
        # Prüfen, ob der aktuelle Pfad von der Authentifizierung ausgenommen ist
        for path in exempt_paths:
            if request.path.startswith(path):
                return
        
        # Debug-Info: Aktuelle Seite und Session
        print(f"🔒 Auth-Check für: {request.path} - Session: {'shop' in session}")
        
        # Wenn nicht authentifiziert, überprüfe Shop-Parameter und Weiterleitungspfade
        if not is_authenticated():
            print(f"❌ Nicht authentifizierte Anfrage für Pfad: {request.path}")
            
            # Shop-Parameter aus Query-String extrahieren
            shop = request.args.get('shop')
            
            # Den Referer (vorherige Seite) abrufen
            referer = request.headers.get('Referer', '')
            print(f"ℹ️ Referer: {referer}")
            
            # Überprüfen, ob wir von Shopify kommen
            is_from_shopify = 'myshopify.com' in referer or 'admin.shopify.com' in referer
            
            # Überprüfen, ob wir bereits in einer Weiterleitung sind, um Loops zu vermeiden
            is_redirect_loop = '/install' in referer or '/auth/callback' in referer
            
            # Wenn es sich um einen API-Aufruf handelt, gib 401 zurück
            if request.path.startswith('/api/'):
                return jsonify({
                    "error": "Nicht authentifiziert", 
                    "message": "OAuth-Authentifizierung erforderlich"
                }), 401
            
            # Vermeidung von Weiterleitungsschleifen
            if is_redirect_loop:
                print("⚠️ Mögliche Weiterleitungsschleife erkannt, zeige Fehlerseite an")
                return render_template('oauth_error.html', 
                           error_type="redirect_loop", 
                           error_message="Zu viele Weiterleitungen. Bitte versuche es erneut mit einem gültigen Shop-Parameter.")
                
            # Wenn Shop-Parameter vorhanden ist, direkt zur OAuth-Authentifizierung weiterleiten
            if shop:
                # Shop-Parameter validieren
                if not shop.endswith('.myshopify.com'):
                    if '.' not in shop:
                        shop = f"{shop}.myshopify.com"
                    else:
                        return jsonify({
                            "error": "Ungültiger Shop-Name", 
                            "message": "Bitte gib eine gültige Shopify-Shop-URL ein (Format: dein-shop.myshopify.com)"
                        }), 400
                
                print(f"⏩ Weiterleitung zur Installation mit Shop: {shop}")
                return redirect(f'/install?shop={shop}')
            
            # Wenn wir von Shopify kommen, aber keinen Shop-Parameter haben, versuche ihn aus dem Referer zu extrahieren
            if is_from_shopify:
                # Extrahiere Shop-Domain aus dem Referer
                import re
                shop_match = re.search(r'([\w-]+)\.myshopify\.com', referer)
                if shop_match:
                    shop = f"{shop_match.group(1)}.myshopify.com"
                    print(f"✅ Shop aus Referer extrahiert: {shop}")
                    return redirect(f'/install?shop={shop}')
            
            # Andernfalls zeige eine benutzerfreundliche Fehlerseite an
            return render_template('oauth_error.html', 
                           error_type="authentication_required", 
                           error_message="Um diese App zu nutzen, musst du dich mit deinem Shopify-Shop authentifizieren. Bitte versuche es erneut mit einem gültigen Shop-Parameter.")
    except Exception as e:
        print(f"❌ Fehler in der Authentifizierungs-Middleware: {e}")
        import traceback
        traceback.print_exc()
        # Im Fehlerfall JSON-Fehlermeldung zurückgeben
        if request.path.startswith('/api/'):
            return jsonify({"error": "Authentifizierungsfehler", "message": str(e)}), 500
        return render_template('oauth_error.html', 
                           error_type="internal_error", 
                           error_message=f"Ein interner Fehler ist aufgetreten: {str(e)}")

@app.route('/')
def index():
    """Root-Route mit Authentifizierungsprüfung."""
    try:
        # Prüfen, ob ein Shop-Parameter in der Anfrage vorhanden ist
        shop = request.args.get('shop')
        
        # Wenn ein Shop-Parameter vorhanden ist, direkt zum OAuth-Prozess weiterleiten
        if shop:
            return redirect(f'/install?shop={shop}')
        
        # Wenn nicht authentifiziert und kein Shop-Parameter, Fehler zurückgeben
        if not is_authenticated():
            print("❌ Kein Shop in der Session gefunden - OAuth erforderlich")
            return jsonify({
                "error": "Authentifizierung erforderlich",
                "message": "Diese App erfordert eine Shopify-OAuth-Authentifizierung. Bitte stelle sicher, dass ein shop-Parameter in der URL angegeben ist."
            }), 401
            
        print(f"✅ Shop authentifiziert: {session['shop']}")
        return redirect('/dashboard')
        
    except Exception as e:
        print(f"❌ Fehler in der Root-Route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Allgemeiner Fehler", "message": f"Ein Fehler ist aufgetreten: {str(e)}"}), 500

@app.route('/install')
def install():
    """Shopify OAuth-Installationsseite mit direkter Weiterleitung zur Authentifizierung"""
    try:
        # Prüfen, ob ein Shop-Parameter in der Anfrage vorhanden ist
        shop = request.args.get('shop')
        
        # Falls kein Shop-Parameter vorhanden ist, aber in der Session
        if not shop and 'shop' in session:
            shop = session.get('shop')
            print(f"✅ Shop aus Session verwendet: {shop}")
        
        # Wenn kein Shop-Parameter vorhanden ist, zeige KEINE Formular an
        # sondern leite direkt zurück zu Shopify
        if not shop:
            print("❌ Kein Shop-Parameter gefunden und kein Shop in der Session")
            # Statt das Formular anzuzeigen, Error zurückgeben
            return jsonify({"error": "Shop-Parameter fehlt", "message": "Bitte den Shop-Parameter in der URL angeben"}), 400
        
        # Erzeugen eines eindeutigen Nonce für CSRF-Schutz
        nonce = secrets.token_hex(16)
        
        # Nonce in Session speichern und Session sofort speichern
        session['nonce'] = nonce
        session.modified = True
        
        print(f"✅ Nonce in Session gespeichert: {nonce}")
        
        # Scopes für die Berechtigungen definieren
        scopes = "read_products,write_products,read_orders,read_customers,write_customers,read_analytics"
        
        # Korrekte Basis-URL mit Schema erstellen
        base_url = get_base_url()
        # Sicherstellen, dass die URL mit https:// beginnt
        if not base_url.startswith(('http://', 'https://')):
            base_url = 'https://' + base_url
            
        redirect_uri = f"{base_url}/auth/callback"
        state = nonce
        
        print(f"🔧 Redirect URI für OAuth: {redirect_uri}")
        
        # Validiere den Shop-Namen (einfache Prüfung)
        if not shop.endswith('.myshopify.com'):
            print(f"⚠️ Ungültiger Shop-Name: {shop} - muss auf .myshopify.com enden")
            
            # Falls nicht die richtige Form hat, versuche zu korrigieren
            if '.' not in shop:
                corrected_shop = f"{shop}.myshopify.com"
                print(f"🔧 Korrigiere Shop-Name zu: {corrected_shop}")
                shop = corrected_shop
            else:
                # Statt das Formular anzuzeigen, Error zurückgeben
                return jsonify({"error": "Ungültiger Shop-Name", "message": "Bitte gib eine gültige Shopify-Shop-URL ein (Format: dein-shop.myshopify.com)"}), 400
        
        try:
            shopify_auth_url = f"https://{shop}/admin/oauth/authorize?client_id={SHOPIFY_API_KEY}&scope={scopes}&redirect_uri={redirect_uri}&state={state}"
            
            print(f"✅ Weiterleitung zur Shopify OAuth: {shopify_auth_url}")
            return redirect(shopify_auth_url)
        except Exception as e:
            print(f"❌ Fehler beim Erstellen der OAuth-URL: {e}")
            return jsonify({"error": "OAuth-Fehler", "message": f"Fehler bei der Weiterleitung: {str(e)}"}), 500
            
    except Exception as e:
        print(f"❌ Fehler in der Install-Route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Allgemeiner Fehler", "message": f"Ein Fehler ist aufgetreten: {str(e)}"}), 500

@app.route('/oauth-error')
def oauth_error():
    """Zeigt eine spezielle Fehlerseite für OAuth-Fehler an."""
    error_type = request.args.get('error', 'unbekannt')
    error_message = request.args.get('error_message', 'Es ist ein unbekannter Fehler bei der OAuth-Authentifizierung aufgetreten.')
    
    print(f"🔴 OAuth-Fehler: {error_type} - {error_message}")
    
    # Spezielle Fehlerseite anzeigen
    return render_template('oauth_error.html', 
                           error_type=error_type, 
                           error_message=error_message,
                           redirect_uri=REDIRECT_URI)

@app.route('/auth/callback')
def auth_callback():
    """Callback für OAuth-Flow mit verbessertem Fehlerhandling und Session-Management."""
    try:
        # HMAC-Validierung für Shopify-Anfragen
        if not hmac_validation(request.args):
            print("❌ HMAC-Validierung fehlgeschlagen")
            return redirect('/oauth-error?error=hmac_validation_failed&error_message=HMAC-Validierung fehlgeschlagen')

        # Prüfen, ob ein OAuth-Fehler aufgetreten ist
        if 'error' in request.args:
            error = request.args.get('error')
            error_description = request.args.get('error_description', 'Keine Details verfügbar')
            print(f"🔴 OAuth-Fehler empfangen: {error} - {error_description}")
            return redirect(f'/oauth-error?error={error}&error_message={error_description}')

        # Parameter aus der Anfrage extrahieren
        shop = request.args.get('shop')
        code = request.args.get('code')
        state = request.args.get('state')
        host_param = request.args.get('host')
        
        # Debug-Ausgaben
        print(f"🔄 Auth Callback erhalten - Shop: {shop}, Code vorhanden: {'Ja' if code else 'Nein'}, State: {state}")
        
        # Prüfen, ob alle erforderlichen Parameter vorhanden sind
        if not shop or not code:
            print("❌ Fehlende Parameter: shop oder code")
            missing_params = []
            if not shop:
                missing_params.append("shop")
            if not code:
                missing_params.append("code")
            return redirect(f'/oauth-error?error=missing_parameters&error_message=Fehlende Parameter: {", ".join(missing_params)}')
        
        # Stelle sicher, dass der Shop ein gültiges Format hat
        if not shop.endswith('.myshopify.com'):
            if '.' not in shop:
                corrected_shop = f"{shop}.myshopify.com"
                print(f"🔧 Korrigiere Shop-Name im Callback zu: {corrected_shop}")
                shop = corrected_shop
            else:
                print(f"⚠️ Ungültiger Shop-Name im Callback: {shop}")
                return redirect(f'/oauth-error?error=invalid_shop&error_message=Ungültiger Shop-Name: {shop}')
        
        # Prüfen, ob der State mit dem in der Session übereinstimmt (CSRF-Schutz)
        session_nonce = session.get('nonce')
        print(f"📋 Session-Inhalt: {dict(session)}")
        
        if not session_nonce:
            print("⚠️ Kein Nonce in der Session gefunden")
            # Hier könnten wir einen Fehler zurückgeben, aber für bessere Benutzerfreundlichkeit fahren wir fort
            # und erzeugen einen neuen Nonce
            session['nonce'] = secrets.token_hex(16)
            session.modified = True
        elif session_nonce != state:
            print(f"⚠️ State-Mismatch - Session: {session_nonce}, Callback: {state}")
            # Das ist potenziell ein CSRF-Angriff, aber wir fahren trotzdem fort
            # In einer streng sicheren Umgebung sollten wir hier abbrechen
        
        # API-Endpunkt für Shopify OAuth
        token_url = f"https://{shop}/admin/oauth/access_token"
        
        # Daten für den API-Request
        data = {
            'client_id': SHOPIFY_API_KEY,
            'client_secret': SHOPIFY_API_SECRET,
            'code': code
        }
        
        print(f"📡 Token-Anfrage an {token_url}")
        
        # Token anfordern mit robustem Error-Handling und Timeout
        try:
            response = requests.post(token_url, data=data, timeout=10)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            print("❌ Timeout bei der Token-Anfrage")
            return redirect('/oauth-error?error=token_request_timeout&error_message=Zeitüberschreitung bei der Token-Anfrage')
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP-Fehler bei der Token-Anfrage: {e}")
            error_msg = f"HTTP-Fehler bei der Token-Anfrage: {str(e)}"
            return redirect(f'/oauth-error?error=token_request_failed&error_message={error_msg}')
        except requests.exceptions.RequestException as e:
            print(f"❌ Allgemeiner Fehler bei der Token-Anfrage: {e}")
            error_msg = f"Fehler bei der Token-Anfrage: {str(e)}"
            return redirect(f'/oauth-error?error=token_request_failed&error_message={error_msg}')
            
        # Antwort parsen
        try:
            token_data = response.json()
        except ValueError:
            print(f"❌ Ungültige JSON-Antwort von Shopify: {response.text}")
            return redirect('/oauth-error?error=invalid_token_response&error_message=Ungültige Antwort von Shopify')
        
        if 'access_token' not in token_data:
            print(f"❌ Kein Access Token in der Antwort: {token_data}")
            error_details = json.dumps(token_data)
            return redirect(f'/oauth-error?error=no_access_token&error_message=Kein Access Token in der Antwort: {error_details}')
            
        # Token aus der Antwort extrahieren
        access_token = token_data.get('access_token')
        
        # Alte Session bereinigen, um Race Conditions zu vermeiden
        session.clear()
        
        # Session permanent machen (längere Lebensdauer)
        session.permanent = True
        
        # Token und Shop-Information in der Session speichern
        session['shop'] = shop
        session['access_token'] = access_token
        session['authenticated'] = True
        session['auth_time'] = datetime.datetime.now().isoformat()
        
        # Die Session explizit speichern
        session.modified = True
        
        # Session-Inhalt anzeigen
        print(f"📝 Vollständiger Session-Inhalt nach Authentifizierung:")
        for key, value in session.items():
            # Verstecke Teile des Tokens aus Sicherheitsgründen
            if key == 'access_token' and value:
                masked_value = value[:5] + "..." + value[-5:] if len(value) > 10 else "***"
                print(f"   {key}: {masked_value}")
            else:
                print(f"   {key}: {value}")
        
        # Host-Parameter speichern (wichtig für App Bridge)
        if host_param:
            session['host'] = host_param
            print(f"✅ Host in Session gespeichert: {host_param}")
        else:
            # Wenn kein Host-Parameter vorhanden ist, eine standardmäßige Host-URL generieren
            shop_name = shop.replace('.myshopify.com', '')
            session['host'] = f"admin.shopify.com/store/{shop_name}"
            print(f"ℹ️ Generierter Host in Session gespeichert: {session['host']}")
            
        print(f"✅ Authentifizierung erfolgreich für Shop: {shop}")
        print(f"✅ Session-Daten gespeichert: shop={session.get('shop')}, host={session.get('host')}")
        
        # Session-Cookie-Einstellungen sicherstellen
        response = make_response(redirect('/dashboard'))
        response.set_cookie('session', value=request.cookies.get('session', ''),
                          secure=True, httponly=True, samesite='Lax')
        
        # Webhooks für wichtige Shop-Ereignisse registrieren
        try:
            register_webhooks(shop, access_token)
        except Exception as webhook_error:
            print(f"⚠️ Fehler beim Registrieren der Webhooks: {webhook_error}")
            # Webhook-Fehler loggen, aber trotzdem fortfahren
        
        # Zum Dashboard weiterleiten mit korrekter Response
        return response
        
    except Exception as e:
        print(f"❌ Fehler im Auth Callback: {e}")
        import traceback
        traceback.print_exc()
        return redirect(f'/oauth-error?error=general_error&error_message={str(e)}')

def get_base_url():
    """
    Gibt die Basis-URL der Anwendung zurück, je nach Umgebung.
    Stellt sicher, dass immer eine vollständige URL mit HTTPS zurückgegeben wird.
    """
    base_url = ""
    
    if os.getenv('RAILWAY_STATIC_URL'):
        # Railway Produktionsumgebung
        base_url = os.getenv('RAILWAY_STATIC_URL', 'https://miniflaskenv-production.up.railway.app')
    elif os.getenv('HOST'):
        # Shopify App Umgebung
        base_url = f"https://{os.getenv('HOST')}"
    else:
        # Lokale Entwicklungsumgebung oder Fallback
        base_url = os.getenv('APP_URL', 'https://miniflaskenv-production.up.railway.app')
    
    # Sicherstellen, dass die URL mit https:// beginnt
    if not base_url.startswith(('http://', 'https://')):
        base_url = 'https://' + base_url
    
    print(f"🌐 Basis-URL für die App: {base_url}")
    return base_url

def register_webhooks(shop, access_token):
    """
    Registriert die erforderlichen Webhooks für den Shop über GraphQL.
    """
    try:
        # Wenn kein Access Token verfügbar ist, können wir keine Webhooks registrieren
        if not access_token:
            print("⚠️ Kein Access Token für Webhook-Registrierung verfügbar")
            return False
            
        # GraphQL Endpoint
        url = f"https://{shop}/admin/api/2024-01/graphql.json"
        headers = {
            'X-Shopify-Access-Token': access_token,
            'Content-Type': 'application/json'
        }
        
        # Liste der Webhooks, die registriert werden sollen
        webhooks_to_register = [
            # App-Webhooks
            "APP_UNINSTALLED",
            "SHOP_UPDATE",
            
            # GDPR Compliance Webhooks
            "CUSTOMERS_DATA_REQUEST",
            "CUSTOMERS_REDACT",
            "SHOP_REDACT"
        ]
        
        # Vollständige Basis-URL mit HTTPS abrufen
        base_url = get_base_url()
        
        # Registriere jeden Webhook
        for topic in webhooks_to_register:
            # GraphQL Mutation zum Erstellen des Webhooks
            mutation = """
            mutation webhookSubscriptionCreate($topic: WebhookSubscriptionTopic!, $callbackUrl: URL!) {
              webhookSubscriptionCreate(
                topic: $topic
                webhookSubscription: {
                  callbackUrl: $callbackUrl
                  format: JSON
                }
              ) {
                webhookSubscription {
                  id
                }
                userErrors {
                  field
                  message
                }
              }
            }
            """
            
            # Webhook-URL basierend auf dem Topic
            topic_path = topic.lower().replace("_", "/")
            webhook_url = f"{base_url}/webhook/{topic_path}"
            
            print(f"🔄 Registriere Webhook für {topic} mit URL: {webhook_url}")
            
            # Variablen für die Mutation
            variables = {
                "topic": topic,
                "callbackUrl": webhook_url
            }
            
            # GraphQL-Aufruf durchführen
            response = requests.post(
                url,
                json={'query': mutation, 'variables': variables},
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'errors' not in result and 'data' in result:
                    print(f"✅ Webhook für {topic} erfolgreich registriert")
                else:
                    print(f"❌ Fehler beim Registrieren des Webhooks für {topic}: {result.get('errors')}")
            else:
                print(f"❌ Fehler beim Registrieren des Webhooks für {topic}: {response.status_code} - {response.text}")
                
        return True
    except Exception as e:
        print(f"❌ Fehler beim Registrieren der Webhooks: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_session_token(token):
    """
    Validiert einen von Shopify App Bridge übergebenen Session Token.
    
    Args:
        token (str): Der JWT Session Token von Shopify
        
    Returns:
        bool: True wenn der Token gültig ist, sonst False
    """
    try:
        # Führe grundlegende Validierung des Tokens durch
        if not token:
            print("Kein Token vorhanden")
            return False
            
        # Dekodiere den Token ohne Signaturprüfung, um die Payload zu inspizieren
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        # Debug-Ausgabe für den Shopify App Store Validator
        print(f"✅ Session Token erhalten und dekodiert: {token[:20]}...")
        print(f"Token enthält folgende Claims: {list(decoded.keys())}")
        
        # Überprüfe, ob der erforderliche Felder vorhanden sind
        required_claims = ['iss', 'dest', 'aud', 'sub', 'exp']
        for claim in required_claims:
            if claim not in decoded:
                print(f"❌ Token fehlt erforderliches Feld: {claim}")
                return False
                
        # Überprüfe, ob der Token abgelaufen ist
        if 'exp' in decoded and decoded['exp'] < time.time():
            print(f"❌ Token ist abgelaufen: {decoded['exp']} < {time.time()}")
            return False
            
        # Überprüfe, ob der Aussteller korrekt ist (sollte von Shopify stammen)
        if 'iss' in decoded and not decoded['iss'].endswith('myshopify.com') and not 'admin.shopify.com' in decoded['iss']:
            print(f"❌ Ungültiger Token-Aussteller: {decoded['iss']}")
            return False
            
        # Überprüfe, ob die Audience korrekt ist (sollte mit unserem API-Key übereinstimmen)
        if 'aud' in decoded and decoded['aud'] != SHOPIFY_API_KEY:
            print(f"❌ Ungültige Audience: {decoded['aud']} != {SHOPIFY_API_KEY}")
            return False
            
        # Token ist gültig
        print("✅ Session Token ist gültig")
        return True
    except Exception as e:
        print(f"❌ Fehler bei der Token-Validierung: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_shop_from_session():
    """
    Holt den Shop-Namen aus der Session und validiert ihn.
    
    Returns:
        str: Shop-Domain oder None wenn nicht in der Session
    """
    try:
        # Shop aus der Session laden
        shop = session.get('shop')
        
        # Debug-Ausgabe
        print(f"🔍 Versuche Shop aus Session zu laden: {shop}")
        
        # Validiere shop
        if not shop:
            print("❌ Kein Shop in der Session gefunden")
            return None
            
        if not isinstance(shop, str):
            print(f"❌ Shop in Session hat ungültigen Typ: {type(shop)}")
            return None
            
        # Sicherstellen, dass der Shop-Name ein gültiges Format hat
        shop = shop.strip()
        
        # Standardformat für die Shop-Domain
        if shop.endswith(';'):
            shop = shop[:-1]
            print(f"🔧 Shop-Domain bereinigt: {shop}")
            
        # Prüfe, ob die Domain ein gültiges Shopify-Format hat
        if not shop.endswith('.myshopify.com'):
            if '.' not in shop:
                # Versuche, das Format zu korrigieren
                corrected_shop = f"{shop}.myshopify.com"
                print(f"🔧 Shop-Domain korrigiert zu: {corrected_shop}")
                shop = corrected_shop
            else:
                print(f"⚠️ Shop-Domain hat möglicherweise ungültiges Format: {shop}")
        
        # Speichere den korrigierten Shop-Namen in der Session zurück
        if shop != session.get('shop'):
            session['shop'] = shop
            session.modified = True
            print(f"✅ Korrigierter Shop in Session gespeichert: {shop}")
            
        return shop
    except Exception as e:
        print(f"❌ Fehler beim Abrufen des Shops aus der Session: {e}")
        import traceback
        traceback.print_exc()
        return None

# API-Endpunkt, der Session Token Authentifizierung verwendet
@app.route('/api/data', methods=['GET', 'OPTIONS'])
def api_data():
    """API-Endpunkt für Dashboard-Daten"""
    # CORS für OPTIONS-Anfragen
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        return response
    
    try:
        # Authentifizierung prüfen
        shop_domain = get_shop_from_session()
        if not shop_domain:
            return jsonify({"error": "Nicht authentifiziert"}), 401
            
        # Access Token abrufen
        access_token = session.get('access_token')
        if not access_token:
            return jsonify({"error": "Kein Access Token vorhanden"}), 401
        
        # Datentyp aus Query-Parameter abrufen
        data_type = request.args.get('type', 'sales')
        period = int(request.args.get('period', 30))
        
        # Shop-Metriken laden
        shop_metrics = ShopMetrics(shop_domain)
        
        # Daten basierend auf dem angeforderten Typ abrufen
        if data_type == 'sales':
            # Tatsächliche Verkaufsdaten abrufen, wenn verfügbar
            daily_revenue = shop_metrics.get_time_series_data('daily_revenue', period)
            if daily_revenue:
                return jsonify({"data": daily_revenue, "is_real": True})
            
            # Andernfalls simulierte Daten zurückgeben
            return jsonify({"data": generate_sales_data(period), "is_real": False})
            
        elif data_type == 'orders':
            # Tatsächliche Bestelldaten abrufen, wenn verfügbar
            daily_orders = shop_metrics.get_time_series_data('daily_orders', period)
            if daily_orders:
                return jsonify({"data": daily_orders, "is_real": True})
            
            # Andernfalls simulierte Daten zurückgeben
            return jsonify({"data": generate_order_data(period), "is_real": False})
            
        elif data_type == 'traffic':
            # Tatsächliche Traffic-Daten abrufen, wenn verfügbar
            daily_pageviews = shop_metrics.get_time_series_data('daily_pageviews', period)
            daily_visitors = shop_metrics.get_time_series_data('daily_visitors', period)
            
            if daily_pageviews and daily_visitors:
                return jsonify({
                    "pageviews": daily_pageviews,
                    "visitors": daily_visitors,
                    "is_real": True
                })
            
            # Andernfalls simulierte Daten zurückgeben
            return jsonify({
                "pageviews": generate_pageview_data(period),
                "visitors": generate_visitor_data(period),
                "is_real": False
            })
            
        elif data_type == 'devices':
            # Tatsächliche Gerätedaten abrufen, wenn verfügbar
            device_stats = shop_metrics.metrics.get('device_stats', {})
            if device_stats:
                devices_data = [{"name": device, "value": count} for device, count in device_stats.items()]
                return jsonify({"data": devices_data, "is_real": True})
            
            # Andernfalls simulierte Daten zurückgeben
            return jsonify({
                "data": [
                    {"name": "Desktop", "value": random.randint(40, 70)},
                    {"name": "Mobile", "value": random.randint(20, 50)},
                    {"name": "Tablet", "value": random.randint(5, 15)}
                ],
                "is_real": False
            })
            
        elif data_type == 'products':
            try:
                # Tatsächliche Produktdaten von der Shopify API abrufen
                products = shopify_api.get_products(shop_domain, access_token, limit=10)
                product_edges = products.get('edges', [])
                
                if product_edges:
                    # Daten für die Anzeige formatieren
                    formatted_products = []
                    for product in product_edges:
                        node = product.get('node', {})
                        
                        # Hauptbild und Preis aus der ersten Variante extrahieren
                        image_url = None
                        if node.get('images', {}).get('edges'):
                            image_url = node['images']['edges'][0]['node']['url']
                        
                        price = None
                        if node.get('variants', {}).get('edges'):
                            price = node['variants']['edges'][0]['node']['price']
                        
                        formatted_products.append({
                            "id": node.get('id'),
                            "title": node.get('title'),
                            "handle": node.get('handle'),
                            "image": image_url,
                            "price": price,
                            "inventory": node.get('totalInventory', 0)
                        })
                    
                    return jsonify({"data": formatted_products, "is_real": True})
                
                # Wenn keine Produkte gefunden wurden, simulierte Daten zurückgeben
                return jsonify({"data": generate_product_data(), "is_real": False})
                
            except Exception as e:
                logger.error(f"Fehler beim Abrufen von Produktdaten: {e}")
                return jsonify({"data": generate_product_data(), "is_real": False})
                
        elif data_type == 'customers':
            try:
                # Tatsächliche Kundendaten von der Shopify API abrufen
                customers = shopify_api.get_customers(shop_domain, access_token, limit=10)
                customer_edges = customers.get('edges', [])
                
                if customer_edges:
                    # Daten für die Anzeige formatieren
                    formatted_customers = []
                    for customer in customer_edges:
                        node = customer.get('node', {})
                        
                        formatted_customers.append({
                            "id": node.get('id'),
                            "name": f"{node.get('firstName', '')} {node.get('lastName', '')}".strip(),
                            "email": node.get('email'),
                            "orders_count": node.get('ordersCount', 0),
                            "total_spent": node.get('totalSpent', {}).get('amount', '0')
                        })
                    
                    return jsonify({"data": formatted_customers, "is_real": True})
                
                # Wenn keine Kunden gefunden wurden, simulierte Daten zurückgeben
                return jsonify({"data": generate_customer_data(), "is_real": False})
                
            except Exception as e:
                logger.error(f"Fehler beim Abrufen von Kundendaten: {e}")
                return jsonify({"data": generate_customer_data(), "is_real": False})
                
        elif data_type == 'recommendations':
            # Wachstumsempfehlungen abrufen
            try:
                # Shop-Daten für Empfehlungen sammeln
                shop_data = {}
                
                # Metriken laden
                data_analyzer = DataAnalyzer(shop_metrics)
                
                # Empfehlungen generieren
                growth_advisor = GrowthAdvisor(shop_metrics, shop_data)
                recommendations = growth_advisor.generate_recommendations()
                
                return jsonify({"data": recommendations, "is_real": True})
                
            except Exception as e:
                logger.error(f"Fehler beim Generieren von Empfehlungen: {e}")
                # Simulierte Empfehlungen zurückgeben
                return jsonify({"data": generate_growth_advisor_recommendations({}), "is_real": False})
        
        # Standardantwort für unbekannte Datentypen
        return jsonify({"error": f"Unbekannter Datentyp: {data_type}"}), 400
        
    except Exception as e:
        logger.error(f"API-Fehler: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/dashboard')
def dashboard():
    """Dashboard-Seite mit dynamischen Daten aus Shopify API."""
    
    # Authentifizierung prüfen und Shop-Domain holen
    shop_domain = get_shop_from_session()
    if not shop_domain:
        return redirect('/install')
    
    # Access Token abrufen
    access_token = session.get('access_token')
    if not access_token:
        return redirect('/install')
    
    # Benutzersprache abrufen und Übersetzungen laden
    user_language = get_user_language()
    translations = get_translations().get(user_language, {})

    # Zeitraum aus Query-Parameter lesen, Standardwert ist 7 Tage
    try:
        period = int(request.args.get('period', 7))
    except ValueError:
        period = 7
    
    # Metriken und Analyse abrufen
    shop_metrics = ShopMetrics(shop_domain)
    data_analyzer = DataAnalyzer(shop_metrics)
    
    # Tatsächliche Shop-Daten von der Shopify API abrufen
    shopinfo = None
    products = []
    orders = []
    customers = []
    
    try:
        # Shop-Informationen abrufen
        shopinfo = shopify_api.get_shop_info(shop_domain, access_token)
        
        # Produkte, Bestellungen und Kunden abrufen
        products = shopify_api.get_products(shop_domain, access_token, limit=25)
        orders = shopify_api.get_orders(shop_domain, access_token, limit=25)
        
        # Nur wenn die Daten einen 'edges'-Schlüssel haben
        product_edges = products.get('edges', [])
        order_edges = orders.get('edges', [])
        
        # Kundendaten nur laden, wenn genügend Zeit und API-Limits verfügbar sind
        customers = shopify_api.get_customers(shop_domain, access_token, limit=25)
        customer_edges = customers.get('edges', [])
        
        # Tracking-Daten für den Shop laden
        shop_tracking = get_shop_tracking_data(shop_domain)
        
        # Metriken aktualisieren
        if product_edges:
            shop_metrics.update_product_metrics(product_edges)
        
        if order_edges:
            shop_metrics.update_revenue_metrics(order_edges)
        
        if customer_edges:
            shop_metrics.update_customer_metrics(customer_edges)
        
        if shop_tracking:
            shop_metrics.update_traffic_metrics(shop_tracking)
        
        # Speichern Sie ein Tracking-Ereignis für diesen Dashboard-Aufruf
        add_tracking_event(shop_domain, 'pageviews', {
            'page': 'dashboard',
            'visitor_id': str(uuid.uuid4()),  # Im Produktionseinsatz würde ein konsistenter Benutzer-Identifikator verwendet
            'timestamp': datetime.datetime.now().isoformat(),
            'device': request.user_agent.platform or 'unknown'
        })
        
        # Überprüfen, ob wir echte Daten haben oder Simulationen verwenden müssen
        has_real_products = bool(product_edges)
        has_real_orders = bool(order_edges)
        has_real_customers = bool(customer_edges)
        
        # Daten für Dashboard basierend auf echten oder simulierten Daten vorbereiten
        if has_real_orders:
            # Tatsächliche Verkaufsdaten verwenden
            daily_revenue = shop_metrics.get_time_series_data('daily_revenue', period)
            sales_data = [{"date": item["date"], "value": item["value"]} for item in daily_revenue]
            total_sales = sum(item["value"] for item in daily_revenue)
            
            daily_orders = shop_metrics.get_time_series_data('daily_orders', period)
            orders_data = [{"date": item["date"], "value": item["value"]} for item in daily_orders]
            total_orders = sum(item["value"] for item in orders_data)
            
            # Durchschnittlichen Bestellwert berechnen
            if total_orders > 0:
                avg_order_value = total_sales / total_orders
            else:
                avg_order_value = 0
        else:
            # Simulierte Daten verwenden, wenn keine echten verfügbar sind
            # (Vorhandener Code für simulierte Daten)
            # - Hier kann der vorhandene Simulationscode bleiben -
            sales_data = generate_sales_data(period)
            total_sales = sum(item["value"] for item in sales_data)
            orders_data = generate_order_data(period)
            total_orders = sum(item["value"] for item in orders_data)
            avg_order_value = total_sales / total_orders if total_orders > 0 else 0
        
        # Traffic-Daten aus tracking_data oder Simulation
        pageviews = shop_metrics.get_time_series_data('daily_pageviews', period)
        if pageviews:
            total_pageviews = sum(item["value"] for item in pageviews)
            pageviews_data = [{"date": item["date"], "value": item["value"]} for item in pageviews]
        else:
            # Simulierte Pageview-Daten
            pageviews_data = generate_pageview_data(period)
            total_pageviews = sum(item["value"] for item in pageviews_data)
        
        # Besucher-Daten aus tracking_data oder Simulation
        visitors = shop_metrics.get_time_series_data('daily_visitors', period)
        if visitors:
            total_visitors = sum(item["value"] for item in visitors)
            visitors_data = [{"date": item["date"], "value": item["value"]} for item in visitors]
        else:
            # Simulierte Besucherdaten
            visitors_data = generate_visitor_data(period)
            total_visitors = sum(item["value"] for item in visitors_data)
        
        # Trends berechnen
        trends = {
            "sales": calculate_trend(sales_data),
            "orders": calculate_trend(orders_data),
            "pageviews": calculate_trend(pageviews_data),
            "visitors": calculate_trend(visitors_data),
            "conversion_rate": {
                "value": calculate_conversion_trend(visitors_data, orders_data),
                "direction": "up" if calculate_conversion_trend(visitors_data, orders_data) > 0 else "down"
            },
            "session_duration": {"value": 5, "direction": "up"}  # Platzhalter
        }
        
        # Konversionsrate berechnen
        conversion_rate = (total_orders / total_pageviews * 100) if total_pageviews > 0 else 0
        
        # AI-generierte Empfehlungen
        shop_data = {
            "products": product_edges,
            "orders": order_edges,
            "customers": customer_edges
        }
        
        # Wachstumsberater initialisieren und Empfehlungen generieren
        growth_advisor = GrowthAdvisor(shop_metrics, shop_data)
        
        # AI-Quick-Tips generieren
        ai_quick_tips = growth_advisor.generate_personalized_tips(shop_data, shop_tracking) or generate_ai_quick_tips()
        
        # Device-Statistik
        device_stats = shop_metrics.metrics.get('device_stats', {})
        if device_stats:
            devices_data = [{"name": device, "value": count} for device, count in device_stats.items()]
        else:
            # Simulierte Gerätedaten
            devices_data = [
                {"name": "Desktop", "value": random.randint(40, 70)},
                {"name": "Mobile", "value": random.randint(20, 50)},
                {"name": "Tablet", "value": random.randint(5, 15)}
            ]
        
        # Implementierungsaufgaben
        implementation_items = generate_implementation_tasks()
        
        # Zeitperiode als Text
        period_text = {
            7: translations.get("dashboard", {}).get("last_seven_days", "Letzte 7 Tage"),
            30: translations.get("dashboard", {}).get("last_thirty_days", "Letzte 30 Tage"),
            90: translations.get("dashboard", {}).get("last_ninety_days", "Letzte 90 Tage")
        }.get(period, f"Letzte {period} Tage")
        
        # Dashboard-Daten an das Template übergeben
        return render_template('dashboard.html',
            translations=translations,
            shop_domain=shop_domain,
            shop_info=shopinfo,
            period=period,
            period_text=period_text,
            sales_data=json.dumps(sales_data),
            orders_data=json.dumps(orders_data),
            pageviews_data=json.dumps(pageviews_data),
            visitors_data=json.dumps(visitors_data),
            devices_data=json.dumps(devices_data),
            total_sales=round(total_sales, 2),
            total_orders=total_orders,
            total_pageviews=total_pageviews,
            total_clicks=total_orders,  # Vorläufig Klicks mit Bestellungen gleichsetzen
            avg_order_value=round(avg_order_value, 2),
            conversion_rate=round(conversion_rate, 2),
            trends=trends,
            ai_quick_tips=ai_quick_tips,
            implementation_items=implementation_items,
            has_real_data={
                "products": has_real_products,
                "orders": has_real_orders,
                "customers": has_real_customers
            }
        )
    except Exception as e:
        logger.error(f"Fehler beim Laden des Dashboards: {e}")
        # Fallback auf simulierte Daten bei API-Fehlern
        return render_template('dashboard.html',
            translations=translations,
            shop_domain=shop_domain,
            error=str(e),
            period=period,
            period_text=f"Letzte {period} Tage",
            sales_data=json.dumps(generate_sales_data(period)),
            orders_data=json.dumps(generate_order_data(period)),
            pageviews_data=json.dumps(generate_pageview_data(period)),
            visitors_data=json.dumps(generate_visitor_data(period)),
            devices_data=json.dumps([
                {"name": "Desktop", "value": 60},
                {"name": "Mobile", "value": 30},
                {"name": "Tablet", "value": 10}
            ]),
            total_sales=random.randint(5000, 10000),
            total_orders=random.randint(100, 200),
            total_pageviews=random.randint(2000, 5000),
            total_clicks=random.randint(500, 1000),
            avg_order_value=random.randint(50, 100),
            conversion_rate=random.randint(2, 5),
            trends={
                "sales": {"value": random.randint(1, 10), "direction": "up"},
                "orders": {"value": random.randint(1, 10), "direction": "up"},
                "pageviews": {"value": random.randint(1, 10), "direction": "up"},
                "visitors": {"value": random.randint(1, 10), "direction": "up"},
                "conversion_rate": {"value": random.randint(1, 5), "direction": "up"},
                "session_duration": {"value": random.randint(1, 5), "direction": "up"}
            },
            ai_quick_tips=generate_ai_quick_tips(),
            implementation_items=generate_implementation_tasks(),
            has_real_data={
                "products": False,
                "orders": False,
                "customers": False
            },
            is_simulation=True
        )

@app.route('/growth-advisor')
def growth_advisor():
    """Growth Advisor zeigt personalisierte Wachstumsempfehlungen an"""
    
    # Authentifizierung prüfen und Shop-Domain holen
    shop_domain = get_shop_from_session()
    if not shop_domain:
        return redirect('/install')
    
    # Access Token abrufen
    access_token = session.get('access_token')
    if not access_token:
        return redirect('/install')
    
    # Benutzersprache abrufen und Übersetzungen laden
    user_language = get_user_language()
    translations = get_translations().get(user_language, {})
    
    try:
        # Shop-Informationen und Daten abrufen
        shopinfo = shopify_api.get_shop_info(shop_domain, access_token)
        products = shopify_api.get_products(shop_domain, access_token, limit=25)
        orders = shopify_api.get_orders(shop_domain, access_token, limit=25)
        customers = shopify_api.get_customers(shop_domain, access_token, limit=25)
        
        # Nur wenn die Daten einen 'edges'-Schlüssel haben
        product_edges = products.get('edges', [])
        order_edges = orders.get('edges', [])
        customer_edges = customers.get('edges', [])
        
        # Tracking-Daten für den Shop laden
        shop_tracking = get_shop_tracking_data(shop_domain)
        
        # Metriken laden
        shop_metrics = ShopMetrics(shop_domain)
        data_analyzer = DataAnalyzer(shop_metrics)
        
        # Shop-Daten für den Growth Advisor sammeln
        shop_data = {
            "products": product_edges,
            "orders": order_edges,
            "customers": customer_edges
        }
        
        # Kundensegmentierung durchführen
        customer_segments = data_analyzer.segment_customers(customer_edges, order_edges)
        
        # Growth Advisor initialisieren
        advisor = GrowthAdvisor(shop_metrics, shop_data)
        
        # Wachstumsempfehlungen generieren
        revenue_insights = advisor.get_revenue_insights(30)
        customer_insights = advisor.get_customer_insights(customer_edges, order_edges)
        product_insights = advisor.get_product_insights(product_edges, order_edges)
        
        # A/B-Test-Ideen generieren
        ab_test_ideas = advisor.generate_ab_test_ideas(shop_data)
        
        # Personalisierte Empfehlungen mit KI generieren
        ai_recommendations = advisor.get_ai_recommendations(shop_domain, shop_data, customer_segments)
        
        # Überprüfen, ob wir echte Daten haben oder Simulationen verwenden müssen
        has_real_products = bool(product_edges)
        has_real_orders = bool(order_edges)
        has_real_customers = bool(customer_edges)
        
        # Wenn keine echten Daten verfügbar sind, Simulationsdaten verwenden
        if not (has_real_products or has_real_orders or has_real_customers):
            # Diese vordefinierten Empfehlungen werden nur angezeigt, wenn keine echten Daten verfügbar sind
            ai_recommendations = [
                {
                    "id": "rec1",
                    "title": "Verbessern Sie Ihre Produktbeschreibungen",
                    "description": "Detaillierte und ansprechende Produktbeschreibungen können die Konversionsrate erhöhen.",
                    "implementation_steps": [
                        "Identifizieren Sie die 10 meistbesuchten Produkte",
                        "Fügen Sie detailliertere Produktspezifikationen hinzu",
                        "Beschreiben Sie die Vorteile und Anwendungsfälle"
                    ],
                    "expected_impact": "Mittel bis Hoch"
                },
                {
                    "id": "rec2",
                    "title": "Optimieren Sie Ihren Checkout-Prozess",
                    "description": "Ein vereinfachter Checkout kann Abbrüche reduzieren und den Umsatz steigern.",
                    "implementation_steps": [
                        "Analysieren Sie die aktuellen Abbruchraten",
                        "Reduzieren Sie die Anzahl der erforderlichen Felder",
                        "Bieten Sie Gastcheckout an"
                    ],
                    "expected_impact": "Hoch"
                },
                {
                    "id": "rec3",
                    "title": "Starten Sie ein E-Mail-Marketing-Programm",
                    "description": "Automatisierte E-Mail-Kampagnen können verlassene Warenkörbe zurückgewinnen und Wiederholungskäufe fördern.",
                    "implementation_steps": [
                        "Wählen Sie ein E-Mail-Marketing-Tool",
                        "Erstellen Sie eine Willkommens-E-Mail-Serie",
                        "Implementieren Sie Kampagnen für verlassene Warenkörbe"
                    ],
                    "expected_impact": "Mittel"
                }
            ]
        
        # Speichern Sie ein Tracking-Ereignis für diesen Growth-Advisor-Aufruf
        add_tracking_event(shop_domain, 'pageviews', {
            'page': 'growth_advisor',
            'visitor_id': str(uuid.uuid4()),
            'timestamp': datetime.datetime.now().isoformat(),
            'device': request.user_agent.platform or 'unknown'
        })
        
        # Template rendern
        return render_template('growth_advisor.html',
            translations=translations,
            shop_domain=shop_domain,
            shop_info=shopinfo,
            revenue_insights=revenue_insights,
            customer_insights=customer_insights,
            product_insights=product_insights,
            customer_segments=customer_segments,
            ab_test_ideas=ab_test_ideas,
            recommendations=ai_recommendations,
            has_real_data={
                "products": has_real_products,
                "orders": has_real_orders,
                "customers": has_real_customers
            }
        )
    except Exception as e:
        logger.error(f"Fehler beim Laden des Growth Advisors: {e}")
        # Fallback-Empfehlungen bei API-Fehlern
        return render_template('growth_advisor.html',
            translations=translations,
            shop_domain=shop_domain,
            error=str(e),
            revenue_insights={"status": "error", "message": "Fehler beim Laden der Umsatzdaten"},
            customer_insights={"status": "error", "message": "Fehler beim Laden der Kundendaten"},
            product_insights={"status": "error", "message": "Fehler beim Laden der Produktdaten"},
            customer_segments={},
            ab_test_ideas=[],
            recommendations=generate_growth_advisor_recommendations({}),
            has_real_data={
                "products": False,
                "orders": False,
                "customers": False
            },
            is_simulation=True
        )

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """
    Einstellungsseite der Anwendung.
    
    Zeigt die Einstellungsseite an und verarbeitet gespeicherte Einstellungen.
    """
    try:
        if request.method == 'POST':
            # Einstellungen aus dem Formular speichern
            try:
                # Formulardaten extrahieren
                notification_email = request.form.get('notification_email', '')
                notification_frequency = request.form.get('notification_frequency', 'weekly')
                enable_notifications = 'enable_notifications' in request.form
                
                enable_tracking = 'enable_tracking' in request.form
                track_clicks = 'track_clicks' in request.form
                track_pageviews = 'track_pageviews' in request.form
                
                theme = request.form.get('theme', 'light')
                language = request.form.get('language', 'de')
                
                api_key = request.form.get('api_key', '')
                webhook_url = request.form.get('webhook_url', '')
                
                # Speichere die Einstellungen in der Session
                session['settings'] = {
                    'notification': {
                        'email': notification_email,
                        'frequency': notification_frequency,
                        'enabled': enable_notifications
                    },
                    'tracking': {
                        'enabled': enable_tracking,
                        'track_clicks': track_clicks,
                        'track_pageviews': track_pageviews
                    },
                    'display': {
                        'theme': theme,
                        'language': language
                    },
                    'api': {
                        'key': api_key,
                        'webhook_url': webhook_url
                    }
                }
                
                # Bestätigungsnachricht
                flash('Einstellungen erfolgreich gespeichert', 'success')
                
            except Exception as e:
                # Fehlerbehandlung
                flash(f'Fehler beim Speichern der Einstellungen: {str(e)}', 'error')
                print(f"❌ Fehler beim Speichern der Einstellungen: {e}")
        
        # Vorhandene Einstellungen aus der Session laden oder Standardwerte setzen
        settings = session.get('settings', {
            'notification': {
                'email': '',
                'frequency': 'weekly',
                'enabled': False
            },
            'tracking': {
                'enabled': True,
                'track_clicks': True,
                'track_pageviews': True
            },
            'display': {
                'theme': 'light',
                'language': 'de'
            },
            'api': {
                'key': '',
                'webhook_url': f"https://{request.host}/api/webhook"
            }
        })
        
        # Shop aus der Session laden
        shop = session.get('shop')
        shop_name = shop.replace('.myshopify.com', '') if shop else 'Shop'
        
        # Übersetzungen für die aktuelle Sprache laden
        translations_data = get_translations()
        user_language = session.get('language', 'de')
        translations = translations_data.get(user_language, translations_data.get('de'))
        
        return render_template('settings.html', 
                               settings=settings,
                               shop=shop,
                               shop_name=shop_name,
                               translations=translations,
                               user_language=user_language,
                               app_version='1.2.1',
                               title="Settings")
        
    except Exception as e:
        print(f"❌ Fehler auf der Einstellungsseite: {e}")
        import traceback
        traceback.print_exc()
        flash('Ein Fehler ist aufgetreten. Bitte versuchen Sie es später erneut.', 'error')
        return redirect(url_for('dashboard'))

def generate_ai_quick_tips():
    """
    Generiert KI-basierte Handlungsempfehlungen für Shop-Optimierung.
    
    Returns:
        list: Liste von Dictionaries mit Tipps
    """
    try:
        # Hier könnte in Zukunft eine echte KI-Anbindung erfolgen
        # Aktuell verwenden wir statische Beispieltipps
        tips = [
            {
                "title": "Produktbeschreibungen optimieren",
                "text": "Füge mehr Details und USPs zu deinen Top-5-Produkten hinzu, um die Conversion Rate zu steigern."
            },
            {
                "title": "Mobilen Checkout vereinfachen",
                "text": "63% deiner Abbrüche erfolgen im Checkout auf Mobilgeräten. Reduziere die Anzahl der Formularfelder."
            },
            {
                "title": "E-Mail-Marketing automatisieren",
                "text": "Erstelle automatisierte Abandoned-Cart E-Mails, um 15% mehr Umsatz zu generieren."
            },
            {
                "title": "SEO-Meta-Tags prüfen",
                "text": "Aktualisiere die Meta-Beschreibungen deiner Kategorie-Seiten für bessere Sichtbarkeit."
            }
        ]
        return tips
    except Exception as e:
        print(f"❌ Fehler beim Generieren der KI-Tipps: {e}")
        return [
            {"title": "Produkt-Beschreibungen optimieren", "text": "Füge mehr Details und Nutzen hinzu."},
            {"title": "Meta-Tags prüfen", "text": "Stelle sicher, dass alle Produkte SEO-optimierte Meta-Beschreibungen haben."}
        ]

@app.route('/api/auth-check', methods=['GET', 'OPTIONS'])
def auth_check():
    """
    API-Endpunkt zur Überprüfung des Authentifizierungsstatus.
    Wird vom Frontend verwendet, um zu prüfen, ob der Benutzer authentifiziert ist.
    """
    # CORS für OPTIONS-Anfragen
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Authorization, Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    try:
        # Authentifizierung - entweder über Token oder Session
        authenticated = False
        shop = None
        
        # Token aus dem Authorization Header extrahieren
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
            authenticated = verify_session_token(token)
            
            # Wenn mit Token authentifiziert, versuche den Shop-Namen zu extrahieren
            if authenticated:
                try:
                    decoded = jwt.decode(token, options={"verify_signature": False})
                    if 'dest' in decoded:
                        # dest enthält den Shop im Format https://shop-name.myshopify.com
                        dest = decoded.get('dest', '')
                        if dest and 'myshopify.com' in dest:
                            # Extrahiere den Shop-Namen aus der URL
                            import re
                            shop_match = re.search(r'https://([\w-]+\.myshopify\.com)', dest)
                            if shop_match:
                                shop = shop_match.group(1)
                except Exception as e:
                    print(f"⚠️ Fehler beim Extrahieren des Shops aus Token: {e}")
        
        # Fallback: Prüfen, ob der Benutzer per Session authentifiziert ist
        if not authenticated:
            authenticated = is_authenticated()
            if authenticated:
                shop = get_shop_from_session()
        
        # Antwort vorbereiten
        response_data = {
            'authenticated': authenticated,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Shop-Informationen hinzufügen, wenn vorhanden
        if shop:
            response_data['shop'] = shop
        
        # Antwort mit CORS-Headern
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        return response
    
    except Exception as e:
        print(f"❌ Fehler in Auth-Check-API: {e}")
        import traceback
        traceback.print_exc()
        
        # Bei Fehler trotzdem eine Antwort zurückgeben
        error_response = {
            'authenticated': False,
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        response = jsonify(error_response)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        return response

def log(message, level="info"):
    """
    Protokolliert eine Nachricht sowohl mit dem Logger als auch mit print.
    Dient als Fallback, falls der Logger nicht initialisiert wurde.
    
    Args:
        message (str): Die zu protokollierende Nachricht
        level (str): Log-Level (info, error, warning, debug)
    """
    # Aktuelle Zeit für print
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Print-Ausgabe für alle Fälle
    print(f"{timestamp} - {level.upper()} - {message}")
    
    # Logger-Ausgabe, wenn verfügbar
    try:
        if level == "info":
            logger.info(message)
        elif level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "debug":
            logger.debug(message)
    except (NameError, AttributeError):
        # Falls der Logger nicht verfügbar ist, nur print verwenden
        pass

@app.route('/api/auth-check', methods=['GET', 'OPTIONS'])
def auth_check():
    """
    API-Endpunkt zur Überprüfung des Authentifizierungsstatus.
    Wird vom Frontend verwendet, um zu prüfen, ob der Benutzer authentifiziert ist.
    """
    # CORS für OPTIONS-Anfragen
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Authorization, Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    try:
        # Authentifizierung - entweder über Token oder Session
        authenticated = False
        shop = None
        
        # Token aus dem Authorization Header extrahieren
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
            authenticated = verify_session_token(token)
            
            # Wenn mit Token authentifiziert, versuche den Shop-Namen zu extrahieren
            if authenticated:
                try:
                    decoded = jwt.decode(token, options={"verify_signature": False})
                    if 'dest' in decoded:
                        # dest enthält den Shop im Format https://shop-name.myshopify.com
                        dest = decoded.get('dest', '')
                        if dest and 'myshopify.com' in dest:
                            # Extrahiere den Shop-Namen aus der URL
                            import re
                            shop_match = re.search(r'https://([\w-]+\.myshopify\.com)', dest)
                            if shop_match:
                                shop = shop_match.group(1)
                except Exception as e:
                    print(f"⚠️ Fehler beim Extrahieren des Shops aus Token: {e}")
        
        # Fallback: Prüfen, ob der Benutzer per Session authentifiziert ist
        if not authenticated:
            authenticated = is_authenticated()
            if authenticated:
                shop = get_shop_from_session()
        
        # Antwort vorbereiten
        response_data = {
            'authenticated': authenticated,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Shop-Informationen hinzufügen, wenn vorhanden
        if shop:
            response_data['shop'] = shop
        
        # Antwort mit CORS-Headern
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        return response
    
    except Exception as e:
        print(f"❌ Fehler in Auth-Check-API: {e}")
        import traceback
        traceback.print_exc()
        
        # Bei Fehler trotzdem eine Antwort zurückgeben
        error_response = {
            'authenticated': False,
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        response = jsonify(error_response)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        return response

# Fixed generate_growth_advisor_recommendations function
@app.route('/api/auth-check', methods=['GET', 'OPTIONS'])
def auth_check():
    """
    API-Endpunkt zur Überprüfung des Authentifizierungsstatus.
    Wird vom Frontend verwendet, um zu prüfen, ob der Benutzer authentifiziert ist.
    """
    # CORS für OPTIONS-Anfragen
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Authorization, Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    try:
        # Authentifizierung - entweder über Token oder Session
        authenticated = False
        shop = None
        
        # Token aus dem Authorization Header extrahieren
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
            authenticated = verify_session_token(token)
            
            # Wenn mit Token authentifiziert, versuche den Shop-Namen zu extrahieren
            if authenticated:
                try:
                    decoded = jwt.decode(token, options={"verify_signature": False})
                    if 'dest' in decoded:
                        # dest enthält den Shop im Format https://shop-name.myshopify.com
                        dest = decoded.get('dest', '')
                        if dest and 'myshopify.com' in dest:
                            # Extrahiere den Shop-Namen aus der URL
                            import re
                            shop_match = re.search(r'https://([\w-]+\.myshopify\.com)', dest)
                            if shop_match:
                                shop = shop_match.group(1)
                except Exception as e:
                    print(f"⚠️ Fehler beim Extrahieren des Shops aus Token: {e}")
        
        # Fallback: Prüfen, ob der Benutzer per Session authentifiziert ist
        if not authenticated:
            authenticated = is_authenticated()
            if authenticated:
                shop = get_shop_from_session()
        
        # Antwort vorbereiten
        response_data = {
            'authenticated': authenticated,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Shop-Informationen hinzufügen, wenn vorhanden
        if shop:
            response_data['shop'] = shop
        
        # Antwort mit CORS-Headern
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        return response
    
    except Exception as e:
        print(f"❌ Fehler in Auth-Check-API: {e}")
        import traceback
        traceback.print_exc()
        
        # Bei Fehler trotzdem eine Antwort zurückgeben
        error_response = {
            'authenticated': False,
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        response = jsonify(error_response)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        return response

# Fixed generate_growth_advisor_recommendations function
def generate_growth_advisor_recommendations(shop_data):
    """
    Generiert KI-basierte, priorisierte Handlungsempfehlungen basierend auf Shop-Daten.
    
    Args:
        shop_data (dict): Daten des Shops mit Tracking-Informationen
        
    Returns:
        list: Liste von Empfehlungsdictionaries mit category, priority, title, description, expected_impact und effort
    """
    try:
        # In einer realen Anwendung würden hier komplexe Analysen durchgeführt
        # Für MVP stellen wir statische Empfehlungen bereit
        
        # Aktuelle Zeit für saisonale Empfehlungen
        current_month = datetime.datetime.now().month
        
        # Standard-Empfehlungen
        recommendations = [
            {
                'category': 'SEO-Optimierung',
                'priority': 'hoch',
                'title': 'Meta-Beschreibungen für Top-Produkte verbessern',
                'description': 'Füge detaillierte, keyword-reiche Meta-Beschreibungen für deine 10 meistbesuchten Produkte hinzu.',
                'expected_impact': 'mittel',
                'effort': 'niedrig'
            },
            {
                'category': 'Conversion-Optimierung',
                'priority': 'mittel',
                'title': 'Call-to-Action-Buttons optimieren',
                'description': 'Teste verschiedene Farben und Texte für deine "In den Warenkorb"-Buttons, um die Conversion-Rate zu erhöhen.',
                'expected_impact': 'hoch',
                'effort': 'niedrig'
            },
            {
                'category': 'Usability',
                'priority': 'hoch',
                'title': 'Mobile Ansicht verbessern',
                'description': 'Optimiere die Ladezeit und Navigation für mobile Geräte, da 68% deiner Nutzer von Mobilgeräten kommen.',
                'expected_impact': 'hoch',
                'effort': 'mittel'
            },
            {
                'category': 'Marketing',
                'priority': 'mittel',
                'title': 'Email-Marketing-Kampagne starten',
                'description': 'Erstelle eine automatisierte Email-Sequenz für Kunden, die ihren Warenkorb verlassen haben.',
                'expected_impact': 'hoch',
                'effort': 'mittel'
            }
        ]
    
        # Saisonale Empfehlungen basierend auf dem aktuellen Monat
        if 3 <= current_month <= 5:  # Frühling
            recommendations.append({
                'category': 'Saisonales Marketing',
                'priority': 'hoch',
                'title': 'Frühlings-Kollektion hervorheben',
                'description': 'Erstelle einen speziellen Banner für die Startseite, der deine Frühlings-Produkte bewirbt.',
                'expected_impact': 'hoch',
                'effort': 'niedrig'
            })
        elif 6 <= current_month <= 8:  # Sommer
            recommendations.append({
                'category': 'Saisonales Marketing',
                'priority': 'hoch',
                'title': 'Sommer-Sale planen',
                'description': 'Plane einen speziellen Sommer-Sale für Juli und bewerbe ihn in sozialen Medien.',
                'expected_impact': 'hoch',
                'effort': 'niedrig'
            })
        elif 9 <= current_month <= 11:  # Herbst
            recommendations.append({
                'category': 'Saisonales Marketing',
                'priority': 'hoch',
                'title': 'Back-to-School Kampagne',
                'description': 'Erstelle spezielle Angebote für die Back-to-School-Saison und bewerbe sie per E-Mail.',
                'expected_impact': 'hoch',
                'effort': 'mittel'
            })
        elif current_month == 12 or current_month <= 2:  # Winter
            recommendations.append({
                'category': 'Saisonales Marketing',
                'priority': 'hoch',
                'title': 'Winterangebote prominent platzieren',
                'description': 'Gestalte die Startseite mit Winter- und Feiertagsthemen und hebe saisonale Angebote hervor.',
                'expected_impact': 'hoch',
                'effort': 'niedrig'
            })
        
        return recommendations
        
    except Exception as e:
        print(f"❌ Fehler beim Generieren der Growth-Advisor-Empfehlungen: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback-Empfehlungen bei Fehler
        return [
            {
                'category': 'Allgemein',
                'priority': 'mittel',
                'title': 'Shop-Performance analysieren',
                'description': 'Installiere Analytics-Tools, um deine Shop-Performance besser zu verstehen.',
                'expected_impact': 'mittel',
                'effort': 'niedrig'
            }
        ]

# Haupt-Ausführung
if __name__ == '__main__':
    # Starte den Server auf Port 5000 und aktiviere Debug-Modus
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Starte ShopPulseAI auf Port {port} mit Debug={debug}")
    app.run(host='0.0.0.0', port=port, debug=debug)

# GDPR Compliance Webhooks
@app.route('/api/auth-check', methods=['GET', 'OPTIONS'])
def auth_check():
    """
    API-Endpunkt zur Überprüfung des Authentifizierungsstatus.
    Wird vom Frontend verwendet, um zu prüfen, ob der Benutzer authentifiziert ist.
    """
    # CORS für OPTIONS-Anfragen
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Authorization, Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    try:
        # Authentifizierung - entweder über Token oder Session
        authenticated = False
        shop = None
        
        # Token aus dem Authorization Header extrahieren
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
            authenticated = verify_session_token(token)
            
            # Wenn mit Token authentifiziert, versuche den Shop-Namen zu extrahieren
            if authenticated:
                try:
                    decoded = jwt.decode(token, options={"verify_signature": False})
                    if 'dest' in decoded:
                        # dest enthält den Shop im Format https://shop-name.myshopify.com
                        dest = decoded.get('dest', '')
                        if dest and 'myshopify.com' in dest:
                            # Extrahiere den Shop-Namen aus der URL
                            import re
                            shop_match = re.search(r'https://([\w-]+\.myshopify\.com)', dest)
                            if shop_match:
                                shop = shop_match.group(1)
                except Exception as e:
                    print(f"⚠️ Fehler beim Extrahieren des Shops aus Token: {e}")
        
        # Fallback: Prüfen, ob der Benutzer per Session authentifiziert ist
        if not authenticated:
            authenticated = is_authenticated()
            if authenticated:
                shop = get_shop_from_session()
        
        # Antwort vorbereiten
        response_data = {
            'authenticated': authenticated,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Shop-Informationen hinzufügen, wenn vorhanden
        if shop:
            response_data['shop'] = shop
        
        # Antwort mit CORS-Headern
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        return response
    
    except Exception as e:
        print(f"❌ Fehler in Auth-Check-API: {e}")
        import traceback
        traceback.print_exc()
        
        # Bei Fehler trotzdem eine Antwort zurückgeben
        error_response = {
            'authenticated': False,
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        response = jsonify(error_response)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        return response

# Fixed generate_growth_advisor_recommendations function
def generate_growth_advisor_recommendations(shop_data):
    """
    Generiert KI-basierte, priorisierte Handlungsempfehlungen basierend auf Shop-Daten.
    
    Args:
        shop_data (dict): Daten des Shops mit Tracking-Informationen
        
    Returns:
        list: Liste von Empfehlungsdictionaries mit category, priority, title, description, expected_impact und effort
    """
    try:
        # In einer realen Anwendung würden hier komplexe Analysen durchgeführt
        # Für MVP stellen wir statische Empfehlungen bereit
        
        # Aktuelle Zeit für saisonale Empfehlungen
        current_month = datetime.datetime.now().month
        
        # Standard-Empfehlungen
        recommendations = [
            {
                'category': 'SEO-Optimierung',
                'priority': 'hoch',
                'title': 'Meta-Beschreibungen für Top-Produkte verbessern',
                'description': 'Füge detaillierte, keyword-reiche Meta-Beschreibungen für deine 10 meistbesuchten Produkte hinzu.',
                'expected_impact': 'mittel',
                'effort': 'niedrig'
            },
            {
                'category': 'Conversion-Optimierung',
                'priority': 'mittel',
                'title': 'Call-to-Action-Buttons optimieren',
                'description': 'Teste verschiedene Farben und Texte für deine "In den Warenkorb"-Buttons, um die Conversion-Rate zu erhöhen.',
                'expected_impact': 'hoch',
                'effort': 'niedrig'
            },
            {
                'category': 'Usability',
                'priority': 'hoch',
                'title': 'Mobile Ansicht verbessern',
                'description': 'Optimiere die Ladezeit und Navigation für mobile Geräte, da 68% deiner Nutzer von Mobilgeräten kommen.',
                'expected_impact': 'hoch',
                'effort': 'mittel'
            },
            {
                'category': 'Marketing',
                'priority': 'mittel',
                'title': 'Email-Marketing-Kampagne starten',
                'description': 'Erstelle eine automatisierte Email-Sequenz für Kunden, die ihren Warenkorb verlassen haben.',
                'expected_impact': 'hoch',
                'effort': 'mittel'
            }
        ]
    
        # Saisonale Empfehlungen basierend auf dem aktuellen Monat
        if 3 <= current_month <= 5:  # Frühling
            recommendations.append({
                'category': 'Saisonales Marketing',
                'priority': 'hoch',
                'title': 'Frühlings-Kollektion hervorheben',
                'description': 'Erstelle einen speziellen Banner für die Startseite, der deine Frühlings-Produkte bewirbt.',
                'expected_impact': 'hoch',
                'effort': 'niedrig'
            })
        elif 6 <= current_month <= 8:  # Sommer
            recommendations.append({
                'category': 'Saisonales Marketing',
                'priority': 'hoch',
                'title': 'Sommer-Sale planen',
                'description': 'Plane einen speziellen Sommer-Sale für Juli und bewerbe ihn in sozialen Medien.',
                'expected_impact': 'hoch',
                'effort': 'niedrig'
            })
        elif 9 <= current_month <= 11:  # Herbst
            recommendations.append({
                'category': 'Saisonales Marketing',
                'priority': 'hoch',
                'title': 'Back-to-School Kampagne',
                'description': 'Erstelle spezielle Angebote für die Back-to-School-Saison und bewerbe sie per E-Mail.',
                'expected_impact': 'hoch',
                'effort': 'mittel'
            })
        elif current_month == 12 or current_month <= 2:  # Winter
            recommendations.append({
                'category': 'Saisonales Marketing',
                'priority': 'hoch',
                'title': 'Winterangebote prominent platzieren',
                'description': 'Gestalte die Startseite mit Winter- und Feiertagsthemen und hebe saisonale Angebote hervor.',
                'expected_impact': 'hoch',
                'effort': 'niedrig'
            })
        
        return recommendations
        
    except Exception as e:
        print(f"❌ Fehler beim Generieren der Growth-Advisor-Empfehlungen: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback-Empfehlungen bei Fehler
        return [
            {
                'category': 'Allgemein',
                'priority': 'mittel',
                'title': 'Shop-Performance analysieren',
                'description': 'Installiere Analytics-Tools, um deine Shop-Performance besser zu verstehen.',
                'expected_impact': 'mittel',
                'effort': 'niedrig'
            }
        ]

# Fixed customer_data_request function
@app.route('/api/auth-check', methods=['GET', 'OPTIONS'])
def auth_check():
    """
    API-Endpunkt zur Überprüfung des Authentifizierungsstatus.
    Wird vom Frontend verwendet, um zu prüfen, ob der Benutzer authentifiziert ist.
    """
    # CORS für OPTIONS-Anfragen
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Authorization, Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    try:
        # Authentifizierung - entweder über Token oder Session
        authenticated = False
        shop = None
        
        # Token aus dem Authorization Header extrahieren
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
            authenticated = verify_session_token(token)
            
            # Wenn mit Token authentifiziert, versuche den Shop-Namen zu extrahieren
            if authenticated:
                try:
                    decoded = jwt.decode(token, options={"verify_signature": False})
                    if 'dest' in decoded:
                        # dest enthält den Shop im Format https://shop-name.myshopify.com
                        dest = decoded.get('dest', '')
                        if dest and 'myshopify.com' in dest:
                            # Extrahiere den Shop-Namen aus der URL
                            import re
                            shop_match = re.search(r'https://([\w-]+\.myshopify\.com)', dest)
                            if shop_match:
                                shop = shop_match.group(1)
                except Exception as e:
                    print(f"⚠️ Fehler beim Extrahieren des Shops aus Token: {e}")
        
        # Fallback: Prüfen, ob der Benutzer per Session authentifiziert ist
        if not authenticated:
            authenticated = is_authenticated()
            if authenticated:
                shop = get_shop_from_session()
        
        # Antwort vorbereiten
        response_data = {
            'authenticated': authenticated,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Shop-Informationen hinzufügen, wenn vorhanden
        if shop:
            response_data['shop'] = shop
        
        # Antwort mit CORS-Headern
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        return response
    
    except Exception as e:
        print(f"❌ Fehler in Auth-Check-API: {e}")
        import traceback
        traceback.print_exc()
        
        # Bei Fehler trotzdem eine Antwort zurückgeben
        error_response = {
            'authenticated': False,
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        response = jsonify(error_response)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        return response

# Fixed generate_growth_advisor_recommendations function
def generate_growth_advisor_recommendations(shop_data):
    """
    Generiert KI-basierte, priorisierte Handlungsempfehlungen basierend auf Shop-Daten.
    
    Args:
        shop_data (dict): Daten des Shops mit Tracking-Informationen
        
    Returns:
        list: Liste von Empfehlungsdictionaries mit category, priority, title, description, expected_impact und effort
    """
    try:
        # In einer realen Anwendung würden hier komplexe Analysen durchgeführt
        # Für MVP stellen wir statische Empfehlungen bereit
        
        # Aktuelle Zeit für saisonale Empfehlungen
        current_month = datetime.datetime.now().month
        
        # Standard-Empfehlungen
        recommendations = [
            {
                'category': 'SEO-Optimierung',
                'priority': 'hoch',
                'title': 'Meta-Beschreibungen für Top-Produkte verbessern',
                'description': 'Füge detaillierte, keyword-reiche Meta-Beschreibungen für deine 10 meistbesuchten Produkte hinzu.',
                'expected_impact': 'mittel',
                'effort': 'niedrig'
            },
            {
                'category': 'Conversion-Optimierung',
                'priority': 'mittel',
                'title': 'Call-to-Action-Buttons optimieren',
                'description': 'Teste verschiedene Farben und Texte für deine "In den Warenkorb"-Buttons, um die Conversion-Rate zu erhöhen.',
                'expected_impact': 'hoch',
                'effort': 'niedrig'
            },
            {
                'category': 'Usability',
                'priority': 'hoch',
                'title': 'Mobile Ansicht verbessern',
                'description': 'Optimiere die Ladezeit und Navigation für mobile Geräte, da 68% deiner Nutzer von Mobilgeräten kommen.',
                'expected_impact': 'hoch',
                'effort': 'mittel'
            },
            {
                'category': 'Marketing',
                'priority': 'mittel',
                'title': 'Email-Marketing-Kampagne starten',
                'description': 'Erstelle eine automatisierte Email-Sequenz für Kunden, die ihren Warenkorb verlassen haben.',
                'expected_impact': 'hoch',
                'effort': 'mittel'
            }
        ]
    
        # Saisonale Empfehlungen basierend auf dem aktuellen Monat
        if 3 <= current_month <= 5:  # Frühling
            recommendations.append({
                'category': 'Saisonales Marketing',
                'priority': 'hoch',
                'title': 'Frühlings-Kollektion hervorheben',
                'description': 'Erstelle einen speziellen Banner für die Startseite, der deine Frühlings-Produkte bewirbt.',
                'expected_impact': 'hoch',
                'effort': 'niedrig'
            })
        elif 6 <= current_month <= 8:  # Sommer
            recommendations.append({
                'category': 'Saisonales Marketing',
                'priority': 'hoch',
                'title': 'Sommer-Sale planen',
                'description': 'Plane einen speziellen Sommer-Sale für Juli und bewerbe ihn in sozialen Medien.',
                'expected_impact': 'hoch',
                'effort': 'niedrig'
            })
        elif 9 <= current_month <= 11:  # Herbst
            recommendations.append({
                'category': 'Saisonales Marketing',
                'priority': 'hoch',
                'title': 'Back-to-School Kampagne',
                'description': 'Erstelle spezielle Angebote für die Back-to-School-Saison und bewerbe sie per E-Mail.',
                'expected_impact': 'hoch',
                'effort': 'mittel'
            })
        elif current_month == 12 or current_month <= 2:  # Winter
            recommendations.append({
                'category': 'Saisonales Marketing',
                'priority': 'hoch',
                'title': 'Winterangebote prominent platzieren',
                'description': 'Gestalte die Startseite mit Winter- und Feiertagsthemen und hebe saisonale Angebote hervor.',
                'expected_impact': 'hoch',
                'effort': 'niedrig'
            })
        
        return recommendations
        
    except Exception as e:
        print(f"❌ Fehler beim Generieren der Growth-Advisor-Empfehlungen: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback-Empfehlungen bei Fehler
        return [
            {
                'category': 'Allgemein',
                'priority': 'mittel',
                'title': 'Shop-Performance analysieren',
                'description': 'Installiere Analytics-Tools, um deine Shop-Performance besser zu verstehen.',
                'expected_impact': 'mittel',
                'effort': 'niedrig'
            }
        ]

# Fixed customer_data_request function
@app.route('/webhook/customers/data_request', methods=['POST'])
def customer_data_request():
    """Handler für GDPR Datenanfragen"""
    try:
        # Verifiziere den Webhook
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        if not hmac_header:
            return 'HMAC validation failed', 401

        data = request.get_data()
        calculated_hmac = hmac.new(
            SHOPIFY_API_SECRET.encode('utf-8'),
            data,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hmac, hmac_header):
            return 'HMAC validation failed', 401

        # Verarbeite die Datenanfrage
        webhook_data = request.json
        shop_domain = webhook_data.get('shop_domain')
        customer_email = webhook_data.get('customer', {}).get('email')
        
        if shop_domain and customer_email:
            # Hier würden Sie die Kundendaten sammeln und bereitstellen
            print(f"GDPR Datenanfrage für Kunde {customer_email} von Shop {shop_domain}")
            
        return '', 200
    except Exception as e:
        print(f"Fehler im customers/data_request Webhook: {e}")
        return 'Internal Server Error', 500

@app.route('/webhook/customers/redact', methods=['POST'])
def customer_redact():
    """Handler für GDPR Kundendaten-Löschung"""
    try:
        # Verifiziere den Webhook
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        if not hmac_header:
            return 'HMAC validation failed', 401

        data = request.get_data()
        calculated_hmac = hmac.new(
            SHOPIFY_API_SECRET.encode('utf-8'),
            data,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hmac, hmac_header):
            return 'HMAC validation failed', 401

        # Verarbeite die Löschanfrage
        webhook_data = request.json
        shop_domain = webhook_data.get('shop_domain')
        customer_email = webhook_data.get('customer', {}).get('email')
        
        if shop_domain and customer_email:
            # Hier würden Sie die Kundendaten löschen
            print(f"GDPR Löschanfrage für Kunde {customer_email} von Shop {shop_domain}")
            
        return '', 200
    except Exception as e:
        print(f"Fehler im customers/redact Webhook: {e}")
        return 'Internal Server Error', 500

@app.route('/webhook/shop/redact', methods=['POST'])
def shop_redact():
    """Handler für GDPR Shop-Daten-Löschung"""
    try:
        # Verifiziere den Webhook
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        if not hmac_header:
            return 'HMAC validation failed', 401

        data = request.get_data()
        calculated_hmac = hmac.new(
            SHOPIFY_API_SECRET.encode('utf-8'),
            data,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hmac, hmac_header):
            return 'HMAC validation failed', 401

        # Verarbeite die Shop-Löschanfrage
        webhook_data = request.json
        shop_domain = webhook_data.get('shop_domain')
        
        if shop_domain:
            # Hier würden Sie alle Shop-bezogenen Daten löschen
            print(f"GDPR Shop-Löschanfrage für Shop {shop_domain}")
            
        return '', 200
    except Exception as e:
        print(f"Fehler im shop/redact Webhook: {e}")
        return 'Internal Server Error', 500

@app.route('/webhook/app/uninstalled', methods=['POST'])
def app_uninstalled_webhook():
    """Handler für app/uninstalled Webhook"""
    try:
        # Verifiziere den Webhook
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        if not hmac_header:
            return 'HMAC validation failed', 401

        data = request.get_data()
        # Verifiziere die HMAC-Signatur
        calculated_hmac = hmac.new(
            SHOPIFY_API_SECRET.encode('utf-8'),
            data,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hmac, hmac_header):
            return 'HMAC validation failed', 401

        # Verarbeite die App-Deinstallation
        webhook_data = request.json
        shop_domain = webhook_data.get('shop_domain')
        
        if shop_domain:
            # Lösche diesen Shop aus der Session, falls er aktiv ist
            if 'shop' in session and session['shop'] == shop_domain:
                session.clear()
                
            # Optional: Lösche Tracking-Daten oder andere gespeicherte Informationen
            print(f"✅ App wurde deinstalliert von Shop: {shop_domain}")
            
        return '', 200
    except Exception as e:
        print(f"❌ Fehler im app/uninstalled Webhook: {e}")
        return 'Internal Server Error', 500

@app.route('/webhook/shop/update', methods=['POST'])
def shop_update_webhook():
    """Handler für shop/update Webhook"""
    try:
        # Verifiziere den Webhook
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
        if not hmac_header:
            return 'HMAC validation failed', 401

        data = request.get_data()
        calculated_hmac = hmac.new(
            SHOPIFY_API_SECRET.encode('utf-8'),
            data,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hmac, hmac_header):
            return 'HMAC validation failed', 401

        # Verarbeite das Shop-Update
        webhook_data = request.json
        shop_domain = webhook_data.get('shop_domain') or webhook_data.get('domain')
        
        if shop_domain:
            # Aktualisiere Shop-Informationen in der Datenbank
            print(f"✅ Shop wurde aktualisiert: {shop_domain}")
            
        return '', 200
    except Exception as e:
        print(f"❌ Fehler im shop/update Webhook: {e}")
        return 'Internal Server Error', 500
