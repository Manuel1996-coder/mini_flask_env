import json
import os
import logging
import datetime
import pandas as pd
import numpy as np
from collections import defaultdict

# Logger einrichten
logger = logging.getLogger('data_models')

# Konstanten
DATA_DIR = os.environ.get('DATA_DIR', 'data')
SHOP_DATA_FILE = os.path.join(DATA_DIR, 'shop_data.json')
METRICS_FILE = os.path.join(DATA_DIR, 'metrics.json')
TRACKING_FILE = os.path.join(DATA_DIR, 'tracking_data.json')

# Stellen Sie sicher, dass das Datenverzeichnis existiert
os.makedirs(DATA_DIR, exist_ok=True)

class ShopMetrics:
    """Klasse zur Verwaltung von Shop-Metriken"""
    
    def __init__(self, shop_domain):
        self.shop_domain = shop_domain
        self.metrics = defaultdict(dict)
        self.load_metrics()
        
    def load_metrics(self):
        """Lädt vorhandene Metriken aus der Datei oder initialisiert neue"""
        try:
            if os.path.exists(METRICS_FILE):
                with open(METRICS_FILE, 'r') as f:
                    all_metrics = json.load(f)
                    self.metrics = defaultdict(dict, all_metrics.get(self.shop_domain, {}))
                    logger.info(f"Metriken für Shop {self.shop_domain} geladen")
            else:
                logger.info(f"Keine vorhandenen Metriken gefunden für {self.shop_domain}, initialisiere neu")
        except Exception as e:
            logger.error(f"Fehler beim Laden der Metriken: {e}")
            
    def save_metrics(self):
        """Speichert die Metriken in der Datei"""
        try:
            # Zuerst vorhandene Metriken laden
            all_metrics = {}
            if os.path.exists(METRICS_FILE):
                with open(METRICS_FILE, 'r') as f:
                    all_metrics = json.load(f)
            
            # Aktualisieren und speichern
            all_metrics[self.shop_domain] = dict(self.metrics)
            with open(METRICS_FILE, 'w') as f:
                json.dump(all_metrics, f, indent=2)
                
            logger.info(f"Metriken für Shop {self.shop_domain} gespeichert")
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Metriken: {e}")
    
    def update_revenue_metrics(self, orders):
        """Aktualisiert Umsatzmetriken basierend auf Bestellungen"""
        try:
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            daily_revenue = 0
            order_count = 0
            
            for order in orders:
                # Berechnen Sie nur für Bestellungen von heute
                if order.get('node', {}).get('createdAt', '').startswith(today):
                    total_price = float(order.get('node', {}).get('totalPrice', 0))
                    daily_revenue += total_price
                    order_count += 1
            
            # Metriken aktualisieren
            if not self.metrics.get('daily_revenue'):
                self.metrics['daily_revenue'] = {}
                
            self.metrics['daily_revenue'][today] = daily_revenue
            
            if not self.metrics.get('daily_orders'):
                self.metrics['daily_orders'] = {}
                
            self.metrics['daily_orders'][today] = order_count
            
            # Durchschnittswert berechnen
            if order_count > 0:
                self.metrics['average_order_value'] = daily_revenue / order_count
            
            self.save_metrics()
            logger.info(f"Umsatzmetriken aktualisiert für {self.shop_domain}: {daily_revenue}€, {order_count} Bestellungen")
            
        except Exception as e:
            logger.error(f"Fehler bei der Aktualisierung der Umsatzmetriken: {e}")
    
    def update_customer_metrics(self, customers):
        """Aktualisiert Kundenmetriken basierend auf Kundendaten"""
        try:
            total_customers = len(customers)
            total_orders = sum(customer.get('node', {}).get('ordersCount', 0) for customer in customers)
            
            if total_customers > 0:
                # Durchschnittliche Bestellungen pro Kunde
                self.metrics['avg_orders_per_customer'] = total_orders / total_customers
                
                # Kundenherkunft analysieren
                countries = {}
                for customer in customers:
                    address = customer.get('node', {}).get('defaultAddress', {})
                    if address:
                        country = address.get('country')
                        if country:
                            countries[country] = countries.get(country, 0) + 1
                
                self.metrics['customer_countries'] = countries
                
                # Speichern
                self.save_metrics()
                logger.info(f"Kundenmetriken aktualisiert für {self.shop_domain}")
                
        except Exception as e:
            logger.error(f"Fehler bei der Aktualisierung der Kundenmetriken: {e}")
    
    def update_product_metrics(self, products):
        """Aktualisiert Produktmetriken basierend auf Produktdaten"""
        try:
            product_types = {}
            inventory_levels = {}
            
            for product in products:
                prod_data = product.get('node', {})
                product_type = prod_data.get('productType', 'Andere')
                
                # Produkttypen zählen
                product_types[product_type] = product_types.get(product_type, 0) + 1
                
                # Bestandsebenen erfassen
                inventory = prod_data.get('totalInventory', 0)
                if inventory is not None:
                    inventory_levels[prod_data.get('title')] = inventory
            
            self.metrics['product_types'] = product_types
            self.metrics['inventory_levels'] = inventory_levels
            
            # Speichern
            self.save_metrics()
            logger.info(f"Produktmetriken aktualisiert für {self.shop_domain}")
            
        except Exception as e:
            logger.error(f"Fehler bei der Aktualisierung der Produktmetriken: {e}")
    
    def update_traffic_metrics(self, tracking_data):
        """Aktualisiert Traffic-Metriken basierend auf Tracking-Daten"""
        try:
            if not tracking_data:
                logger.warning("Keine Tracking-Daten gefunden")
                return
                
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            
            # Initialisierung
            if 'daily_pageviews' not in self.metrics:
                self.metrics['daily_pageviews'] = {}
            if 'daily_visitors' not in self.metrics:
                self.metrics['daily_visitors'] = {}
            if 'device_stats' not in self.metrics:
                self.metrics['device_stats'] = {}
            
            # Zählen der Seitenaufrufe
            pageviews = len(tracking_data.get('pageviews', []))
            unique_visitors = len(set(pv.get('visitor_id') for pv in tracking_data.get('pageviews', [])))
            
            # Gerätestatistik
            devices = {}
            for pageview in tracking_data.get('pageviews', []):
                device = pageview.get('device', 'unknown')
                devices[device] = devices.get(device, 0) + 1
            
            # Metriken aktualisieren
            self.metrics['daily_pageviews'][today] = pageviews
            self.metrics['daily_visitors'][today] = unique_visitors
            self.metrics['device_stats'] = devices
            
            # Speichern
            self.save_metrics()
            logger.info(f"Traffic-Metriken aktualisiert für {self.shop_domain}: {pageviews} Aufrufe, {unique_visitors} Besucher")
            
        except Exception as e:
            logger.error(f"Fehler bei der Aktualisierung der Traffic-Metriken: {e}")
    
    def get_time_series_data(self, metric_name, days=30):
        """Gibt Zeitreihendaten für eine bestimmte Metrik zurück"""
        try:
            if metric_name not in self.metrics or not isinstance(self.metrics[metric_name], dict):
                logger.warning(f"Metrik {metric_name} nicht gefunden oder kein Zeitreihenformat")
                return []
                
            # Datumsliste erstellen
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=days-1)
            date_list = [(start_date + datetime.timedelta(days=i)).strftime('%Y-%m-%d') 
                        for i in range(days)]
            
            # Daten für jedes Datum abrufen
            result = []
            for date in date_list:
                value = self.metrics[metric_name].get(date, 0)
                result.append({"date": date, "value": value})
                
            return result
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Zeitreihendaten: {e}")
            return []
    
    def calculate_growth_rate(self, metric_name, days=30):
        """Berechnet die Wachstumsrate für eine bestimmte Metrik"""
        try:
            time_series = self.get_time_series_data(metric_name, days)
            if not time_series or len(time_series) < 2:
                return 0
                
            # Teilen in zwei Hälften für Vergleich
            half = len(time_series) // 2
            first_half = time_series[:half]
            second_half = time_series[half:]
            
            avg_first = sum(item['value'] for item in first_half) / len(first_half) if first_half else 0
            avg_second = sum(item['value'] for item in second_half) / len(second_half) if second_half else 0
            
            if avg_first == 0:
                return 0
                
            growth_rate = ((avg_second - avg_first) / avg_first) * 100
            return round(growth_rate, 2)
            
        except Exception as e:
            logger.error(f"Fehler bei der Berechnung der Wachstumsrate: {e}")
            return 0
    
    def get_top_products(self, limit=5):
        """Gibt die Top-Produkte basierend auf Verkaufszahlen zurück"""
        # In einer realen Implementierung würde dies auf tatsächlichen Verkaufsdaten basieren
        try:
            if 'product_sales' not in self.metrics:
                return []
                
            products = [(k, v) for k, v in self.metrics['product_sales'].items()]
            products.sort(key=lambda x: x[1], reverse=True)
            
            return [{"name": p[0], "sales": p[1]} for p in products[:limit]]
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Top-Produkte: {e}")
            return []
    
    def get_metrics_summary(self):
        """Gibt eine Zusammenfassung der wichtigsten Metriken zurück"""
        return {
            "revenue_growth": self.calculate_growth_rate("daily_revenue"),
            "orders_growth": self.calculate_growth_rate("daily_orders"),
            "visitors_growth": self.calculate_growth_rate("daily_visitors"),
            "avg_order_value": self.metrics.get("average_order_value", 0),
            "top_product_types": self.metrics.get("product_types", {}),
            "customer_countries": self.metrics.get("customer_countries", {})
        }


class DataAnalyzer:
    """Klasse für fortgeschrittene Datenanalysen"""
    
    def __init__(self, shop_metrics):
        self.shop_metrics = shop_metrics
    
    def convert_to_dataframe(self, metric_name, days=90):
        """Konvertiert Metrikdaten in ein Pandas DataFrame für Analysen"""
        try:
            time_series = self.shop_metrics.get_time_series_data(metric_name, days)
            if not time_series:
                return None
                
            df = pd.DataFrame(time_series)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Fehler bei der Konvertierung in DataFrame: {e}")
            return None
    
    def detect_seasonality(self, metric_name, days=90):
        """Erkennt saisonale Muster in den Daten"""
        try:
            df = self.convert_to_dataframe(metric_name, days)
            if df is None or len(df) < 14:  # Mindestens 2 Wochen Daten
                return {"seasonality": "unknown", "confidence": 0}
                
            # Wochentagsanalyse
            df['weekday'] = df.index.weekday
            weekly_pattern = df.groupby('weekday')['value'].mean()
            
            # Standardabweichung berechnen
            std_dev = weekly_pattern.std()
            mean_val = weekly_pattern.mean()
            
            # Bestimmen Sie, ob eine Saisonalität vorliegt
            if mean_val == 0:
                return {"seasonality": "unknown", "confidence": 0}
                
            variation_coeff = std_dev / mean_val
            
            if variation_coeff > 0.2:
                # Wochentag mit höchstem Wert finden
                best_day = weekly_pattern.idxmax()
                day_names = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
                
                return {
                    "seasonality": "weekly",
                    "best_day": day_names[best_day],
                    "confidence": min(variation_coeff * 100, 100)
                }
            else:
                return {"seasonality": "none", "confidence": 0}
                
        except Exception as e:
            logger.error(f"Fehler bei der Erkennung der Saisonalität: {e}")
            return {"seasonality": "error", "confidence": 0}
    
    def predict_future_values(self, metric_name, days_to_predict=7):
        """Einfache Prognose zukünftiger Werte basierend auf historischen Daten"""
        try:
            df = self.convert_to_dataframe(metric_name, 30)  # 30 Tage historische Daten
            if df is None or len(df) < 7:  # Mindestens 7 Tage Daten
                return []
            
            # Einfache Fortschreibung des gleitenden Durchschnitts
            window = min(7, len(df))
            rolling_avg = df['value'].rolling(window=window).mean().iloc[-1]
            
            # Letzten Wert und Trend ermitteln
            last_value = df['value'].iloc[-1]
            last_week = df['value'].iloc[-window:].mean()
            prev_week = df['value'].iloc[-window*2:-window].mean() if len(df) >= window*2 else last_week
            
            # Trendbestimmung
            trend = (last_week - prev_week) / window if prev_week > 0 else 0
            
            # Zukünftige Werte vorhersagen
            last_date = df.index[-1]
            predictions = []
            
            for i in range(1, days_to_predict + 1):
                future_date = (last_date + datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                predicted_value = max(0, last_value + trend * i)  # Keine negativen Werte
                predictions.append({"date": future_date, "value": round(predicted_value, 2)})
            
            return predictions
            
        except Exception as e:
            logger.error(f"Fehler bei der Vorhersage zukünftiger Werte: {e}")
            return []
    
    def segment_customers(self, customers, orders):
        """Segmentiert Kunden basierend auf RFM-Analyse (Recency, Frequency, Monetary)"""
        try:
            # In einer realen Implementierung würde dies auf tatsächlichen Kundendaten basieren
            # Hier implementieren wir ein Grundgerüst
            
            segments = {
                "high_value": [],
                "loyal": [],
                "potential": [],
                "at_risk": [],
                "inactive": []
            }
            
            # Simulierte Implementierung (in Realität mit tatsächlichen Daten)
            customer_data = {}
            
            for customer in customers:
                customer_id = customer.get('node', {}).get('id')
                if not customer_id:
                    continue
                    
                customer_data[customer_id] = {
                    "id": customer_id,
                    "name": f"{customer.get('node', {}).get('firstName', '')} {customer.get('node', {}).get('lastName', '')}",
                    "orders_count": customer.get('node', {}).get('ordersCount', 0),
                    "total_spent": float(customer.get('node', {}).get('totalSpent', {}).get('amount', 0))
                }
            
            # Einfache Segmentierung basierend auf Bestellhäufigkeit und Ausgaben
            for customer_id, data in customer_data.items():
                if data["orders_count"] >= 3 and data["total_spent"] >= 500:
                    segments["high_value"].append(data)
                elif data["orders_count"] >= 2:
                    segments["loyal"].append(data)
                elif data["total_spent"] > 0:
                    segments["potential"].append(data)
                else:
                    segments["inactive"].append(data)
            
            return segments
            
        except Exception as e:
            logger.error(f"Fehler bei der Kundensegmentierung: {e}")
            return {}
    
    def get_product_recommendations(self, customer_id, products, orders):
        """Generiert Produktempfehlungen für einen bestimmten Kunden"""
        # In einer realen Implementierung würde dies auf kollaborativem Filtern oder 
        # einem Machine-Learning-Modell basieren
        
        try:
            # Einfache zufällige Empfehlungen für Demozwecke
            # In einer realen Anwendung würden hier tatsächliche Empfehlungsalgorithmen verwendet
            if not products or len(products) < 3:
                return []
                
            sample_size = min(3, len(products))
            recommended_indices = np.random.choice(len(products), sample_size, replace=False)
            
            recommendations = []
            for idx in recommended_indices:
                product = products[idx].get('node', {})
                recommendations.append({
                    "id": product.get('id', ''),
                    "title": product.get('title', 'Unbekanntes Produkt'),
                    "reason": "Basierend auf vorherigen Käufen"  # Platzhalter
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Fehler bei der Generierung von Produktempfehlungen: {e}")
            return []
            

# Hilfsfunktionen

def load_tracking_data():
    """Lädt die Tracking-Daten aus der Datei"""
    try:
        if os.path.exists(TRACKING_FILE):
            with open(TRACKING_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Fehler beim Laden der Tracking-Daten: {e}")
        return {}

def save_tracking_data(data):
    """Speichert die Tracking-Daten in der Datei"""
    try:
        with open(TRACKING_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Tracking-Daten gespeichert")
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Tracking-Daten: {e}")

def add_tracking_event(shop, event_type, data):
    """Fügt ein Tracking-Ereignis hinzu"""
    try:
        tracking_data = load_tracking_data()
        
        # Shop-Eintrag initialisieren, wenn nicht vorhanden
        if shop not in tracking_data:
            tracking_data[shop] = {}
        
        # Ereignistyp initialisieren, wenn nicht vorhanden
        if event_type not in tracking_data[shop]:
            tracking_data[shop][event_type] = []
        
        # Zeitstempel hinzufügen
        data['timestamp'] = datetime.datetime.now().isoformat()
        
        # Ereignis hinzufügen
        tracking_data[shop][event_type].append(data)
        
        # Speichern
        save_tracking_data(tracking_data)
        logger.info(f"Tracking-Ereignis '{event_type}' für Shop {shop} hinzugefügt")
        
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen des Tracking-Ereignisses: {e}")

def get_shop_tracking_data(shop):
    """Gibt alle Tracking-Daten für einen bestimmten Shop zurück"""
    try:
        tracking_data = load_tracking_data()
        return tracking_data.get(shop, {})
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Shop-Tracking-Daten: {e}")
        return {} 