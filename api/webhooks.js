const express = require('express');
const crypto = require('crypto');
const bodyParser = require('body-parser');
const app = require('./_app');

// Replace with your actual secret
const SHOPIFY_API_SECRET = process.env.SHOPIFY_API_SECRET || 'your-api-secret';

// Use raw body parser for webhook verification
const rawBodyParser = bodyParser.raw({ type: 'application/json' });

// Verify Shopify webhook HMAC
function verifyWebhookHmac(req) {
  const hmacHeader = req.headers['x-shopify-hmac-sha256'];
  if (!hmacHeader) return false;

  const hash = crypto
    .createHmac('sha256', SHOPIFY_API_SECRET)
    .update(req.body)
    .digest('base64');

  return crypto.timingSafeEqual(
    Buffer.from(hash),
    Buffer.from(hmacHeader)
  );
}

// Handle mandatory compliance webhooks
app.post('/api/webhooks/customers/data_request', rawBodyParser, (req, res) => {
  // Verify the webhook is from Shopify
  if (!verifyWebhookHmac(req)) {
    return res.status(401).send('Webhook HMAC validation failed');
  }

  const data = JSON.parse(req.body.toString());
  console.log('Received customer data request webhook');
  
  // In a real implementation, you would:
  // 1. Gather all customer data
  // 2. Create a report
  // 3. Upload to the provided URL or create a downloadable file
  
  // Here we're just acknowledging receipt
  res.status(200).send('Customer data request received');
});

app.post('/api/webhooks/customers/redact', rawBodyParser, (req, res) => {
  // Verify the webhook is from Shopify
  if (!verifyWebhookHmac(req)) {
    return res.status(401).send('Webhook HMAC validation failed');
  }

  const data = JSON.parse(req.body.toString());
  console.log('Received customer redact webhook');
  
  // In a real implementation, you would:
  // 1. Delete all customer data associated with this customer
  // 2. Log the deletion for compliance purposes
  
  // Here we're just acknowledging receipt
  res.status(200).send('Customer redact request received');
});

app.post('/api/webhooks/shop/redact', rawBodyParser, (req, res) => {
  // Verify the webhook is from Shopify
  if (!verifyWebhookHmac(req)) {
    return res.status(401).send('Webhook HMAC validation failed');
  }

  const data = JSON.parse(req.body.toString());
  console.log('Received shop redact webhook');
  
  // In a real implementation, you would:
  // 1. Delete all shop data associated with this shop
  // 2. Log the deletion for compliance purposes
  
  // Here we're just acknowledging receipt
  res.status(200).send('Shop redact request received');
});

module.exports = app; 