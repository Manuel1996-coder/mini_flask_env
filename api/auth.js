const express = require('express');
const crypto = require('crypto');
const querystring = require('querystring');
const axios = require('axios');
const app = require('./_app');

// Replace with your actual credentials
const SHOPIFY_API_KEY = process.env.SHOPIFY_API_KEY || 'your-api-key';
const SHOPIFY_API_SECRET = process.env.SHOPIFY_API_SECRET || 'your-api-secret';
const SCOPES = 'read_products,write_products,read_customers,read_orders,write_orders';
const APP_URL = process.env.APP_URL || 'https://shoppulse.vercel.app';
const REDIRECT_URI = `${APP_URL}/api/auth/callback`;

// Global nonce store (in production use Redis/database)
const nonceStore = new Map();

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

// Register required GDPR webhooks
async function registerWebhooks(shop, accessToken) {
  const webhooks = [
    {
      topic: 'customers/data_request',
      address: `${APP_URL}/api/webhooks/customers/data_request`,
      format: 'json'
    },
    {
      topic: 'customers/redact',
      address: `${APP_URL}/api/webhooks/customers/redact`,
      format: 'json'
    },
    {
      topic: 'shop/redact',
      address: `${APP_URL}/api/webhooks/shop/redact`,
      format: 'json'
    }
  ];

  const registerPromises = webhooks.map(webhook => {
    return axios.post(
      `https://${shop}/admin/api/2023-10/webhooks.json`,
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

// Start the OAuth process
app.get('/api/auth', (req, res) => {
  const shop = req.query.shop;
  
  if (!shop) {
    return res.status(400).json({ error: 'Missing shop parameter' });
  }
  
  // Shopify requires myshopify.com domain
  if (!shop.includes('myshopify.com')) {
    return res.status(400).json({ error: 'Invalid shop domain. Must be a myshopify.com domain.' });
  }
  
  console.log(`Starting OAuth flow for shop: ${shop}`);
  
  // Generate and store nonce for this shop
  const nonce = generateNonce();
  nonceStore.set(shop, nonce);
  
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
  const { shop, code, state, hmac } = req.query;
  
  console.log(`Received OAuth callback from Shopify for shop: ${shop}`);
  
  if (!shop || !code || !hmac) {
    console.error('Missing required OAuth callback parameters', req.query);
    return res.status(400).json({ error: 'Required parameters missing' });
  }
  
  // Retrieve and verify the nonce
  const storedNonce = nonceStore.get(shop);
  if (!storedNonce || state !== storedNonce) {
    console.error(`Invalid state parameter. Expected: ${storedNonce}, Received: ${state}`);
    return res.status(403).json({ error: 'Invalid state parameter' });
  }
  
  // Clean up the nonce
  nonceStore.delete(shop);
  
  // Verify the HMAC
  try {
    if (!verifyHmac(req.query)) {
      console.error('HMAC validation failed for OAuth callback');
      return res.status(403).json({ error: 'HMAC validation failed' });
    }
  } catch (error) {
    console.error('HMAC validation error:', error);
    return res.status(403).json({ error: 'HMAC validation error' });
  }
  
  // Exchange the authorization code for an access token
  try {
    console.log(`Exchanging auth code for token for shop: ${shop}`);
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
    
    // In a real app, you would store this token securely
    // For this demo, we'll set it in a cookie
    res.setHeader('Set-Cookie', [
      `shopifyAccessToken=${accessToken}; Path=/; HttpOnly; SameSite=None; Secure`,
      `shopifyShop=${shop}; Path=/; HttpOnly; SameSite=None; Secure`
    ]);
    
    // Redirect to the embedded app
    const appRedirectUrl = `/dashboard?shop=${shop}`;
    console.log(`OAuth completed, redirecting to: ${appRedirectUrl}`);
    res.redirect(appRedirectUrl);
  } catch (error) {
    console.error('Error exchanging code for token:', error.response?.data || error.message);
    res.status(500).json({ error: 'Error exchanging code for token' });
  }
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

module.exports = app; 