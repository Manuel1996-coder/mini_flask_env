# ShopPulseAI - Shopify Growth Analytics

This is a Flask-based Shopify app that provides analytics and growth insights for Shopify stores.

## Deployment on Railway

This application is configured for deployment on Railway. It uses:
- Flask for the web application
- Gunicorn as the WSGI server
- Flask-Session for session management
- Flask-CORS for cross-origin resource sharing

## Local Development

1. Clone this repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment: 
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run the application: `python app.py`

## Environment Variables

Create a `.env` file with the following variables:
```
SHOPIFY_API_KEY=your_api_key
SHOPIFY_API_SECRET=your_api_secret
APP_URL=your_app_url
OPENAI_API_KEY=your_openai_api_key
```

## Files

- `app.py`: Main application code
- `shopify_api.py`: Shopify API interactions
- `data_models.py`: Data models for analytics
- `growth_advisor.py`: Growth recommendation engine
- `wsgi.py`: WSGI entry point for production
- `Procfile`: Railway deployment configuration
