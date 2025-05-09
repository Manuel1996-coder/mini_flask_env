// Minimale Express App für Shopify OAuth
const express = require('express');
const cors = require('cors');
const crypto = require('crypto');
const axios = require('axios');
const cookieParser = require('cookie-parser');
const querystring = require('querystring');
const dotenv = require('dotenv');

// Load environment variables
dotenv.config();

// Erforderliche Umgebungsvariablen
const SHOPIFY_API_KEY = process.env.SHOPIFY_API_KEY;
const SHOPIFY_API_SECRET = process.env.SHOPIFY_API_SECRET;
const SCOPES = process.env.SCOPES || 'read_products,write_products';
const APP_URL = process.env.APP_URL || 'https://shoppulse.vercel.app';
const REDIRECT_URI = `${APP_URL}/api/auth/callback`;

// Express App erstellen
const app = express();

// Grundlegende Middleware
app.use(cors({
  origin: true,
  credentials: true
}));
app.use(express.json());
app.use(cookieParser());

// CORS-Handler
app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Credentials', true);
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (req.headers.origin) {
    res.setHeader('Access-Control-Allow-Origin', req.headers.origin);
  }
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, Authorization'
  );
  
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }
  next();
});

// Hilfsfunktion: Nonce für CSRF-Schutz generieren
function generateNonce() {
  return crypto.randomBytes(16).toString('hex');
}

// Hilfsfunktion: HMAC verifizieren
function verifyHmac(query) {
  const hmac = query.hmac;
  delete query.hmac;
  
  const message = querystring.stringify(query);
  const generatedHash = crypto.createHmac('sha256', SHOPIFY_API_SECRET)
    .update(message)
    .digest('hex');

  try {
    return crypto.timingSafeEqual(
      Buffer.from(generatedHash, 'hex'),
      Buffer.from(hmac, 'hex')
    );
  } catch (error) {
    console.error('HMAC verification error:', error);
    return false;
  }
}

// OAuth-Route: Start des Auth-Flows
app.get('/api/auth', (req, res) => {
  console.log('Auth Flow gestartet');
  const shop = req.query.shop;
  
  if (!shop) {
    return res.status(400).json({ error: 'Shop parameter is required' });
  }
  
  if (!shop.includes('myshopify.com')) {
    return res.status(400).json({ error: 'Invalid shop domain' });
  }
  
  // Nonce generieren
  const nonce = generateNonce();
  res.setHeader('Set-Cookie', `shopify_nonce=${nonce}; Path=/; HttpOnly; SameSite=None; Secure`);
  
  // Redirect zu Shopify Auth
  const redirectUrl = `https://${shop}/admin/oauth/authorize?` +
    querystring.stringify({
      client_id: SHOPIFY_API_KEY,
      scope: SCOPES,
      redirect_uri: REDIRECT_URI,
      state: nonce
    });
  
  res.redirect(redirectUrl);
});

// OAuth-Route: Callback nach erfolgreicher Autorisierung
app.get('/api/auth/callback', async (req, res) => {
  console.log('Auth Callback erhalten');
  const { shop, code, state, hmac } = req.query;
  
  if (!shop || !code || !hmac) {
    return res.status(400).json({ error: 'Required parameters missing' });
  }
  
  // Nonce prüfen
  const nonce = req.cookies?.shopify_nonce;
  if (!nonce || state !== nonce) {
    return res.status(403).json({ error: 'Invalid state parameter' });
  }
  
  try {
    // HMAC verifizieren
    if (!verifyHmac(req.query)) {
      return res.status(403).json({ error: 'HMAC validation failed' });
    }
    
    // Access Token abrufen
    const tokenResponse = await axios.post(
      `https://${shop}/admin/oauth/access_token`,
      {
        client_id: SHOPIFY_API_KEY,
        client_secret: SHOPIFY_API_SECRET,
        code
      }
    );
    
    const accessToken = tokenResponse.data.access_token;
    
    // Cookies setzen
    res.setHeader('Set-Cookie', [
      `shopifyAccessToken=${accessToken}; Path=/; HttpOnly; SameSite=None; Secure`,
      `shopifyShop=${shop}; Path=/; HttpOnly; SameSite=None; Secure`
    ]);
    
    // Zum Dashboard umleiten
    res.redirect(`/dashboard?shop=${shop}`);
    
  } catch (error) {
    console.error('Error exchanging code for token:', error);
    res.status(500).json({ error: 'Failed to complete OAuth' });
  }
});

// API-Key für App Bridge (für embedded apps)
app.get('/api/shopify/api-key', (req, res) => {
  res.json({ apiKey: SHOPIFY_API_KEY });
});

// Export für Vercel
module.exports = app; 