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