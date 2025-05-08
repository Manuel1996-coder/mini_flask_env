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
import random
import numpy as np
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

# Environment-Variablen laden
load_dotenv()

# Flask App konfigurieren
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

# Shopify API Keys aus der .env Datei
SHOPIFY_API_KEY = os.environ.get('SHOPIFY_API_KEY', 'bc64e63be55d4cbad777bc2b89d1307c')
SHOPIFY_API_SECRET = os.environ.get('SHOPIFY_API_SECRET', 'a04bb1e1c1cd5b9d8881d6c9c19f4c6c')
APP_URL = os.environ.get('APP_URL', 'https://miniflaskenv-production.up.railway.app')

# Geheimer Schlüssel für Session-Verschlüsselung
app.secret_key = os.environ.get('SECRET_KEY', 'sehr_sicherer_schlüssel_2023')

# Fixed auth_check function
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

if __name__ == '__main__':
    # Starte den Server auf Port 5000 und aktiviere Debug-Modus
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Starte ShopPulseAI auf Port {port} mit Debug={debug}")
    app.run(host='0.0.0.0', port=port, debug=debug) 