# ShopPulseAI

ShopPulseAI ist eine moderne Shopify-App, die KI-gestützte Wachstumsempfehlungen und Preisoptimierungen für Shopify-Händler bietet.

## Funktionen

- **Handlungsempfehlungen**: KI-gestützte, umsetzbare Wachstumsempfehlungen basierend auf Shopdaten
- **Preisoptimierung**: Intelligente Preisvorschläge für Produkte mit Begründung
- **Shopify-Integration**: Nahtlose Einbindung in den Shopify Admin-Bereich
- **Reaktives Dashboard**: Moderne UI mit React und Shopify Polaris

## Technologien

- **Frontend**: React, TypeScript, Emotion (CSS-in-JS), Shopify Polaris
- **Backend**: Node.js, Express, TypeScript
- **Datenbank**: SQLite (Entwicklung), PostgreSQL (Produktion)
- **AI**: OpenAI GPT-4o Integration
- **Authentifizierung**: Shopify OAuth 2.0
- **Deployment**: Railway

## Installation

### Voraussetzungen

- Node.js 18 oder höher
- Shopify Partner Account (für API-Schlüssel)
- OpenAI API-Schlüssel

### Einrichtung

1. Repository klonen:
   ```
   git clone https://github.com/yourusername/shoppulseai.git
   cd shoppulseai
   ```

2. Abhängigkeiten installieren:
   ```
   npm install
   ```

3. Umgebungsvariablen konfigurieren:
   - Kopiere `.env.example` zu `.env`
   - Ergänze deine API-Schlüssel und andere Konfigurationen

4. Entwicklungsserver starten:
   ```
   npm run dev
   ```

### Für Produktionsumgebung

1. Build erstellen:
   ```
   npm run build
   ```

2. Anwendung starten:
   ```
   npm start
   ```

3. Deployment auf Railway:
   ```
   npm run railway:up
   ```

## Projektstuktur

```
shoppulseai/
├── server/                   # Backend-Code
│   ├── auth.ts               # Authentifizierung
│   ├── webhooks.ts           # GDPR & andere Webhooks
│   ├── openai.ts             # OpenAI Integration
│   ├── routes.ts             # API-Endpunkte
│   └── index.ts              # Server-Entrypoint
├── frontend/                 # Frontend-Code
│   ├── src/
│   │   ├── components/       # React-Komponenten
│   │   ├── pages/            # Seitenkomponenten
│   │   ├── styles/           # CSS-Styles
│   │   ├── types/            # TypeScript-Definitionen
│   │   ├── App.tsx           # Haupt-App-Komponente
│   │   └── main.tsx          # Frontend-Entrypoint
│   └── public/               # Statische Assets
├── shopify.app.toml          # Shopify App-Konfiguration
└── tsconfig.json             # TypeScript-Konfiguration
```

## Fehlersuche

Bei roten Code-Markierungen in der IDE:

1. Prüfe, ob alle Abhängigkeiten installiert sind:
   ```
   npm install
   ```

2. TypeScript-Typprüfung ausführen:
   ```
   npm run typecheck
   ```

3. Linter-Fehler beheben:
   ```
   npm run lint
   ```

## Lizenz

MIT
