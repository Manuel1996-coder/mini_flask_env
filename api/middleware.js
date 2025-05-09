const axios = require('axios');

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

module.exports = {
  validateSessionToken,
  checkAuth
}; 