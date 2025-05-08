#!/usr/bin/env python3

import re
import subprocess
import sys

def main():
    print("Creating backup of app.py")
    subprocess.run(["cp", "app.py", "app.py.backup"])
    
    # Read the original file
    with open("app.py", "r") as f:
        content = f.read()
    
    # Fix auth_check function
    print("Fixing auth_check function...")
    auth_fix = """@app.route('/api/auth-check', methods=['GET', 'OPTIONS'])
def auth_check():
    \"\"\"
    API-Endpunkt zur Überprüfung des Authentifizierungsstatus.
    Wird vom Frontend verwendet, um zu prüfen, ob der Benutzer authentifiziert ist.
    \"\"\"
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
        return response"""
    
    # Replace auth_check function
    auth_pattern = r"@app\.route\('/api/auth-check'.*?return response"
    content = re.sub(auth_pattern, auth_fix, content, flags=re.DOTALL)
    
    # Fix generate_growth_advisor_recommendations function
    print("Fixing generate_growth_advisor_recommendations function...")
    growth_fix = """def generate_growth_advisor_recommendations(shop_data):
    \"\"\"
    Generiert KI-basierte, priorisierte Handlungsempfehlungen basierend auf Shop-Daten.
    
    Args:
        shop_data (dict): Daten des Shops mit Tracking-Informationen
        
    Returns:
        list: Liste von Empfehlungsdictionaries mit category, priority, title, description, expected_impact und effort
    \"\"\"
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
        ]"""
    
    # Replace generate_growth_advisor_recommendations function
    growth_pattern = r"def generate_growth_advisor_recommendations\(shop_data\):.*?return \["
    content = re.sub(growth_pattern, growth_fix, content, flags=re.DOTALL)
    
    # Fix customer_data_request function
    print("Fixing customer_data_request function...")
    customer_fix = """@app.route('/webhook/customers/data_request', methods=['POST'])
def customer_data_request():
    \"\"\"Handler für GDPR Datenanfragen\"\"\"
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
            
        return '', 200"""
    
    # Replace customer_data_request function
    customer_pattern = r"@app\.route\('/webhook/customers/data_request'.*?shop {shop_domain}\"\)"
    content = re.sub(customer_pattern, customer_fix, content, flags=re.DOTALL)
    
    # Write fixed content back to app.py
    print("Writing fixed content to app.py")
    with open("app.py", "w") as f:
        f.write(content)
    
    # Verify the file compiles
    print("Verifying that the fixed file compiles correctly")
    result = subprocess.run(["python3", "-m", "py_compile", "app.py"], capture_output=True)
    
    if result.returncode == 0:
        print("✅ Syntax fixes were successful! The file compiles correctly.")
        return 0
    else:
        print("❌ There are still syntax errors in the file:")
        print(result.stderr.decode())
        print("Please restore from backup with: cp app.py.backup app.py")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 