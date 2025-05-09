// Serverless Funktion für /api/price-optimize
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
}; 