#!/usr/bin/env python3

# This script creates a new version of app.py with fixed syntax

# 1. Create backup
import shutil
import sys
import subprocess

# Create backup
shutil.copy('app.py', 'app.py.backup')
print("Created backup as app.py.backup")

# 2. Create fixed functions
with open('fixed_auth_check.py', 'w') as f:
    f.write('''@app.route('/api/auth-check', methods=['GET', 'OPTIONS'])
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
        return response''')

with open('fixed_growth_advisor.py', 'w') as f:
    f.write('''def generate_growth_advisor_recommendations(shop_data):
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
        ]''')

with open('fixed_customer_data_request.py', 'w') as f:
    f.write('''@app.route('/webhook/customers/data_request', methods=['POST'])
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
            
        return '', 200''')

# 3. Create a new app.py
print("Creating fixed app.py")
with open('app.py.fixed', 'w') as new_file:
    with open('app.py.backup', 'r') as old_file:
        content = old_file.read()
        
        # Replace the functions
        with open('fixed_auth_check.py', 'r') as f:
            auth_check_function = f.read()
        
        with open('fixed_growth_advisor.py', 'r') as f:
            growth_advisor_function = f.read()
            
        with open('fixed_customer_data_request.py', 'r') as f:
            customer_data_request_function = f.read()
        
        # Replace the problematic auth_check function
        auth_check_start = content.find('@app.route(\'/api/auth-check\'')
        auth_check_end = content.find('def log(message, level="info"):', auth_check_start)
        if auth_check_start >= 0 and auth_check_end >= 0:
            content = content[:auth_check_start] + auth_check_function + '\n\n' + content[auth_check_end:]
        
        # Replace the problematic generate_growth_advisor_recommendations function
        growth_advisor_start = content.find('def generate_growth_advisor_recommendations(shop_data):')
        growth_advisor_end = content.find('# Haupt-Ausführung', growth_advisor_start)
        if growth_advisor_start >= 0 and growth_advisor_end >= 0:
            content = content[:growth_advisor_start] + growth_advisor_function + '\n\n' + content[growth_advisor_end:]
        
        # Replace the problematic customer_data_request function
        customer_data_start = content.find('@app.route(\'/webhook/customers/data_request\'')
        customer_data_end = content.find('@app.route(\'/webhook/customers/redact\'', customer_data_start)
        if customer_data_start >= 0 and customer_data_end >= 0:
            content = content[:customer_data_start] + customer_data_request_function + '\n\n' + content[customer_data_end:]
        
        new_file.write(content)

# 4. Test the compilation of the new file
print("Testing compilation of fixed app.py")
result = subprocess.run(['python3', '-m', 'py_compile', 'app.py.fixed'], capture_output=True)

if result.returncode == 0:
    print("✅ Fixed app.py compiles successfully!")
    # Rename fixed file to app.py
    shutil.move('app.py.fixed', 'app.py')
    print("✅ Renamed app.py.fixed to app.py")
    print("Original file is backed up as app.py.backup")
else:
    print("❌ Fixed app.py still has syntax errors:")
    print(result.stderr.decode())
    print("Please check app.py.fixed manually or restore from backup: cp app.py.backup app.py")
    sys.exit(1)

# Cleanup temp files
import os
try:
    os.remove('fixed_auth_check.py')
    os.remove('fixed_growth_advisor.py')
    os.remove('fixed_customer_data_request.py')
    print("✅ Cleaned up temporary files")
except:
    pass 