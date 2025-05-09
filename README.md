# ShopPulseAI - Shopify App

Eine moderne TypeScript/React-Anwendung für Shopify, die intelligente Produktempfehlungen und Preisoptimierungen bietet.

## Funktionen

- 🤖 AI-gestützte Produktempfehlungen
- 💰 Automatische Preisoptimierung
- 📊 Datengetriebene Entscheidungsfindung
- 🔒 Shopify App Bridge Integration

## Tech-Stack

- **Frontend**: React, TypeScript, Shopify Polaris
- **Backend**: Node.js mit Express
- **Serverless**: Vercel Serverless Functions
- **Shopify Integration**: App Bridge, GraphQL API
- **AI**: OpenAI Integration

## Entwicklung

1. Klonen Sie das Repository:
```bash
git clone https://github.com/yourusername/shoppulseai.git
cd shoppulseai
```

2. Installieren Sie die Abhängigkeiten:
```bash
npm install
```

3. Erstellen Sie eine `.env`-Datei mit den benötigten Umgebungsvariablen:
```
SHOPIFY_API_KEY=your_api_key
SHOPIFY_API_SECRET=your_api_secret
OPENAI_API_KEY=your_openai_api_key
SCOPES=write_products,read_products,read_orders,write_orders
```

4. Starten Sie die Entwicklungsumgebung:
```bash
npm run dev
```

## Bereitstellung auf Vercel

Diese App ist für eine Bereitstellung auf Vercel optimiert.

1. Erstellen Sie ein Konto auf [Vercel](https://vercel.com)
2. Installieren Sie die Vercel CLI:
```bash
npm install -g vercel
```

3. Loggen Sie sich ein:
```bash
vercel login
```

4. Führen Sie die Bereitstellung durch:
```bash
vercel
```

5. Für Produktionsbereitstellungen:
```bash
vercel --prod
```

## Umgebungsvariablen in Vercel

Stellen Sie sicher, dass Sie die folgenden Umgebungsvariablen in Ihrem Vercel-Projekt einrichten:

- `SHOPIFY_API_KEY`
- `SHOPIFY_API_SECRET`
- `OPENAI_API_KEY`
- `SCOPES`
- `NODE_ENV` (sollte auf `production` gesetzt sein)

## Struktur der Serverless-Funktionen

Die App verwendet Vercel Serverless Functions für die Backend-Logik:

- `/api/index.js` - Hauptendpunkt, der alle Routen bereitstellt
- `/api/products.js` - Produktabfragen
- `/api/recommendations.js` - AI-gestützte Empfehlungen
- `/api/price-optimize.js` - Preisoptimierungen

## Lizenz

MIT

## Shopify App Compliance

Die App erfüllt alle Anforderungen für die Shopify App Store Einreichung:

### OAuth-Authentifizierung
- Vollständiger OAuth-Flow mit Shopify
- Sichere HMAC-Validierung der Anfragen
- Ordnungsgemäße Behandlung von Zugriffstoken

### Session Tokens
- Integration mit App Bridge für Authentifizierung
- Verwendung von Session Tokens für alle API-Anfragen
- Eingebettete App-Funktionalität mit korrektem Token-Handling

### GDPR-Compliance Webhooks
- Implementierung aller erforderlichen GDPR-Webhooks:
  - `customers/data_request`
  - `customers/redact`
  - `shop/redact`
- Automatische Registrierung der Webhooks bei App-Installation
- HMAC-Validierung für alle Webhook-Anfragen

### Sicherheit
- TLS-Verschlüsselung für alle Verbindungen
- Sichere Cookie-Einstellungen (HttpOnly, Secure, SameSite)
- CORS-Konfiguration für sichere API-Anfragen

## Lokale Entwicklung

```
npm install
npm run dev
```

## Deployment auf Vercel

```
vercel deploy --prod
```

## Umgebungsvariablen

Erstellen Sie eine `.env`-Datei mit den folgenden Variablen:

```
SHOPIFY_API_KEY=your_shopify_api_key
SHOPIFY_API_SECRET=your_shopify_api_secret
APP_URL=https://your-app-url.vercel.app
```

## Wichtige URLs

- App-URL: https://mini-flask-env.vercel.app
- OAuth-Callback: https://mini-flask-env.vercel.app/api/auth/callback
- Webhook-URLs:
  - https://mini-flask-env.vercel.app/api/webhooks/customers/data_request
  - https://mini-flask-env.vercel.app/api/webhooks/customers/redact
  - https://mini-flask-env.vercel.app/api/webhooks/shop/redact
