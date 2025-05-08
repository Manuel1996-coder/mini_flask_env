# ShopPulseAI - Intelligent Analytics for Shopify

A Shopify app providing advanced analytics and growth recommendations for store owners.

## Features

- **Analytics Dashboard**: Visualize key store metrics and trends
- **Growth Advisor**: AI-powered recommendations to optimize your store
- **Price Optimizer**: Smart pricing suggestions based on market analysis
- **GDPR Compliant**: Full support for data privacy regulations

## Shopify App Requirements

This app is built to meet all Shopify App Store requirements:

### Technical Requirements

- **HTTPS/SSL**: Secure connections with proper certificate validation
- **OAuth 2.0**: Standard Shopify authentication flow
- **GDPR Compliance**: 
  - Data Request endpoint: `/webhook/customers/data_request`
  - Customer Data Deletion: `/webhook/customers/redact`
  - Shop Data Deletion: `/webhook/shop/redact`
- **Shopify API**: Uses the Shopify REST and GraphQL APIs

### App Setup Guide

1. Create a Shopify Partner account
2. Create a new app in the Partner Dashboard
3. Configure the app with:
   - App URL: `https://[your-app-domain].railway.app`
   - Allowed redirection URLs: `https://[your-app-domain].railway.app/auth/callback`
   - Add required scopes: `read_products, write_products, read_orders, read_customers, write_customers, read_analytics`

## Development Setup

### Requirements

- Python 3.10+
- Railway account (for deployment)

### Local Setup

1. Clone this repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the environment: 
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Create a `.env` file with your Shopify API credentials:
```
SHOPIFY_API_KEY=your_api_key
SHOPIFY_API_SECRET=your_api_secret
APP_URL=https://your_app_url
SECRET_KEY=your_secret_key
```
6. Run the app: `python wsgi.py`

### Deployment

This app is configured for deployment on Railway:

1. Connect your Railway account to your repository
2. Set the environment variables:
   - `SHOPIFY_API_KEY`
   - `SHOPIFY_API_SECRET`
   - `APP_URL`
   - `SECRET_KEY`
3. Deploy the app

## Troubleshooting

### SSL Certificate Issues

If you encounter SSL certificate verification issues:

1. Make sure the app is using the `certifi` package for SSL certificate validation
2. Check that `REQUESTS_CA_BUNDLE` and `SSL_CERT_FILE` environment variables are set to the certifi CA bundle
3. Ensure the `wsgi.py` file properly initializes SSL certificates

### OAuth Flow Problems

1. Verify your API key and secret are correct
2. Check that your redirect URI exactly matches what's in your Shopify app settings
3. Ensure your app domain has a valid SSL certificate
