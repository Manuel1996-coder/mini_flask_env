// Serverless-Wrapper für Express
const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');

// Load environment variables
dotenv.config();

// Main Express app
const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// Import route handlers
const productsHandler = require('./products');
const recommendationsHandler = require('./recommendations');
const priceOptimizeHandler = require('./price-optimize');

// Register routes using Express
app.get('/api/products', (req, res) => productsHandler(req, res));
app.post('/api/recommendations', (req, res) => recommendationsHandler(req, res));
app.post('/api/price-optimize', (req, res) => priceOptimizeHandler(req, res));

// Default route
app.all('/api', (req, res) => {
  res.json({ message: 'ShopPulseAI API is running' });
});

// Required for Vercel serverless functions
module.exports = app; 