// OAuth Callback Handler für Shopify
const express = require('express');
const crypto = require('crypto');
const axios = require('axios');
const app = express();

// Handle the OAuth callback
app.get('/api/auth/callback', async (req, res) => {
  console.log('Received OAuth callback from Shopify');
  
  const { shop, code, state, hmac } = req.query;
  
  if (!shop || !code || !hmac) {
    console.error('Missing required parameters:', req.query);
    return res.status(400).json({ error: 'Required parameters missing' });
  }
  
  // Get the nonce from cookie
  const nonce = req.cookies?.shopify_nonce;
  if (!nonce || state !== nonce) {
    console.error(`State validation failed. Expected: ${nonce}, Got: ${state}`);
    return res.status(403).json({ error: 'Invalid state parameter' });
  }
  
  try {
    // Get credentials from environment variables
    const SHOPIFY_API_KEY = process.env.SHOPIFY_API_KEY;
    const SHOPIFY_API_SECRET = process.env.SHOPIFY_API_SECRET;
    
    if (!SHOPIFY_API_KEY || !SHOPIFY_API_SECRET) {
      console.error('Missing API credentials in environment variables');
      return res.status(500).json({ error: 'Server configuration error' });
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
    
    // Set cookies with the access token and shop
    res.setHeader('Set-Cookie', [
      `shopifyAccessToken=${accessToken}; Path=/; HttpOnly; SameSite=None; Secure`,
      `shopifyShop=${shop}; Path=/; HttpOnly; SameSite=None; Secure`
    ]);
    
    // Redirect to the app
    const APP_URL = process.env.APP_URL || 'https://shoppulse.vercel.app';
    const redirectUrl = `${APP_URL}/dashboard?shop=${shop}`;
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

module.exports = app; 