// Serverless Funktion für /api/recommendations
const { parse } = require('url');

// Vercel Serverless Funktion
module.exports = async (req, res) => {
  // CORS-Header hinzufügen
  res.setHeader('Access-Control-Allow-Credentials', true);
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version'
  );

  // OPTIONS-Anfragen für CORS bearbeiten
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  // Nur POST-Anfragen erlauben
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

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
}; 