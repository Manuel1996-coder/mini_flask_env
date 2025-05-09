// Haupteinstiegspunkt für alle API-Anfragen
const express = require('express');
const cors = require('cors');
const cookieParser = require('cookie-parser');

// Hilfsfunktion für CORS-Header
const setCorsHeaders = (res) => {
  res.setHeader('Access-Control-Allow-Credentials', true);
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version'
  );
};

// Serverloses Express für Vercel
const app = express();

// Middleware
app.use(cors({
  origin: true,
  credentials: true
}));
app.use(express.json());
app.use(cookieParser());

// CORS-Handler für alle Routen
app.use((req, res, next) => {
  setCorsHeaders(res);
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }
  next();
});

// Standardroute für API-Endpunkt
app.get('/api', (req, res) => {
  res.json({ 
    message: 'ShopPulseAI API is running',
    version: '1.0.1',
    timestamp: new Date().toISOString()
  });
});

// Gesundheitscheck für Vercel
app.get('/api/health', (req, res) => {
  res.status(200).json({ status: 'ok' });
});

// Exportiere die App für Vercel
module.exports = app; 