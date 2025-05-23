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
const SCOPES = 'read_products,write_products,read_orders,read_script_tags,write_script_tags';
// Direkte URL statt environment Variable verwenden, damit es garantiert klappt
const REDIRECT_URI = 'https://mini-flask-env.vercel.app/api/auth/callback';
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
    
    res.redirect(`/dashboard?shop=${shop}`);
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
    console.log('❗ KPI-Abruf gestartet - MINIMAL VERSION');
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
      // Nur minimale Shop-Informationen abrufen
      console.log('🏬 Hole Shop-Informationen (minimal)');
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
      
      // Produkte (sehr limitiert, nur für Top-Produkte)
      console.log('📦 Hole minimale Produktdaten');
      const productsResponse = await axios({
        method: 'get',
        url: `https://${shop}/admin/api/${API_VERSION}/products.json`,
        params: {
          limit: 5 // Nur 5 Produkte holen
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
      const products = productsResponse.data.products || [];
      
      // Vereinfachte Top-Produkte
      const topProducts = products.map(product => ({
        id: product.id,
        title: product.title,
        inventory: product.variants[0]?.inventory_quantity || 0,
        image: product.image?.src || 'https://placehold.co/100x100',
        price: product.variants[0]?.price || '0.00'
      }));

      // Minimale Dummy-Daten für den Rest
      const dummyData = {
        ordersToday: 3,
        ordersWeek: 15,
        ordersMonth: 42,
        revenueToday: 299.95,
        revenueWeek: 1259.85,
        revenueMonth: 3499.75
      };

      // KPIs zusammenstellen
      const kpis = {
        shop: {
          name: shopData.name,
          email: shopData.email,
          domain: shopData.domain,
          created_at: shopData.created_at
        },
        orders: {
          today: dummyData.ordersToday,
          thisWeek: dummyData.ordersWeek,
          thisMonth: dummyData.ordersMonth,
          total: dummyData.ordersMonth
        },
        revenue: {
          today: dummyData.revenueToday.toFixed(2),
          thisWeek: dummyData.revenueWeek.toFixed(2),
          thisMonth: dummyData.revenueMonth.toFixed(2),
          total: dummyData.revenueMonth.toFixed(2)
        },
        topProducts,
        customerCount: 25, // Fester Dummy-Wert
        // Debug-Informationen
        debug: {
          apiVersion: API_VERSION,
          shopFound: !!shopData,
          productsFound: products.length,
          serverTime: new Date().toISOString(),
          isDummyData: true
        }
      };

      console.log('✅ KPIs erfolgreich generiert (Dummy-Daten)');
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

// Nur lokal starten, wenn direkt ausgeführt (nicht in Vercel)
if (require.main === module) {
  const PORT = process.env.PORT || 3000;
  app.listen(PORT, () => {
    console.log(`Server läuft lokal auf http://localhost:${PORT}`);
  });
}

module.exports = app; 