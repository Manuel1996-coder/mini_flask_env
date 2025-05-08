import requests
import json
import logging
import time
from functools import wraps
from flask_caching import Cache
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportQueryError
import os
from dotenv import load_dotenv

# Logger einrichten
logger = logging.getLogger('shopify_api')

# Environment-Variablen laden
load_dotenv()

# Cache-Konfiguration
cache_config = {
    "DEBUG": os.environ.get('DEBUG', 'False').lower() == 'true',
    "CACHE_TYPE": "SimpleCache",  # In Produktion durch "RedisCache" ersetzen
    "CACHE_DEFAULT_TIMEOUT": 300,  # Standard-Timeout in Sekunden (5 Minuten)
}

# Cache initialisieren (wird später im app-Kontext initialisiert)
cache = Cache(config=cache_config)

# Konstanten für API-Ratenbegrenzungen
MAX_API_RETRIES = 3
API_RATE_LIMIT_DELAY = 1  # Sekunden

# GraphQL-Abfragen
PRODUCTS_QUERY = """
query GetProducts($first: Int!, $after: String) {
  products(first: $first, after: $after) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        title
        description
        productType
        handle
        createdAt
        updatedAt
        totalInventory
        variants(first: 10) {
          edges {
            node {
              id
              title
              price
              compareAtPrice
              inventoryQuantity
              sku
            }
          }
        }
        images(first: 1) {
          edges {
            node {
              id
              url
            }
          }
        }
        tags
      }
    }
  }
}
"""

ORDERS_QUERY = """
query GetOrders($first: Int!, $after: String, $query: String) {
  orders(first: $first, after: $after, query: $query) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        name
        createdAt
        updatedAt
        totalPrice
        totalTax
        subtotalPrice
        financialStatus
        fulfillmentStatus
        customer {
          id
          email
          firstName
          lastName
        }
        lineItems(first: 10) {
          edges {
            node {
              id
              title
              quantity
              originalTotalPrice {
                amount
                currencyCode
              }
              variant {
                id
                title
                price
                product {
                  id
                  title
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

CUSTOMERS_QUERY = """
query GetCustomers($first: Int!, $after: String, $query: String) {
  customers(first: $first, after: $after, query: $query) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        firstName
        lastName
        email
        phone
        createdAt
        updatedAt
        ordersCount
        totalSpent {
          amount
          currencyCode
        }
        addresses(first: 1) {
          edges {
            node {
              id
              address1
              city
              country
              zip
            }
          }
        }
        defaultAddress {
          id
          address1
          city
          country
          zip
        }
      }
    }
  }
}
"""

SHOP_INFO_QUERY = """
query GetShopInfo {
  shop {
    id
    name
    email
    url
    myshopifyDomain
    primaryDomain {
      url
      host
    }
    plan {
      displayName
      partnerDevelopment
      shopifyPlus
    }
    currencyCode
    billingAddress {
      country
      countryCodeV2
    }
  }
}
"""

def with_error_handling(func):
    """Dekorator für einheitliche Fehlerbehandlung der API-Funktionen"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        retries = 0
        last_error = None
        
        while retries < MAX_API_RETRIES:
            try:
                return func(*args, **kwargs)
            except TransportQueryError as e:
                # GraphQL spezifischer Fehler
                error_data = getattr(e, 'errors', None)
                if error_data and any('THROTTLED' in str(err) for err in error_data):
                    # Rate-Limit erreicht, warten und erneut versuchen
                    wait_time = API_RATE_LIMIT_DELAY * (2 ** retries)  # Exponentielles Backoff
                    logger.warning(f"Shopify API rate limit erreicht. Warte {wait_time}s vor dem nächsten Versuch.")
                    time.sleep(wait_time)
                    retries += 1
                    last_error = e
                    continue
                    
                logger.error(f"GraphQL-Fehler: {e}")
                raise
            except Exception as e:
                logger.error(f"API-Fehler: {type(e).__name__}: {e}")
                retries += 1
                last_error = e
                time.sleep(API_RATE_LIMIT_DELAY)
                
        # Nach allen Wiederholungsversuchen
        logger.error(f"Maximale Anzahl an Versuchen erreicht. Letzter Fehler: {last_error}")
        raise last_error
        
    return wrapper

def init_app(app):
    """Initialisiert die Shopify-API mit der Flask-App"""
    global cache
    cache.init_app(app)
    logger.info("Shopify API mit Caching initialisiert")

def get_graphql_client(shop, access_token):
    """Erstellt einen GraphQL-Client für Shopify"""
    transport = AIOHTTPTransport(
        url=f"https://{shop}/admin/api/2023-10/graphql.json",
        headers={"X-Shopify-Access-Token": access_token}
    )
    return Client(transport=transport, fetch_schema_from_transport=False)

@with_error_handling
@cache.memoize(timeout=300)  # 5 Minuten Cache
def get_shop_info(shop, access_token):
    """Ruft Informationen über den Shop ab"""
    client = get_graphql_client(shop, access_token)
    query = gql(SHOP_INFO_QUERY)
    result = client.execute(query)
    return result['shop']

@with_error_handling
@cache.memoize(timeout=300)  # 5 Minuten Cache
def get_products(shop, access_token, limit=50, cursor=None):
    """Ruft Produkte aus dem Shop ab mit Pagination"""
    client = get_graphql_client(shop, access_token)
    query = gql(PRODUCTS_QUERY)
    
    variables = {
        "first": limit
    }
    
    if cursor:
        variables["after"] = cursor
        
    result = client.execute(query, variable_values=variables)
    return result["products"]

@with_error_handling
@cache.memoize(timeout=300)  # 5 Minuten Cache
def get_orders(shop, access_token, limit=50, cursor=None, date_range=None):
    """Ruft Bestellungen aus dem Shop ab mit Pagination und optionalem Datumsfilter"""
    client = get_graphql_client(shop, access_token)
    query = gql(ORDERS_QUERY)
    
    variables = {
        "first": limit
    }
    
    if cursor:
        variables["after"] = cursor
        
    # Optionaler Datumsbereichsfilter als GraphQL-Query-String
    if date_range:
        variables["query"] = date_range
        
    result = client.execute(query, variable_values=variables)
    return result["orders"]

@with_error_handling
@cache.memoize(timeout=300)  # 5 Minuten Cache
def get_customers(shop, access_token, limit=50, cursor=None, search_query=None):
    """Ruft Kunden aus dem Shop ab mit Pagination und optionaler Suche"""
    client = get_graphql_client(shop, access_token)
    query = gql(CUSTOMERS_QUERY)
    
    variables = {
        "first": limit
    }
    
    if cursor:
        variables["after"] = cursor
        
    if search_query:
        variables["query"] = search_query
        
    result = client.execute(query, variable_values=variables)
    return result["customers"]

def clear_cache_for_shop(shop_domain):
    """Löscht den Cache für einen bestimmten Shop"""
    # Im SimpleCache ist das direktes Löschen nach Schlüssel nicht einfach möglich
    # In der Produktionsumgebung mit Redis wäre das einfacher
    logger.info(f"Cache für Shop {shop_domain} wird gelöscht")
    cache.clear()  # Löscht den gesamten Cache - in Produktion spezifischer implementieren

def make_rest_api_request(shop, access_token, endpoint, method="GET", data=None):
    """
    Führt eine REST-API-Anfrage an Shopify aus (für Funktionen, die nicht über GraphQL verfügbar sind)
    """
    url = f"https://{shop}/admin/api/2023-10/{endpoint}"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    
    for attempt in range(MAX_API_RETRIES):
        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Ungültige HTTP-Methode: {method}")
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:  # Rate limiting
                wait_time = API_RATE_LIMIT_DELAY * (2 ** attempt)
                logger.warning(f"REST API Rate-Limit erreicht. Warte {wait_time}s vor dem nächsten Versuch.")
                time.sleep(wait_time)
                continue
            logger.error(f"HTTP-Fehler: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"REST-API-Fehler: {type(e).__name__}: {e}")
            if attempt < MAX_API_RETRIES - 1:
                time.sleep(API_RATE_LIMIT_DELAY)
                continue
            raise
            
    raise Exception("Maximale Anzahl an API-Versuchen erreicht") 