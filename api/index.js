// Minimale Express App für Shopify OAuth
const express = require('express');
const cors = require('cors');
const crypto = require('crypto');
const axios = require('axios');
const cookieParser = require('cookie-parser');
// Session-Modul entfernen, da es mit Serverless/Vercel nicht gut funktioniert
// const session = require('express-session');
const querystring = require('querystring');
const dotenv = require('dotenv');
const path = require('path');

dotenv.config();

const SHOPIFY_API_KEY = process.env.SHOPIFY_API_KEY;
const SHOPIFY_API_SECRET = process.env.SHOPIFY_API_SECRET;
const SCOPES = 'read_products,write_products,read_orders,read_customers';
// Statt direkter URL, nutze die HOST-Umgebungsvariable wie in shopify.app.toml
const HOST = process.env.HOST || 'https://mini-flask-env.vercel.app';
const REDIRECT_URI = `${HOST}/auth/callback`;
// Shopify API Version
const API_VERSION = process.env.SHOPIFY_API_VERSION || '2023-10';

const app = express();
// CORS mit vollständigen Optionen konfigurieren
app.use(cors({
  origin: true,
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['X-CSRF-Token', 'X-Requested-With', 'Accept', 'Accept-Version', 'Content-Length', 'Content-MD5', 'Content-Type', 'Date', 'X-Api-Version', 'Authorization'],
  exposedHeaders: ['Set-Cookie']
}));

app.use(express.json());
app.use(cookieParser());

// Session-Middleware entfernen, stattdessen direkt mit Cookies arbeiten
// app.use(session({
//   secret: SHOPIFY_API_SECRET,
//   resave: false,
//   saveUninitialized: true,
//   cookie: {
//     secure: true,
//     httpOnly: true,
//     sameSite: 'none',
//     maxAge: 24 * 60 * 60 * 1000 // 24 Stunden
//   }
// }));

// Statische Dateien aus dem public-Ordner ausliefern (für lokale Entwicklung)
app.use(express.static('public'));

// Middleware für Cross-Origin Ressourcen deaktivieren, wird von cors package übernommen
// app.use((req, res, next) => {
//   // Debug-Ausgabe für Cookies
//   console.log('Cookies:', req.cookies);
//   
//   // CORS-Header verbessern
//   res.setHeader('Access-Control-Allow-Credentials', true);
//   res.setHeader('Access-Control-Allow-Origin', '*');
//   if (req.headers.origin) {
//     res.setHeader('Access-Control-Allow-Origin', req.headers.origin);
//   }
//   res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
//   res.setHeader('Access-Control-Allow-Headers', 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, Authorization');
//   if (req.method === 'OPTIONS') return res.status(200).end();
//   next();
// });

// Hilfsfunktion zum Setzen von sicheren Cookies
function setSecureCookies(res, cookieName, cookieValue, options = {}) {
  // Für Vercel-Umgebung optimierte Einstellungen
  const defaultOptions = {
    path: '/',
    httpOnly: false, // Auf false setzen, damit JavaScript auch darauf zugreifen kann
    secure: true,
    sameSite: 'none',
    maxAge: 24 * 60 * 60 * 1000 // 24 Stunden
  };
  
  const cookieOptions = { ...defaultOptions, ...options };
  console.log(`Cookie setzen: ${cookieName} mit Optionen:`, cookieOptions);
  res.cookie(cookieName, cookieValue, cookieOptions);
}

function generateNonce() {
  return crypto.randomBytes(16).toString('hex');
}

function verifyHmac(query) {
  const hmac = query.hmac;
  delete query.hmac;
  const message = querystring.stringify(query);
  const generatedHash = crypto.createHmac('sha256', SHOPIFY_API_SECRET)
    .update(message)
    .digest('hex');
  try {
    return crypto.timingSafeEqual(Buffer.from(generatedHash, 'hex'), Buffer.from(hmac, 'hex'));
  } catch (error) {
    return false;
  }
}

app.get('/api/auth', (req, res) => {
  const shop = req.query.shop;
  if (!shop) return res.status(400).json({ error: 'Shop parameter is required' });
  if (!shop.includes('myshopify.com')) return res.status(400).json({ error: 'Invalid shop domain' });
  
  const nonce = generateNonce();
  
  // Nonce als Cookie statt in Session speichern
  setSecureCookies(res, 'shopify_nonce', nonce);
  // Shop auch als Cookie speichern
  setSecureCookies(res, 'shopify_shop', shop);
  
  const redirectUrl = `https://${shop}/admin/oauth/authorize?` +
    querystring.stringify({
      client_id: SHOPIFY_API_KEY,
      scope: SCOPES,
      redirect_uri: REDIRECT_URI,
      state: nonce
    });
  res.redirect(redirectUrl);
});

app.get('/api/auth/callback', async (req, res) => {
  const { shop, code, state, hmac } = req.query;
  if (!shop || !code || !hmac) return res.status(400).json({ error: 'Required parameters missing' });
  
  // Diagnostische Ausgaben
  console.log('Auth Callback erhalten:', { shop, code: code ? 'Vorhanden' : 'Fehlt', state });
  console.log('Cookies:', req.cookies);
  
  const nonce = req.cookies?.shopify_nonce;
  console.log('Nonce aus Cookie:', nonce, 'State aus Query:', state);
  
  if (!nonce || state !== nonce) return res.status(403).json({ error: 'Invalid state parameter', cookieNonce: nonce, queryState: state });
  if (!verifyHmac(req.query)) return res.status(403).json({ error: 'HMAC validation failed' });
  
  try {
    const tokenResponse = await axios.post(`https://${shop}/admin/oauth/access_token`, {
      client_id: SHOPIFY_API_KEY,
      client_secret: SHOPIFY_API_SECRET,
      code
    });
    
    const accessToken = tokenResponse.data.access_token;
    console.log('Token erhalten:', accessToken ? 'Ja' : 'Nein');
    
    // Access Token als Cookie speichern (nicht in Session)
    setSecureCookies(res, 'shopifyAccessToken', accessToken);
    setSecureCookies(res, 'shopifyShop', shop);
    
    // Sofort zur App-UI weiterleiten (wichtig für Shopify-Check)
    // Baue die Redirect-URL mit den erforderlichen Parametern
    const redirectUrl = `/dashboard?shop=${shop}&host=${req.query.host || ''}&embedded=1`;
    console.log(`Redirect nach Authentication zu: ${redirectUrl}`);
    res.redirect(redirectUrl);
  } catch (error) {
    console.error('OAuth-Fehler:', error.message);
    res.status(500).json({ error: 'Failed to complete OAuth', details: error.message });
  }
});

app.get('/api/shopify/api-key', (req, res) => {
  res.json({ apiKey: SHOPIFY_API_KEY });
});

// Shop-KPIs abrufen
app.get('/api/shop-kpis', async (req, res) => {
  try {
    console.log('❗ KPI-Abruf gestartet - REAL DATA WITHOUT CUSTOMER INFO');
    console.log('🍪 Cookies:', req.cookies);
    
    // Daten aus Cookies lesen, alternative Quellen: Header als Fallback
    let shop = req.cookies?.shopifyShop || req.headers['x-shopify-shop'] || req.query.shop;
    let accessToken = req.cookies?.shopifyAccessToken || req.headers['x-shopify-access-token'];
    
    console.log('🏪 Shop:', shop);
    console.log('🔑 Token vorhanden:', !!accessToken);

    if (!shop || !accessToken) {
      return res.status(401).json({ 
        error: 'Authentication required', 
        debug: { 
          cookies: req.cookies,
          hasShop: !!shop,
          hasToken: !!accessToken
        } 
      });
    }

    try {
      // 1. Shop-Informationen abrufen
      console.log('🏬 Hole Shop-Informationen');
      const shopResponse = await axios({
        method: 'get',
        url: `https://${shop}/admin/api/${API_VERSION}/shop.json`,
        headers: {
          'X-Shopify-Access-Token': accessToken,
          'Content-Type': 'application/json'
        }
      }).catch(err => {
        console.error('❌ Fehler bei Shop-API:', err.response?.status, err.response?.statusText);
        console.error('❌ Details:', err.response?.data || err.message);
        throw new Error(`Shop API Error: ${err.response?.status} ${err.response?.data?.errors || err.message}`);
      });
      
      // 2. Orders count abrufen
      console.log('🔢 Hole Orders Count');
      const ordersCountResponse = await axios({
        method: 'get',
        url: `https://${shop}/admin/api/${API_VERSION}/orders/count.json`,
        params: {
          status: 'any'
        },
        headers: {
          'X-Shopify-Access-Token': accessToken,
          'Content-Type': 'application/json'
        }
      }).catch(err => {
        console.error('❌ Fehler bei Orders Count API:', err.response?.status, err.response?.statusText);
        console.error('❌ Details:', err.response?.data || err.message);
        return { data: { count: 0 } };
      });
      
      // 3. Orders abrufen (nur mit minimalen Feldern für Berechnung)
      console.log('🛍️ Hole Orders mit minimalen Feldern');
      const ordersResponse = await axios({
        method: 'get',
        url: `https://${shop}/admin/api/${API_VERSION}/orders.json`,
        params: {
          status: 'any',
          limit: 100, // Erhöht auf 100 für mehr Daten
          fields: 'id,created_at,processed_at,total_price,currency' // Zusätzliche Felder für bessere Filterung
        },
        headers: {
          'X-Shopify-Access-Token': accessToken,
          'Content-Type': 'application/json'
        }
      }).catch(err => {
        console.error('❌ Fehler bei Orders API:', err.response?.status, err.response?.statusText);
        console.error('❌ Details:', err.response?.data || err.message);
        return { data: { orders: [] } };
      });
      
      // 4. Produkte abrufen
      console.log('📦 Hole Produkte');
      const productsResponse = await axios({
        method: 'get',
        url: `https://${shop}/admin/api/${API_VERSION}/products.json`,
        params: {
          limit: 10,
          fields: 'id,title,image,variants' // Nur die wichtigsten Felder
        },
        headers: {
          'X-Shopify-Access-Token': accessToken,
          'Content-Type': 'application/json'
        }
      }).catch(err => {
        console.error('❌ Fehler bei Products-API:', err.response?.status, err.response?.statusText);
        return { data: { products: [] } };
      });
      
      // Daten extrahieren
      const shopData = shopResponse.data.shop;
      const orders = ordersResponse.data.orders || [];
      const products = productsResponse.data.products || [];
      const totalOrderCount = ordersCountResponse.data.count || 0;
      
      console.log(`✅ Daten geladen: ${orders.length} neueste Bestellungen, ${totalOrderCount} Bestellungen gesamt, ${products.length} Produkte`);
      
      // Heute-Datum für Filterung
      const now = new Date();
      const todayStr = now.toISOString().split('T')[0]; // YYYY-MM-DD
      
      // Bestellungen heute filtern
      const ordersToday = orders.filter(order => {
        try {
          // Convert order.created_at to shop's timezone before comparison
          const orderDate = new Date(order.created_at);
          const orderDateStr = orderDate.toISOString().split('T')[0];
          return orderDateStr === todayStr;
        } catch (e) {
          console.error('⚠️ Fehler beim Filtern heutiger Bestellungen:', e);
          return false;
        }
      });
      
      console.log(`DEBUG: Heute ist ${todayStr}, gefundene Bestellungen heute: ${ordersToday.length}`);
      console.log('DEBUG: Alle Bestellungsdaten:', orders.map(o => ({ id: o.id, date: o.created_at })));
      
      // Letzte 7 Tage
      const lastWeekDate = new Date(now);
      lastWeekDate.setDate(now.getDate() - 7);
      
      const ordersThisWeek = orders.filter(order => {
        try {
          const orderDate = new Date(order.created_at);
          return orderDate >= lastWeekDate;
        } catch (e) {
          console.error('⚠️ Fehler beim Filtern der Wochenbestellungen:', e);
          return false;
        }
      });
      
      // Umsatzberechnung
      const calculateRevenue = (orderList) => {
        return orderList.reduce((sum, order) => sum + parseFloat(order.total_price || 0), 0).toFixed(2);
      };
      
      // Top-Produkte aufbereiten
      const topProducts = products.map(product => ({
        id: product.id,
        title: product.title,
        inventory: product.variants[0]?.inventory_quantity || 0,
        image: product.image?.src || 'https://placehold.co/100x100',
        price: product.variants[0]?.price || '0.00'
      }));

      // KPIs zusammenstellen
      const kpis = {
        shop: {
          name: shopData.name,
          email: shopData.email,
          domain: shopData.domain,
          created_at: shopData.created_at
        },
        orders: {
          today: ordersToday.length,
          thisWeek: ordersThisWeek.length,
          thisMonth: orders.length, // Vereinfacht: Nur die letzten 50 Bestellungen
          total: totalOrderCount
        },
        revenue: {
          today: calculateRevenue(ordersToday),
          thisWeek: calculateRevenue(ordersThisWeek),
          thisMonth: calculateRevenue(orders), // Vereinfacht: Nur die letzten 50 Bestellungen
          total: calculateRevenue(orders) // Vereinfacht: Nur die letzten 50 Bestellungen
        },
        topProducts,
        // Debug-Informationen
        debug: {
          apiVersion: API_VERSION,
          ordersLoaded: orders.length,
          ordersToday: ordersToday.length,
          ordersThisWeek: ordersThisWeek.length,
          todayDate: todayStr,
          serverTime: new Date().toISOString(),
          orderDateSamples: orders.length > 0 ? 
            orders.slice(0, Math.min(5, orders.length)).map(o => ({
              id: o.id,
              created_at: o.created_at,
              processed_at: o.processed_at,
              is_today: new Date(o.created_at).toISOString().split('T')[0] === todayStr
            })) : [],
          isRealData: true
        }
      };

      console.log('✅ KPIs erfolgreich generiert (Echte Daten ohne Kundendaten)');
      res.json(kpis);
    } catch (apiError) {
      console.error('❌ API-Fehler:', apiError.message);
      res.status(500).json({ 
        error: 'Failed to fetch shop KPIs',
        message: apiError.message
      });
    }
  } catch (outerError) {
    console.error('❌ Unerwarteter Fehler:', outerError.message);
    res.status(500).json({
      error: 'Unexpected server error',
      message: outerError.message
    });
  }
});

// /dashboard Route auf dashboard.html mappen (für lokale Entwicklung)
app.get('/dashboard', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/dashboard.html'));
});

// Root-Route auf /embedded weiterleiten (für Shopify-Flow)
app.get('/', (req, res) => {
  res.redirect('/embedded');
});

// /embedded Route auf embedded.html mappen (für lokale Entwicklung)
app.get('/embedded', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/embedded.html'));
});

// Shopify API-Test
app.get('/api/test-shopify', async (req, res) => {
  try {
    console.log('Cookies bei Test:', req.cookies);
    
    // Daten aus Cookies lesen, alternative Quellen: Header als Fallback
    let shop = req.cookies?.shopifyShop || req.headers['x-shopify-shop'] || req.query.shop;
    let accessToken = req.cookies?.shopifyAccessToken || req.headers['x-shopify-access-token'];
    
    if (!shop) {
      return res.status(400).json({ error: 'Shop parameter required' });
    }
    
    if (!accessToken) {
      return res.status(401).json({ 
        error: 'Access token required',
        shop: shop,
        cookies: req.cookies
      });
    }
    
    // Vereinfachter API-Test: Shop-Metadaten abfragen
    try {
      const shopResponse = await axios.get(
        `https://${shop}/admin/api/${API_VERSION}/shop.json`,
        {
          headers: {
            'X-Shopify-Access-Token': accessToken
          }
        }
      );
      
      res.json({
        success: true,
        shop: shopResponse.data.shop,
        apiVersion: API_VERSION,
        message: 'Shopify API funktioniert!'
      });
    } catch (apiError) {
      console.error('API-Fehler beim Test:', apiError.response?.data || apiError.message);
      res.status(500).json({
        error: 'Shopify API Error',
        message: apiError.response?.data?.errors || apiError.message,
        status: apiError.response?.status,
        apiVersion: API_VERSION
      });
    }
  } catch (error) {
    console.error('Unerwarteter Fehler im Test-Endpunkt:', error);
    res.status(500).json({
      error: 'Unexpected server error',
      message: error.message
    });
  }
});

// Webhook-Endpunkt für Shopify mit HMAC-Validierung
app.post('/api/webhooks', express.raw({type: 'application/json'}), (req, res) => {
  try {
    // HMAC-Header von Shopify auslesen
    const hmacHeader = req.headers['x-shopify-hmac-sha256'];
    if (!hmacHeader) {
      console.error('Webhook ohne HMAC-Signatur erhalten');
      return res.status(401).send('Keine HMAC-Signatur gefunden');
    }

    // HMAC-Signatur verifizieren
    const calculatedHmac = crypto
      .createHmac('sha256', SHOPIFY_API_SECRET)
      .update(req.body)
      .digest('base64');

    // Timing-Safe Compare der Signaturen
    if (crypto.timingSafeEqual(Buffer.from(calculatedHmac), Buffer.from(hmacHeader))) {
      console.log('✅ Webhook HMAC-Signatur ist gültig');

      // Verarbeite den Webhook-Payload
      const webhookPayload = JSON.parse(req.body.toString('utf8'));
      const topic = req.headers['x-shopify-topic'];
      
      console.log(`📥 Webhook empfangen: ${topic}`);
      
      switch (topic) {
        case 'products/create':
          console.log('Neues Produkt erstellt:', webhookPayload.id);
          break;
        case 'orders/create':
          console.log('Neue Bestellung erstellt:', webhookPayload.id);
          break;
        // Weitere Webhook-Topics hier verarbeiten
        default:
          console.log(`Webhook-Topic "${topic}" nicht verarbeitet`);
      }

      res.status(200).send('Webhook erfolgreich verarbeitet');
    } else {
      console.error('❌ Ungültige HMAC-Signatur');
      res.status(401).send('Ungültige Signatur');
    }
  } catch (error) {
    console.error('Fehler bei der Webhook-Verarbeitung:', error);
    res.status(500).send('Interner Serverfehler');
  }
});

// Nur lokal starten, wenn direkt ausgeführt (nicht in Vercel)
if (require.main === module) {
  const PORT = process.env.PORT || 3000;
  app.listen(PORT, () => {
    console.log(`Server läuft lokal auf http://localhost:${PORT}`);
  });
}

module.exports = app; 