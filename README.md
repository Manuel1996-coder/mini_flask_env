# ShopPulseAI - Shopify OAuth App

A Shopify app for intelligente product recommendations and price optimization, deployable to Vercel.

## Features

- Complete Shopify OAuth implementation
- Compliance with Shopify's app requirements
- GDPR webhook handlers
- Automatic redirect to authorization for merchants
- Dashboard for authenticated users
- API endpoints for products, recommendations, and price optimization

## Setup

### Prerequisites

- Node.js (v18+)
- A Shopify Partner account
- A Vercel account

### Shopify App Setup

1. Create a new custom app in your Shopify Partner Dashboard
2. Set the App URL to: `https://shoppulse.vercel.app` 
3. Set the Allowed Redirection URL to: `https://shoppulse.vercel.app/api/auth/callback`
4. Add the GDPR webhooks:
   - Customer Data Request: `https://shoppulse.vercel.app/api/webhooks/customers/data_request`
   - Customer Redact: `https://shoppulse.vercel.app/api/webhooks/customers/redact`
   - Shop Redact: `https://shoppulse.vercel.app/api/webhooks/shop/redact`
5. Note your API key and API secret key

### Environment Variables

Create a `.env` file with the following variables:

```
SHOPIFY_API_KEY=your_shopify_api_key
SHOPIFY_API_SECRET=your_shopify_api_secret
APP_URL=https://shoppulse.vercel.app
SCOPES=read_products,write_products,read_customers,read_orders,write_orders
NODE_ENV=production
```

### Local Development

1. Clone this repository
2. Install dependencies: `npm install`
3. Set up your environment variables in `.env`
4. Start the development server: `npm run dev`
5. Use a tool like ngrok to expose your local server to test the OAuth flow

### Deployment to Vercel

1. Push your code to GitHub
2. Create a new project in Vercel and connect it to your GitHub repository
3. Set the environment variables in Vercel project settings
4. Deploy the app

## Project Structure

- `/api/index.js` - The main Express app with all API routes
- `/public/index.html` - Landing page with auto-redirect to OAuth
- `/public/dashboard/index.html` - Dashboard for authenticated users
- `/public/install.html` - App installation page
- `vercel.json` - Vercel configuration for routing

## Technical Details

This app implements the Shopify OAuth flow according to Shopify's requirements:

1. When a merchant visits the app, they're immediately redirected to authenticate
2. The app exchanges the authorization code for an access token
3. GDPR webhooks are registered upon installation
4. Once authenticated, merchants can access the dashboard

All routes are consolidated into a single serverless function in `api/index.js` to optimize for Vercel's Hobby plan limit of 12 serverless functions.

## License

MIT
