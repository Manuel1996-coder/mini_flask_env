import logging
import json
import random
import numpy as np
from sklearn.cluster import KMeans
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Logger einrichten
logger = logging.getLogger('growth_advisor')

# Environment-Variablen laden
load_dotenv()

# OpenAI API-Schlüssel verwenden, falls verfügbar
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

class GrowthAdvisor:
    """Klasse für intelligente Wachstumsempfehlungen"""
    
    def __init__(self, shop_metrics, shop_data=None):
        self.shop_metrics = shop_metrics
        self.shop_data = shop_data or {}
        
    def get_revenue_insights(self, days=30):
        """Analysiert Umsatzentwicklungen und gibt Einsichten zurück"""
        try:
            revenue_data = self.shop_metrics.get_time_series_data('daily_revenue', days)
            if not revenue_data or len(revenue_data) < 7:
                return {
                    "status": "insufficient_data",
                    "message": "Nicht genügend Umsatzdaten für aussagekräftige Erkenntnisse."
                }
                
            # Umsatz in den letzten 7 Tagen
            last_week = revenue_data[-7:]
            last_week_total = sum(day['value'] for day in last_week)
            
            # Umsatz in der vorletzten Woche
            prev_week = revenue_data[-14:-7] if len(revenue_data) >= 14 else []
            prev_week_total = sum(day['value'] for day in prev_week) if prev_week else 0
            
            # Berechne Wachstumsrate
            growth_rate = 0
            if prev_week_total > 0:
                growth_rate = ((last_week_total - prev_week_total) / prev_week_total) * 100
            
            # Finde Tag mit höchstem Umsatz
            best_day = max(revenue_data, key=lambda x: x['value']) if revenue_data else None
            
            # Umsatztrend erkennen
            trend = "neutral"
            if len(revenue_data) >= 14:
                first_half = sum(day['value'] for day in revenue_data[:(len(revenue_data)//2)])
                second_half = sum(day['value'] for day in revenue_data[(len(revenue_data)//2):])
                
                if second_half > first_half * 1.1:  # 10% Anstieg
                    trend = "rising"
                elif second_half < first_half * 0.9:  # 10% Abfall
                    trend = "falling"
            
            return {
                "status": "success",
                "growth_rate": round(growth_rate, 2),
                "trend": trend,
                "best_day": best_day,
                "last_week_total": round(last_week_total, 2),
                "prev_week_total": round(prev_week_total, 2)
            }
            
        except Exception as e:
            logger.error(f"Fehler bei der Analyse der Umsatzentwicklung: {e}")
            return {
                "status": "error",
                "message": f"Fehler bei der Analyse: {str(e)}"
            }
            
    def get_customer_insights(self, customers, orders):
        """Analysiert Kundendaten und gibt Einsichten zurück"""
        try:
            if not customers or len(customers) == 0:
                return {
                    "status": "insufficient_data",
                    "message": "Keine Kundendaten für Analyse verfügbar."
                }
                
            # RFM-Segmentierung
            # (Diese Implementierung ist vereinfacht - in der Praxis würde man
            # mehr komplexe Metriken und Segmentierungen verwenden)
            
            # Einfache Analyse der Kundenherkunft
            countries = {}
            for customer in customers:
                address = customer.get('node', {}).get('defaultAddress', {})
                if address:
                    country = address.get('country')
                    if country:
                        countries[country] = countries.get(country, 0) + 1
                        
            # Häufigste Länder
            top_countries = sorted(countries.items(), key=lambda x: x[1], reverse=True)[:3]
            
            # Kundenwert-Berechnung
            customers_with_orders = [c for c in customers if c.get('node', {}).get('ordersCount', 0) > 0]
            avg_orders = sum(c.get('node', {}).get('ordersCount', 0) for c in customers) / len(customers) if customers else 0
            
            return {
                "status": "success",
                "total_customers": len(customers),
                "customers_with_orders": len(customers_with_orders),
                "avg_orders_per_customer": round(avg_orders, 2),
                "top_countries": top_countries
            }
            
        except Exception as e:
            logger.error(f"Fehler bei der Analyse der Kundendaten: {e}")
            return {
                "status": "error",
                "message": f"Fehler bei der Analyse: {str(e)}"
            }
    
    def get_product_insights(self, products, orders):
        """Analysiert Produktdaten und gibt Einsichten zurück"""
        try:
            if not products or len(products) == 0:
                return {
                    "status": "insufficient_data",
                    "message": "Keine Produktdaten für Analyse verfügbar."
                }
                
            # Produkttypen zählen
            product_types = {}
            inventory_levels = []
            price_ranges = {}
            
            for product in products:
                prod_data = product.get('node', {})
                product_type = prod_data.get('productType', 'Andere')
                
                # Produkttypen zählen
                product_types[product_type] = product_types.get(product_type, 0) + 1
                
                # Bestandsebenen erfassen
                inventory = prod_data.get('totalInventory', 0)
                if inventory is not None:
                    inventory_levels.append(inventory)
                
                # Preisbereiche erfassen
                variants = prod_data.get('variants', {}).get('edges', [])
                for variant in variants:
                    price = float(variant.get('node', {}).get('price', 0))
                    if price > 0:
                        price_range = self._get_price_range(price)
                        price_ranges[price_range] = price_ranges.get(price_range, 0) + 1
            
            # Top-Produkttypen
            top_product_types = sorted(product_types.items(), key=lambda x: x[1], reverse=True)[:3]
            
            # Bestandsanalyse
            low_inventory_count = sum(1 for inv in inventory_levels if inv < 5)
            
            return {
                "status": "success",
                "total_products": len(products),
                "top_product_types": top_product_types,
                "low_inventory_count": low_inventory_count,
                "price_ranges": price_ranges
            }
            
        except Exception as e:
            logger.error(f"Fehler bei der Analyse der Produktdaten: {e}")
            return {
                "status": "error",
                "message": f"Fehler bei der Analyse: {str(e)}"
            }
    
    def _get_price_range(self, price):
        """Ordnet einen Preis einem Preisbereich zu"""
        if price < 10:
            return "< 10€"
        elif price < 25:
            return "10-25€"
        elif price < 50:
            return "25-50€"
        elif price < 100:
            return "50-100€"
        elif price < 250:
            return "100-250€"
        else:
            return "> 250€"
    
    def _cluster_customers(self, customers, n_clusters=3):
        """Clustert Kunden basierend auf ihren Eigenschaften mit K-Means"""
        try:
            if not customers or len(customers) < n_clusters:
                return []
                
            # Einfache Feature-Extraktion (in einer realen Anwendung wären mehr Features besser)
            features = []
            for customer in customers:
                c_data = customer.get('node', {})
                orders_count = c_data.get('ordersCount', 0)
                total_spent = float(c_data.get('totalSpent', {}).get('amount', 0))
                
                features.append([orders_count, total_spent])
            
            # Normalisierung der Features (wichtig für K-Means)
            features = np.array(features)
            if features.shape[0] == 0:
                return []
                
            # Normalisierung, wenn es Varianz in den Daten gibt
            for i in range(features.shape[1]):
                if features[:, i].std() > 0:
                    features[:, i] = (features[:, i] - features[:, i].mean()) / features[:, i].std()
            
            # K-Means Clustering
            kmeans = KMeans(n_clusters=min(n_clusters, len(features)), random_state=42)
            cluster_labels = kmeans.fit_predict(features)
            
            # Cluster-Zentren für Interpretation
            cluster_centers = kmeans.cluster_centers_
            
            # Interpretation der Cluster
            cluster_interpretations = []
            for i in range(len(cluster_centers)):
                orders_value = cluster_centers[i][0]
                spent_value = cluster_centers[i][1]
                
                interpretation = "Unbekannt"
                if orders_value > 0.5 and spent_value > 0.5:
                    interpretation = "Hochwertige Kunden"
                elif orders_value > 0.5 and spent_value <= 0.5:
                    interpretation = "Häufige Käufer mit niedrigem Wert"
                elif orders_value <= 0.5 and spent_value > 0.5:
                    interpretation = "Seltene Käufer mit hohem Wert"
                else:
                    interpretation = "Gelegenheitskäufer"
                
                cluster_interpretations.append({
                    "id": i,
                    "interpretation": interpretation,
                    "size": sum(1 for label in cluster_labels if label == i)
                })
            
            return cluster_interpretations
            
        except Exception as e:
            logger.error(f"Fehler beim Clustering der Kunden: {e}")
            return []
    
    def generate_ab_test_ideas(self, shop_data):
        """Generiert Ideen für A/B-Tests basierend auf Shop-Daten"""
        try:
            # In einer echten Implementierung würde dies auf einer tieferen Analyse 
            # der Shop-Daten basieren
            
            # Standard-Test-Ideen
            standard_ideas = [
                {
                    "title": "Produktseiten-Layout optimieren",
                    "description": "Testen Sie verschiedene Anordnungen von Produktbildern, Beschreibungen und Kaufbuttons, um die Konversionsrate zu verbessern.",
                    "expected_impact": "medium",
                    "implementation_effort": "medium"
                },
                {
                    "title": "Checkout-Prozess vereinfachen",
                    "description": "Vergleichen Sie den aktuellen Checkout mit einer vereinfachten Version mit weniger Schritten.",
                    "expected_impact": "high",
                    "implementation_effort": "high"
                },
                {
                    "title": "Preisdarstellung ändern",
                    "description": "Testen Sie verschiedene Preisdarstellungen (z.B. '€99' vs. '99€' oder mit/ohne Rabatte).",
                    "expected_impact": "medium",
                    "implementation_effort": "low"
                },
                {
                    "title": "Produktempfehlungen verbessern",
                    "description": "Vergleichen Sie verschiedene Algorithmen für Produktempfehlungen auf Ihrer Seite.",
                    "expected_impact": "medium",
                    "implementation_effort": "medium"
                },
                {
                    "title": "Call-to-Action-Buttons optimieren",
                    "description": "Testen Sie verschiedene Farben, Größen und Texte für Ihre Kaufbuttons.",
                    "expected_impact": "medium",
                    "implementation_effort": "low"
                }
            ]
            
            # Je nach Shop-Daten spezifische Tests vorschlagen
            shop_specific_ideas = []
            
            # Beispiel: Wenn der Shop viele Produkte hat, Filteroptionen testen
            product_count = len(shop_data.get('products', []))
            if product_count > 20:
                shop_specific_ideas.append({
                    "title": "Verbesserte Filteroptionen",
                    "description": f"Mit {product_count} Produkten könnte ein verbessertes Filtersystem die Nutzererfahrung verbessern. Testen Sie verschiedene Filterdesigns.",
                    "expected_impact": "high",
                    "implementation_effort": "medium"
                })
            
            # Beispiel: Bei vielen internationalen Kunden, Sprachoptionen testen
            countries = self.shop_metrics.metrics.get('customer_countries', {})
            if len(countries) > 1:
                shop_specific_ideas.append({
                    "title": "Mehrsprachige Shop-Oberfläche",
                    "description": "Ihre Kunden kommen aus verschiedenen Ländern. Testen Sie, ob eine mehrsprachige Oberfläche die Konversionsrate verbessert.",
                    "expected_impact": "high",
                    "implementation_effort": "high"
                })
            
            # Kombinieren und eine Teilmenge zurückgeben
            all_ideas = standard_ideas + shop_specific_ideas
            selected_ideas = random.sample(all_ideas, min(3, len(all_ideas)))
            
            return selected_ideas
            
        except Exception as e:
            logger.error(f"Fehler bei der Generierung von A/B-Test-Ideen: {e}")
            return []
    
    def generate_recommendations(self):
        """Generiert umfassende Wachstumsempfehlungen basierend auf allen verfügbaren Daten"""
        try:
            # Dummy-Implementierung - in einer echten Anwendung würde dies aus tatsächlichen
            # Datenanalysen generiert werden
            
            # Basisempfehlungen
            recommendations = [
                {
                    "id": "rec1",
                    "category": "marketing",
                    "title": "E-Mail-Marketing verstärken",
                    "description": "Implementieren Sie eine automatisierte E-Mail-Kampagne für Warenkorbabbrecher",
                    "expected_impact": "medium",
                    "implementation_effort": "medium",
                    "source": "system"
                },
                {
                    "id": "rec2",
                    "category": "product",
                    "title": "Produktbeschreibungen verbessern",
                    "description": "Fügen Sie detailliertere Produktbeschreibungen und mehr Bilder hinzu",
                    "expected_impact": "medium",
                    "implementation_effort": "medium",
                    "source": "system"
                },
                {
                    "id": "rec3",
                    "category": "ux",
                    "title": "Mobile Benutzeroberfläche optimieren",
                    "description": "Verbessern Sie die Ladezeit und Benutzerfreundlichkeit auf mobilen Geräten",
                    "expected_impact": "high",
                    "implementation_effort": "high",
                    "source": "system"
                }
            ]
            
            # Erweitern Sie mit datenbasierten Erkenntnissen
            revenue_insights = self.get_revenue_insights()
            
            if revenue_insights.get("status") == "success":
                trend = revenue_insights.get("trend")
                growth_rate = revenue_insights.get("growth_rate", 0)
                
                if trend == "falling" or growth_rate < 0:
                    recommendations.append({
                        "id": "rec_revenue_1",
                        "category": "sales",
                        "title": "Umsatzrückgang entgegenwirken",
                        "description": f"Ihr Umsatz ist um {abs(growth_rate)}% gesunken. Starten Sie eine gezielte Werbekampagne für Ihre meistverkauften Produkte.",
                        "expected_impact": "high",
                        "implementation_effort": "medium",
                        "source": "data_analysis"
                    })
                elif growth_rate > 15:
                    recommendations.append({
                        "id": "rec_revenue_2",
                        "category": "growth",
                        "title": "Wachstum ausnutzen",
                        "description": f"Ihr Umsatz ist um {growth_rate}% gestiegen. Erwägen Sie, Ihr Produktangebot zu erweitern, um von diesem Momentum zu profitieren.",
                        "expected_impact": "high",
                        "implementation_effort": "high",
                        "source": "data_analysis"
                    })
            
            # Sortieren nach erwartetem Impact
            impact_score = {
                "low": 1,
                "medium": 2,
                "high": 3
            }
            
            sorted_recommendations = sorted(
                recommendations,
                key=lambda x: impact_score.get(x.get("expected_impact"), 0),
                reverse=True
            )
            
            return sorted_recommendations[:5]  # Top 5 Empfehlungen zurückgeben
            
        except Exception as e:
            logger.error(f"Fehler bei der Generierung von Wachstumsempfehlungen: {e}")
            return []
    
    def generate_personalized_tips(self, shop_data, tracking_data):
        """Generiert personalisierte Tipps basierend auf Shop- und Tracking-Daten"""
        try:
            # In einer realen Anwendung würde dies auf tiefgreifenden Analysen und ML-Modellen basieren
            # Hier zeigen wir eine vereinfachte Version
            
            tips = []
            
            # Wenn Tracking-Daten verfügbar sind
            if tracking_data and 'pageviews' in tracking_data:
                pageviews = tracking_data.get('pageviews', [])
                
                # Analyse der am häufigsten besuchten Seiten
                page_counts = {}
                for pv in pageviews:
                    page = pv.get('page', '')
                    page_counts[page] = page_counts.get(page, 0) + 1
                
                # Meistbesuchte Seiten
                top_pages = sorted(page_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                
                if top_pages:
                    tips.append({
                        "title": "Optimieren Sie Ihre Top-Seiten",
                        "description": f"Ihre meistbesuchte Seite ist '{top_pages[0][0]}'. Verbessern Sie die Benutzerfreundlichkeit und Konversionsrate dieser Seite, um die Gesamtleistung zu steigern."
                    })
            
            # Basierend auf Shop-Metriken
            metric_summary = self.shop_metrics.get_metrics_summary()
            
            # Umsatzwachstum
            revenue_growth = metric_summary.get('revenue_growth', 0)
            if revenue_growth < 0:
                tips.append({
                    "title": "Umsatzrückgang analysieren",
                    "description": f"Ihr Umsatz ist um {abs(revenue_growth)}% gesunken. Überprüfen Sie Preise, Marketingmaßnahmen und Produktverfügbarkeit."
                })
            elif revenue_growth > 10:
                tips.append({
                    "title": "Positives Wachstum fortsetzen",
                    "description": f"Gratulation! Ihr Umsatz ist um {revenue_growth}% gestiegen. Identifizieren Sie die Faktoren hinter diesem Erfolg und verstärken Sie diese."
                })
            
            # Durchschnittlicher Bestellwert
            avg_order = metric_summary.get('avg_order_value', 0)
            if avg_order > 0:
                tips.append({
                    "title": "Durchschnittlichen Bestellwert steigern",
                    "description": f"Ihr durchschnittlicher Bestellwert beträgt {avg_order}€. Erhöhen Sie ihn durch Cross-Selling und Produktbündel."
                })
            
            # Fallback, wenn keine datenbasierten Tipps generiert werden konnten
            if not tips:
                tips = [
                    {
                        "title": "Kundenrezensionen sammeln",
                        "description": "Bitten Sie Kunden nach dem Kauf um Bewertungen, um das Vertrauen potenzieller Käufer zu stärken."
                    },
                    {
                        "title": "Social-Media-Präsenz aufbauen",
                        "description": "Stärken Sie Ihre Marke durch regelmäßige Posts und Interaktionen in sozialen Medien."
                    },
                    {
                        "title": "Retargeting-Kampagnen starten",
                        "description": "Erreichen Sie Besucher, die Ihren Shop verlassen haben, durch gezielte Werbung."
                    }
                ]
            
            # Maximal 3 Tipps zurückgeben
            return tips[:3]
            
        except Exception as e:
            logger.error(f"Fehler bei der Generierung personalisierter Tipps: {e}")
            return []

    def get_ai_recommendations(self, shop_domain, shop_data=None, customer_segments=None):
        """
        Generiert intelligente Empfehlungen mit KI (wenn OpenAI API verfügbar)
        oder simuliert dies mit vordefinierten Empfehlungen.
        """
        try:
            # Wenn keine OpenAI API verfügbar ist, verwenden wir vordefinierte Empfehlungen
            if not OPENAI_API_KEY:
                logger.info("Kein OpenAI-API-Schlüssel gefunden, verwende vordefinierte Empfehlungen")
                return self._get_predefined_recommendations(shop_domain, shop_data, customer_segments)
            
            # Wenn der API-Schlüssel vorhanden ist, OpenAI nutzen
            import openai
            openai.api_key = OPENAI_API_KEY
            
            # Kontext für die KI vorbereiten
            context = {
                "shop_domain": shop_domain,
                "metrics_summary": self.shop_metrics.get_metrics_summary(),
                "customer_segments": customer_segments or {},
                "shop_data": {
                    "products_count": len(shop_data.get("products", [])) if shop_data else 0,
                    "orders_count": len(shop_data.get("orders", [])) if shop_data else 0,
                    "customers_count": len(shop_data.get("customers", [])) if shop_data else 0
                }
            }
            
            # OpenAI-Anfrage
            try:
                response = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Du bist ein E-Commerce-Wachstumsexperte, der präzise, praktische Empfehlungen gibt."},
                        {"role": "user", "content": f"Basierend auf diesen Shop-Daten: {json.dumps(context)}, gib 3 spezifische Wachstumsempfehlungen im JSON-Format mit den Feldern 'title', 'description', 'implementation_steps', und 'expected_impact'. Antworte NUR mit dem JSON."}
                    ]
                )
                
                # Antwort verarbeiten
                ai_response = response.choices[0].message.content.strip()
                try:
                    # Versuchen, JSON zu extrahieren
                    start_idx = ai_response.find('[')
                    end_idx = ai_response.rfind(']') + 1
                    
                    if start_idx != -1 and end_idx != -1:
                        json_str = ai_response[start_idx:end_idx]
                        recommendations = json.loads(json_str)
                    else:
                        # Fallback, falls kein gültiges JSON gefunden wird
                        recommendations = self._get_predefined_recommendations(shop_domain, shop_data, customer_segments)
                        
                    return recommendations
                except json.JSONDecodeError:
                    logger.error("Fehler beim Parsen der KI-Antwort als JSON")
                    return self._get_predefined_recommendations(shop_domain, shop_data, customer_segments)
                    
            except Exception as e:
                logger.error(f"Fehler bei der OpenAI-Anfrage: {e}")
                return self._get_predefined_recommendations(shop_domain, shop_data, customer_segments)
                
        except Exception as e:
            logger.error(f"Fehler bei der KI-Empfehlungsgenerierung: {e}")
            return []
    
    def _get_predefined_recommendations(self, shop_domain, shop_data=None, customer_segments=None):
        """Gibt vordefinierte Empfehlungen zurück, wenn die KI nicht verfügbar ist"""
        
        # Basisempfehlungen
        recommendations = [
            {
                "title": "Kundenbindungsprogramm einführen",
                "description": "Belohnen Sie Stammkunden mit einem Treueprogramm, um Wiederholungskäufe zu fördern.",
                "implementation_steps": [
                    "Treuepunktesystem definieren",
                    "Automatisierte E-Mails für Punkte-Updates einrichten",
                    "Exklusive Angebote für Mitglieder erstellen"
                ],
                "expected_impact": "hoch"
            },
            {
                "title": "Produktbündelangebote optimieren",
                "description": "Erhöhen Sie den durchschnittlichen Bestellwert durch strategische Produktbündel.",
                "implementation_steps": [
                    "Häufig zusammen gekaufte Produkte identifizieren",
                    "Preisstrategien für Bündel entwickeln",
                    "Bündel auf Produktseiten bewerben"
                ],
                "expected_impact": "mittel"
            },
            {
                "title": "Checkout-Prozess vereinfachen",
                "description": "Reduzieren Sie Kaufabbrüche durch einen optimierten Checkout-Prozess.",
                "implementation_steps": [
                    "Unnötige Felder entfernen",
                    "Gastbestellung aktivieren",
                    "Fortschrittsanzeige implementieren"
                ],
                "expected_impact": "hoch"
            }
        ]
        
        # Wenn Kundensegmente verfügbar sind, spezifischere Empfehlungen hinzufügen
        if customer_segments and "high_value" in customer_segments and len(customer_segments["high_value"]) > 0:
            recommendations.append({
                "title": "VIP-Programm für hochwertige Kunden",
                "description": f"Sie haben {len(customer_segments['high_value'])} hochwertige Kunden. Erstellen Sie ein exklusives Programm für diese Gruppe.",
                "implementation_steps": [
                    "Exklusive Angebote nur für VIPs erstellen",
                    "Frühzeitigen Zugang zu neuen Produkten anbieten",
                    "Persönliche Einkaufsberatung einführen"
                ],
                "expected_impact": "sehr hoch"
            })
        
        return recommendations 