// Diagnose-API, um zu prüfen, ob API-Routen funktionieren
const express = require('express');
const app = express();

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

// Exportiere die Express-App für Vercel Serverless
module.exports = app; 