// Consolidated Express App for all API routes
const express = require('express');
const cors = require('cors');
const crypto = require('crypto');
const axios = require('axios');
const bodyParser = require('body-parser');
const cookieParser = require('cookie-parser');
const path = require('path');
const querystring = require('querystring');
const dotenv = require('dotenv');

// Load environment variables
dotenv.config();

// Environment variables
const SHOPIFY_API_KEY = process.env.SHOPIFY_API_KEY || 'your-api-key';
const SHOPIFY_API_SECRET = process.env.SHOPIFY_API_SECRET || 'your-api-secret';
const SCOPES = process.env.SCOPES || 'read_products,write_products,read_customers,read_orders,write_orders';
const APP_URL = process.env.APP_URL || 'https://shoppulse.vercel.app';
const REDIRECT_URI = `${APP_URL}/api/auth/callback`;

// --- App Version Log ---
const APP_NAME = 'ShopPulseAI'; // Or read from package.json if you prefer
const DEPLOYMENT_TIMESTAMP = new Date().toISOString();
console.log(`🚀 ${APP_NAME} - Version/Deployment: ${DEPLOYMENT_TIMESTAMP} - Server starting...`);
// --- End App Version Log ---

// Create Express app
const app = express();

// Global nonce store (in production use Redis/database)
const nonceStore = new Map();

// ----- MIDDLEWARE -----

// Standard middleware
app.use(cors({
  origin: true,
  credentials: true
}));
app.use(express.json());
app.use(cookieParser());

// CORS-Handler for all routes
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

// ----- HELPER FUNCTIONS -----

// Generate a random nonce for CSRF protection
function generateNonce() {
  return crypto.randomBytes(16).toString('hex');
}

// Verify the HMAC signature from Shopify
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

// Verify Shopify webhook HMAC
function verifyWebhookHmac(req) {
  const hmacHeader = req.headers['x-shopify-hmac-sha256'];
  if (!hmacHeader) return false;

  const hash = crypto
    .createHmac('sha256', SHOPIFY_API_SECRET)
    .update(req.body)
    .digest('base64');

  try {
    return crypto.timingSafeEqual(
      Buffer.from(hash),
      Buffer.from(hmacHeader)
    );
  } catch (error) {
    console.error('Webhook HMAC verification error:', error);
    return false;
  }
}

// Register required GDPR webhooks
async function registerWebhooks(shop, accessToken) {
  const SHOPIFY_API_VERSION = process.env.SHOPIFY_API_VERSION || '2024-04'; // Use env variable or fallback
  const webhooks = [
    {
      topic: 'customers/data_request',
      address: `${APP_URL}/api/webhooks/customers/data_request`, // This one seems to match already
      format: 'json'
    },
    {
      topic: 'customers/redact',
      address: `${APP_URL}/api/gdpr/customer-redact`, // Updated path
      format: 'json'
    },
    {
      topic: 'shop/redact',
      address: `${APP_URL}/api/gdpr/shop-redact`, // Updated path
      format: 'json'
    }
  ];

  const registerPromises = webhooks.map(webhook => {
    return axios.post(
      `https://${shop}/admin/api/${SHOPIFY_API_VERSION}/webhooks.json`, // Use dynamic API version
      { webhook },
      {
        headers: {
          'X-Shopify-Access-Token': accessToken,
          'Content-Type': 'application/json'
        }
      }
    ).catch(error => {
      console.error(`Error registering ${webhook.topic} webhook:`, error.message);
      // Continue even if one webhook fails
      return null;
    });
  });

  await Promise.all(registerPromises);
  console.log('Webhooks registered successfully');
}

// ----- MIDDLEWARE FUNCTIONS -----

// Session token validation middleware
const validateSessionToken = async (req, res, next) => {
  // Get the session token from authorization header
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ 
      error: 'Unauthorized',
      message: 'Missing session token' 
    });
  }

  const sessionToken = authHeader.replace('Bearer ', '');
  const shop = req.headers['x-shopify-shop-domain'];

  if (!shop) {
    return res.status(401).json({ 
      error: 'Unauthorized',
      message: 'Missing shop domain' 
    });
  }

  try {
    // Validate the session token with Shopify
    // In a real app, you would verify this properly with Shopify's API
    // For this demo, we'll assume it's valid if it's present
    // and save it for API requests
    
    req.sessionToken = sessionToken;
    req.shopDomain = shop;
    
    // Continue to the next middleware
    next();
  } catch (error) {
    console.error('Session token validation error:', error);
    return res.status(401).json({ 
      error: 'Unauthorized',
      message: 'Invalid session token' 
    });
  }
};

// Authentication check middleware (for cookie-based auth)
const checkAuth = (req, res, next) => {
  const token = req.cookies?.shopifyAccessToken;
  const shop = req.cookies?.shopifyShop;
  
  if (!token || !shop) {
    return res.status(401).json({ 
      error: 'Unauthorized',
      message: 'Authentication required' 
    });
  }
  
  // Store the token and shop for use in the controller
  req.shopifyToken = token;
  req.shopDomain = shop;
  
  next();
};

// Raw body parser for webhook verification
const rawBodyParser = bodyParser.raw({ type: 'application/json' });

// ----- API ROUTES -----

// Root API route
app.get('/api', (req, res) => {
  res.json({ 
    message: 'ShopPulseAI API is running',
    version: '1.0.1',
    timestamp: new Date().toISOString(),
    features: [
      'OAuth Authentication',
      'Session Token Support',
      'GDPR Compliance Webhooks',
      'HMAC Verification'
    ]
  });
});

// Health check for Vercel
app.get('/api/health', (req, res) => {
  res.status(200).json({ status: 'ok' });
});

// ----- AUTH ROUTES -----

// Start the OAuth process
app.get('/api/auth', (req, res) => {
  console.log(`==== AUTH START ====`);
  console.log(`Auth request received with query:`, JSON.stringify(req.query));
  console.log(`Cookies:`, JSON.stringify(req.cookies));
  console.log(`Headers:`, JSON.stringify(req.headers));
  
  const shop = req.query.shop;
  
  if (!shop) {
    console.error(`Missing shop parameter in request:`, JSON.stringify(req.query));
    return res.status(400).json({ error: 'Missing shop parameter' });
  }
  
  // Shopify requires myshopify.com domain
  if (!shop.includes('myshopify.com')) {
    console.error(`Invalid shop domain: ${shop}. Must be a myshopify.com domain.`);
    return res.status(400).json({ error: 'Invalid shop domain. Must be a myshopify.com domain.' });
  }
  
  console.log(`Starting OAuth flow for shop: ${shop}`);
  
  // Generate a nonce for CSRF protection
  const nonce = generateNonce();
  console.log(`Generated nonce: ${nonce}`);
  
  // Store nonce in cookie
  res.setHeader('Set-Cookie', `shopify_nonce=${nonce}; Path=/; HttpOnly; SameSite=None; Secure`);
  console.log(`Set nonce cookie`);
  
  // Build the authorization URL
  const redirectUrl = `https://${shop}/admin/oauth/authorize?` +
    querystring.stringify({
      client_id: SHOPIFY_API_KEY,
      scope: SCOPES,
      redirect_uri: REDIRECT_URI,
      state: nonce
    });
    
  // Redirect to Shopify's authorization page
  console.log(`Redirecting to Shopify auth: ${redirectUrl}`);
  res.redirect(redirectUrl);
});

// Handle the OAuth callback
app.get('/api/auth/callback', async (req, res) => {
  console.log(`==== AUTH CALLBACK ====`);
  console.log(`Received OAuth callback from Shopify with query:`, JSON.stringify(req.query));
  console.log(`Cookies:`, JSON.stringify(req.cookies));
  
  const { shop, code, state, hmac } = req.query;
  
  if (!shop || !code || !hmac) {
    console.error('Missing required parameters:', JSON.stringify(req.query));
    return res.status(400).json({ error: 'Required parameters missing' });
  }
  
  // Get the nonce from cookie
  const nonce = req.cookies?.shopify_nonce;
  console.log(`Nonce from cookie: ${nonce}, State from query: ${state}`);
  
  if (!nonce || state !== nonce) {
    console.error(`State validation failed. Expected: ${nonce}, Got: ${state}`);
    return res.status(403).json({ error: 'Invalid state parameter' });
  }
  
  try {
    // Verify the HMAC
    const hmacValid = verifyHmac(req.query);
    console.log(`HMAC validation result: ${hmacValid}`);
    
    if (!hmacValid) {
      console.error('HMAC validation failed');
      return res.status(403).json({ error: 'HMAC validation failed' });
    }
    
    console.log(`Exchanging code for token for shop: ${shop}`);
    
    // Exchange the authorization code for an access token
    const tokenResponse = await axios.post(
      `https://${shop}/admin/oauth/access_token`,
      {
        client_id: SHOPIFY_API_KEY,
        client_secret: SHOPIFY_API_SECRET,
        code
      }
    );
    
    const accessToken = tokenResponse.data.access_token;
    console.log(`Successfully obtained access token for ${shop}`);
    
    // Register webhooks after getting access token
    await registerWebhooks(shop, accessToken);
    
    // Set cookies with the access token and shop
    res.setHeader('Set-Cookie', [
      `shopifyAccessToken=${accessToken}; Path=/; HttpOnly; SameSite=None; Secure`,
      `shopifyShop=${shop}; Path=/; HttpOnly; SameSite=None; Secure`
    ]);
    console.log(`Set cookies for shop and token`);
    
    // Redirect to the app
    const redirectUrl = `/dashboard?shop=${shop}`;
    console.log(`OAuth completed, redirecting to: ${redirectUrl}`);
    res.redirect(redirectUrl);
    
  } catch (error) {
    console.error('Error exchanging code for token:', error.response?.data || error.message);
    res.status(500).json({ 
      error: 'Error exchanging code for token',
      details: error.message,
      stack: error.stack
    });
  }
});

// API endpoint to check authentication status
app.get('/api/auth-status', (req, res) => {
  const token = req.cookies?.shopifyAccessToken;
  const shop = req.cookies?.shopifyShop;
  
  res.json({
    authenticated: !!token,
    shop: shop || null
  });
});

// Endpoint to validate session tokens
app.get('/api/auth/validate-session', (req, res) => {
  // In a real app, you would validate the session token
  // For this demo, we'll just check if the cookie exists
  const token = req.cookies?.shopifyAccessToken;
  const shop = req.cookies?.shopifyShop;
  
  if (!token || !shop) {
    return res.status(401).json({ valid: false, message: 'No valid session' });
  }
  
  // In production, verify the token is still valid with Shopify
  return res.json({ valid: true, shop });
});

// Endpoint for Shopify to verify our app is alive
app.get('/api/auth/shopify', (req, res) => {
  const shop = req.query.shop;
  
  if (shop) {
    // This endpoint is typically hit when Shopify checks if our app is alive
    // Redirect to the auth flow
    return res.redirect(`/api/auth?shop=${encodeURIComponent(shop)}`);
  }
  
  res.status(400).json({ error: 'Missing shop parameter' });
});

// Handle Shopify app install route
app.get('/api/app/install', (req, res) => {
  const shop = req.query.shop;
  
  if (!shop) {
    return res.status(400).json({ error: 'Shop parameter is required' });
  }
  
  res.redirect(`/api/auth?shop=${shop}`);
});

// Fix für die install.html Form - neue Route
app.get('/api/install', (req, res) => {
  console.log('Received install request with query:', JSON.stringify(req.query));
  const shop = req.query.shop;
  
  if (!shop) {
    return res.status(400).json({ error: 'Shop parameter is required' });
  }
  
  console.log(`Redirecting to auth flow for shop: ${shop}`);
  res.redirect(`/api/auth?shop=${shop}`);
});

// ----- PRODUCT ROUTES -----

// Products endpoint
app.get('/api/products', validateSessionToken, (req, res) => {
  // In a real app, this would fetch products from Shopify API
  // using the session token
  const mockProducts = [
    { id: 1, title: 'Sample Product 1', price: '29.99' },
    { id: 2, title: 'Sample Product 2', price: '49.99' },
    { id: 3, title: 'Sample Product 3', price: '19.99' }
  ];
  
  res.json(mockProducts);
});

// ----- RECOMMENDATION ROUTES -----

// Recommendations endpoint
app.get('/api/recommendations', validateSessionToken, (req, res) => {
  // In a real app, this would generate recommendations
  // based on store data and AI analysis
  const mockRecommendations = [
    { id: 1, product_id: 1, suggestion: 'Increase price by 5%', confidence: 0.89 },
    { id: 2, product_id: 2, suggestion: 'Add to featured collection', confidence: 0.76 },
    { id: 3, product_id: 3, suggestion: 'Bundle with Product 1', confidence: 0.92 }
  ];
  
  res.json(mockRecommendations);
});

// POST version of recommendations endpoint
app.post('/api/recommendations', validateSessionToken, (req, res) => {
  try {
    // Request-Body parsen (wenn vorhanden)
    let trackingData = {};
    if (req.body) {
      trackingData = req.body.trackingData || {};
    }

    // Beispiel-Empfehlungen basierend auf Tracking-Daten generieren
    const recommendation = 'Basierend auf Ihren Verkaufsdaten könnten Sie von einer Preisoptimierung für Ihre meistverkauften Produkte profitieren.';
    
    // Antwort senden
    res.status(200).json({
      recommendation,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Error generating recommendation:', error);
    res.status(500).json({ 
      error: 'Failed to generate recommendation',
      details: error.message 
    });
  }
});

// ----- PRICE OPTIMIZATION ROUTES -----

// Price optimization endpoint
app.post('/api/price-optimize', validateSessionToken, (req, res) => {
  try {
    // Request-Body parsen
    let products = [];
    if (req.body && req.body.products) {
      products = req.body.products;
    } else {
      return res.status(400).json({ error: 'No products provided' });
    }

    // Preisoptimierung durchführen
    const optimizedProducts = products.map(product => {
      const price = parseFloat(product.price || 0);
      return {
        ...product,
        originalPrice: price,
        suggestedPrice: (price * 1.1).toFixed(2), // 10% Erhöhung 
        potentialRevenue: (price * 1.1 * 1.2).toFixed(2) // geschätzte Umsatzsteigerung mit neuem Preis
      };
    });

    // Antwort senden
    res.status(200).json({ products: optimizedProducts });
  } catch (error) {
    console.error('Error optimizing prices:', error);
    res.status(500).json({ 
      error: 'Failed to optimize prices',
      details: error.message 
    });
  }
});

// ----- WEBHOOK ROUTES -----

// Handle mandatory GDPR webhooks
app.post('/api/webhooks/customers/data_request', rawBodyParser, (req, res) => {
  // Verify the webhook is from Shopify
  if (!verifyWebhookHmac(req)) {
    return res.status(401).send('Webhook HMAC validation failed');
  }

  const data = JSON.parse(req.body.toString());
  console.log('Received customer data request webhook');
  
  // In a real implementation, you would:
  // 1. Gather all customer data
  // 2. Create a report
  // 3. Upload to the provided URL or create a downloadable file
  
  // Here we're just acknowledging receipt
  res.status(200).send('Customer data request received');
});

// Renamed route to match Shopify config
app.post('/api/gdpr/customer-redact', rawBodyParser, (req, res) => {
  // Verify the webhook is from Shopify
  if (!verifyWebhookHmac(req)) {
    return res.status(401).send('Webhook HMAC validation failed');
  }

  const data = JSON.parse(req.body.toString());
  console.log('Received customer redact webhook');
  
  // In a real implementation, you would:
  // 1. Delete all customer data associated with this customer
  // 2. Log the deletion for compliance purposes
  
  // Here we're just acknowledging receipt
  res.status(200).send('Customer redact request received');
});

// Renamed route to match Shopify config
app.post('/api/gdpr/shop-redact', rawBodyParser, (req, res) => {
  // Verify the webhook is from Shopify
  if (!verifyWebhookHmac(req)) {
    return res.status(401).send('Webhook HMAC validation failed');
  }

  const data = JSON.parse(req.body.toString());
  console.log('Received shop redact webhook');
  
  // In a real implementation, you would:
  // 1. Delete all shop data associated with this shop
  // 2. Log the deletion for compliance purposes
  
  // Here we're just acknowledging receipt
  res.status(200).send('Shop redact request received');
});

// ----- VERIFY SESSION ROUTES -----

// Endpoint to test session tokens
app.get('/api/verify-session', validateSessionToken, (req, res) => {
  res.json({
    status: 'success',
    message: 'Session token is valid',
    shop: req.shopDomain,
    timestamp: new Date().toISOString()
  });
});

// ----- DOMAIN TEST ROUTES -----

app.get('/api/domain', (req, res) => {
  // Zeige Umgebungsvariablen (ohne Geheimnisse)
  const APP_URL = process.env.APP_URL || 'Not set';
  const NODE_ENV = process.env.NODE_ENV || 'Not set';
  
  // Sende eine Erfolgsantwort mit Informationen
  res.json({
    message: 'API is functioning correctly',
    timestamp: new Date().toISOString(),
    appUrl: APP_URL,
    environment: NODE_ENV,
    headers: req.headers
  });
});

// ----- TEST ROUTE -----

app.get('/api/test', (req, res) => {
  res.status(200).json({
    message: 'API endpoint is working',
    timestamp: new Date().toISOString(),
    query: req.query,
    url: req.url,
    method: req.method
  });
});

// ----- APP BRIDGE ROUTE -----

// Endpoint, um den API-Key für AppBridge zu holen
app.get('/api/shopify/api-key', (req, res) => {
  res.json({ apiKey: SHOPIFY_API_KEY });
});

// Export the app for Vercel
module.exports = app; 