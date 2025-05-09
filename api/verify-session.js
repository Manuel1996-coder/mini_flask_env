// Endpoint zur Verifikation von Shopify Session Tokens
const app = require('./_app');
const { validateSessionToken } = require('./middleware');

// Verwende die validateSessionToken-Middleware, um das Token zu überprüfen
app.get('/api/verify-session', validateSessionToken, (req, res) => {
  console.log(`Session Token für Shop ${req.shopDomain} erfolgreich verifiziert`);
  
  // Wenn wir hier ankommen, wurde das Token bereits validiert
  res.json({
    status: 'success',
    message: 'Session token is valid',
    shop: req.shopDomain,
    timestamp: new Date().toISOString()
  });
});

module.exports = app; 