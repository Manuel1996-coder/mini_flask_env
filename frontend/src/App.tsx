import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import {
  AppProvider,
  NavigationMenu,
} from '@shopify/app-bridge-react';
import { PolarisProvider } from '@shopify/polaris';
import '@shopify/polaris/build/esm/styles.css';
import enTranslations from '@shopify/polaris/locales/en.json';
import Dashboard from './pages/Dashboard';

function App() {
  // Get query parameters for Shopify app
  const queryParams = new URLSearchParams(window.location.search);
  const shop = queryParams.get('shop');
  const host = queryParams.get('host');
  
  // If no shop or host, redirect to Shopify
  if (!shop || !host) {
    // In a real app, this would redirect to a missing params page or error page
    return <div>Missing shop or host parameters</div>;
  }
  
  // Shopify App configuration
  const config = {
    apiKey: process.env.SHOPIFY_API_KEY || '',
    host: host,
    forceRedirect: true,
  };
  
  return (
    <PolarisProvider i18n={enTranslations}>
      <AppProvider config={config}>
        <Router>
          <Routes>
            {/* Main dashboard route */}
            <Route path="/dashboard" element={<Dashboard />} />
            
            {/* Redirect root to dashboard */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            
            {/* Fallback route - redirects to dashboard */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
          
          {/* Shopify navigation menu */}
          <NavigationMenu
            navigationLinks={[
              {
                label: 'Dashboard',
                destination: '/dashboard',
              },
            ]}
          />
        </Router>
      </AppProvider>
    </PolarisProvider>
  );
}

export default App; 