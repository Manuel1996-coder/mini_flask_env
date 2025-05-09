// Einfacher Vercel Serverless-Endpunkt ohne Express
module.exports = (req, res) => {
  res.status(200).json({
    message: 'API endpoint is working',
    timestamp: new Date().toISOString(),
    query: req.query,
    url: req.url,
    method: req.method
  });
}; 