// Serverless Funktion für /api/products
const products = [
  { 
    id: 'gid://shopify/Product/1', 
    title: 'Beispielprodukt 1',
    variants: [{ price: '19.99' }]
  },
  { 
    id: 'gid://shopify/Product/2', 
    title: 'Beispielprodukt 2',
    variants: [{ price: '29.99' }]
  }
];

// Vercel Serverless Funktion
module.exports = (req, res) => {
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

  // Nur GET-Anfragen erlauben
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Produkte zurückgeben
  return res.status(200).json({ products });
}; 