import '@shopify/shopify-api/adapters/node';
import { shopifyApi, LATEST_API_VERSION } from '@shopify/shopify-api';
import { SQLiteSessionStorage } from '@shopify/shopify-app-session-storage-sqlite';
import { PostgreSQLSessionStorage } from '@shopify/shopify-app-session-storage-postgresql';
import express from 'express';
import { gdprRoutes, initWebhooks } from './webhooks';

// Ensure environment variables are loaded
try {
  require('dotenv').config();
  console.log('Environment loaded from .env file');
} catch (error) {
  console.warn('Failed to load .env file:', error);
}

// Debug: Print environment variables (with sensitive info redacted)
console.log('Environment variables:');
console.log('- SHOPIFY_API_KEY:', process.env.SHOPIFY_API_KEY ? '[REDACTED]' : 'undefined');
console.log('- SHOPIFY_API_SECRET:', process.env.SHOPIFY_API_SECRET ? '[REDACTED]' : 'undefined');
console.log('- HOST:', process.env.HOST || 'undefined');
console.log('- SCOPES:', process.env.SCOPES || 'undefined');

// For development without .env file, use these default values
const DEFAULT_API_KEY = 'dummy_api_key';
const DEFAULT_API_SECRET = 'dummy_api_secret';
const DEFAULT_HOST = 'http://localhost:8081';
const DEFAULT_SCOPES = 'read_products,write_products,read_orders';

const isProd = process.env.NODE_ENV === 'production';

// Configure session storage based on environment
const sessionStorage = isProd
  ? new PostgreSQLSessionStorage(process.env.DATABASE_URL || '')
  : new SQLiteSessionStorage('./database.sqlite');

// Ensure HOST has protocol prefix
const hostWithProtocol = process.env.HOST
  ? (process.env.HOST.startsWith('http') ? process.env.HOST : `https://${process.env.HOST}`)
  : DEFAULT_HOST;

console.log('Using HOST with protocol:', hostWithProtocol);

// Initialize Shopify API with fallback to default values if env vars are missing
export const shopify = shopifyApi({
  apiKey: process.env.SHOPIFY_API_KEY || DEFAULT_API_KEY,
  apiSecretKey: process.env.SHOPIFY_API_SECRET || DEFAULT_API_SECRET,
  scopes: process.env.SCOPES?.split(',') || DEFAULT_SCOPES.split(','),
  hostName: hostWithProtocol.replace(/https?:\/\//, ''),
  hostScheme: hostWithProtocol.startsWith('https') ? 'https' : 'http',
  apiVersion: LATEST_API_VERSION,
  isEmbeddedApp: true,
  sessionStorage: sessionStorage,
});

// Export session storage for use elsewhere
export const storage = sessionStorage;

// Initialize webhooks module with the shopify client and storage
initWebhooks(shopify, sessionStorage);

// Setup OAuth routes
export const setupAuth = (app: express.Express) => {
  // Register GDPR webhook routes
  app.use('/webhooks', gdprRoutes);

  // OAuth starting point - redirects to Shopify
  app.get('/auth', async (req, res) => {
    if (!req.query.shop) {
      return res.status(400).send('Missing shop parameter');
    }

    const shop = req.query.shop as string;
    const redirectUrl = await shopify.auth.begin({
      shop,
      callbackPath: '/auth/callback',
      isOnline: false,
      rawRequest: req,
      rawResponse: res
    });
    return res.redirect(redirectUrl);
  });

  // OAuth callback - after shop approval
  app.get('/auth/callback', async (req, res) => {
    try {
      const callbackResponse = await shopify.auth.callback({
        rawRequest: req,
        rawResponse: res,
      });
      
      const host = req.query.host as string;
      // Access the session from the callback response
      const { session } = callbackResponse;

      // Successful auth - redirect to app with shop parameter
      res.redirect(`/?shop=${session.shop}&host=${host}`);
    } catch (error) {
      console.error('OAuth callback error', error);
      res.status(500).send('Error during authentication');
    }
  });

  // Verify authenticated requests
  app.use('/api/*', async (req, res, next) => {
    const shop = req.query.shop as string || '';
    
    try {
      // Get session based on shop
      const sessionId = await shopify.session.getCurrentId({
        isOnline: false,
        rawRequest: req,
        rawResponse: res
      });
      
      if (!sessionId) {
        return res.status(401).send('Unauthorized');
      }
      
      const session = await sessionStorage.loadSession(sessionId);
      
      if (!session) {
        return res.status(401).send('Unauthorized');
      }
      
      // Store session in request object for route handlers
      (req as any).shopifySession = session;
      next();
    } catch (error) {
      console.error('Auth verification error', error);
      res.status(401).send('Unauthorized');
    }
  });

  return app;
};

// Create authenticated client for GraphQL queries
export const createClient = async (session: any) => {
  return new shopify.clients.Graphql({ session });
};

export default setupAuth; 