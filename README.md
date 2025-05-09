# Minimale Shopify App

Diese App ist eine minimale Implementierung einer Shopify-App, die nur die wesentlichen Funktionen enthält, um die Anforderungen des App Stores zu erfüllen.

## Funktionen

- OAuth-Authentifizierung mit Shopify
- App Bridge Integration (eingebetteter Modus)
- Minimales Dashboard nach erfolgreicher Authentifizierung

## Struktur

- `api/index.js` - Express-Server mit OAuth-Routen
- `public/embedded.html` - Einstiegspunkt für Shopify
- `public/dashboard.html` - Dashboard nach erfolgreicher Auth
- `vercel.json` - Vercel-Konfiguration

## Einrichtung

1. Klone dieses Repository
2. Erstelle eine `.env` Datei mit folgenden Variablen:
   ```
   SHOPIFY_API_KEY=your_api_key_here
   SHOPIFY_API_SECRET=your_api_secret_here
   APP_URL=https://your-app-url.vercel.app
   SCOPES=read_products,write_products
   ```
3. Installiere Abhängigkeiten: `npm install`
4. In der Shopify Partner-Dashboard:
   - App URL: `https://your-app-url.vercel.app/embedded`
   - Allowed redirection URL: `https://your-app-url.vercel.app/api/auth/callback`

## Deployment auf Vercel

```bash
vercel
```

## Lokale Entwicklung

```bash
npm install
vercel dev
```
