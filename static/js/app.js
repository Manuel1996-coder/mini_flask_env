// ShopPulseAI Haupt-JS-Datei

document.addEventListener('DOMContentLoaded', function() {
    console.log('ShopPulseAI App geladen');
    
    // Dashboard-Daten initialisieren
    initializeGlobalData();
    
    // Link-Handler für eingebettete Shopify-Apps
    handleAppLinks();
    
    // Cookie-Prüfung für Chrome's Third-Party Cookie-Einschränkungen
    checkCookieSupport();
});

// Initialisiert globale Daten aus dem DOM
function initializeGlobalData() {
    // Dashboard-Daten aus dem versteckten Element extrahieren
    const dataElement = document.getElementById('dashboard-data');
    
    if (dataElement) {
        try {
            // Sicheres JSON-Parsing mit Validierung
            const safeJsonParse = (jsonString, defaultValue) => {
                if (!jsonString || jsonString.trim() === '') {
                    return defaultValue;
                }
                try {
                    return JSON.parse(jsonString);
                } catch (error) {
                    console.error('JSON-Parsing-Fehler:', error, 'für String:', jsonString);
                    return defaultValue;
                }
            };
            
            window.dashboardData = {
                trafficDates: safeJsonParse(dataElement.dataset.trafficDates, []),
                trafficData: safeJsonParse(dataElement.dataset.trafficData, {}),
                deviceData: safeJsonParse(dataElement.dataset.deviceData, [])
            };
            console.log('Dashboard-Daten geladen:', window.dashboardData);
        } catch (error) {
            console.error('Fehler beim Laden der Dashboard-Daten:', error);
            // Standardwerte setzen
            window.dashboardData = {
                trafficDates: ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
                trafficData: {
                    pageviews: [450, 520, 480, 630, 580, 520, 680],
                    visitors: [320, 380, 350, 450, 420, 380, 480]
                },
                deviceData: [45, 40, 15]
            };
        }
    }
}

// Verarbeitet interne Links für eingebettete Apps
function handleAppLinks() {
    // Prüfen, ob wir in einem iFrame sind (eingebettete App)
    const isInIframe = window.self !== window.top;
    
    // AppBridge ist verfügbar
    const hasAppBridge = window.shopify && window.shopify.getSessionToken;
    
    // Handle interne Links
    document.addEventListener('click', function(event) {
        // Link finden, wenn auf den Link oder ein Element innerhalb des Links geklickt wurde
        let link = event.target;
        while (link && link.tagName !== 'A') {
            link = link.parentElement;
            if (!link) break;
        }
        
        // Wenn kein Link gefunden wurde oder es ein externer Link ist, normal fortfahren
        if (!link || link.getAttribute('target') === '_blank' || link.getAttribute('href').startsWith('http')) {
            return;
        }
        
        // Interner Link gefunden
        const href = link.getAttribute('href');
        
        // Wenn wir in einem iFrame sind und AppBridge verfügbar ist, versuchen wir Redirect zu verhindern
        if (isInIframe && hasAppBridge) {
            event.preventDefault();
            
            // Aktuelle URL-Parameter beibehalten (shop, host)
            const currentUrl = new URL(window.location.href);
            const shop = currentUrl.searchParams.get('shop');
            const host = currentUrl.searchParams.get('host');
            
            // Neue URL mit Parametern erstellen
            let newUrl = href;
            const separator = href.includes('?') ? '&' : '?';
            
            if (shop) {
                newUrl += `${separator}shop=${shop}`;
            }
            
            if (host) {
                newUrl += `&host=${host}`;
            }
            
            console.log(`App-interne Navigation zu: ${newUrl}`);
            window.location.href = newUrl;
        }
    });
}

// Prüft Cookie-Unterstützung und zeigt Warnungen für Third-Party Cookie-Einschränkungen
function checkCookieSupport() {
    // Test-Cookie setzen
    const testCookieName = 'shopify_app_cookie_test';
    document.cookie = `${testCookieName}=1; path=/; SameSite=None; Secure`;
    
    // Prüfen, ob der Cookie gesetzt wurde
    const cookieEnabled = document.cookie.indexOf(testCookieName) !== -1;
    
    // User-Agent prüfen für Chrome
    const isChrome = navigator.userAgent.indexOf('Chrome') !== -1;
    
    // Wenn Cookies nicht funktionieren und wir in Chrome sind, Warnung anzeigen
    if (!cookieEnabled && isChrome) {
        console.warn('⚠️ Cookies funktionieren nicht - möglicherweise aufgrund von Chrome Third-Party Cookie-Einschränkungen');
        
        // Prüfen, ob wir in einem iFrame sind
        const isInIframe = window.self !== window.top;
        
        if (isInIframe) {
            // Warnung anzeigen für eingebettete Apps
            showCookieWarning();
        }
    } else {
        console.log('✅ Cookie-Test erfolgreich - Cookies funktionieren');
    }
}

// Zeigt eine Warnung über Third-Party Cookie-Einschränkungen an
function showCookieWarning() {
    // Nachricht nur einmal anzeigen (über Session Storage)
    if (sessionStorage.getItem('cookie_warning_shown')) {
        return;
    }
    
    // Warnung erstellen
    const warningElement = document.createElement('div');
    warningElement.style.cssText = 'position: fixed; bottom: 20px; right: 20px; background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 15px; border-radius: 5px; max-width: 400px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); z-index: 1000;';
    warningElement.innerHTML = `
        <div style="font-weight: bold; margin-bottom: 10px;">Chrome Cookie-Einschränkungen</div>
        <p style="margin: 0 0 10px 0;">Chrome blockiert möglicherweise Cookies für diese App. Dies kann zu Problemen bei der Authentifizierung führen.</p>
        <div style="display: flex; justify-content: space-between;">
            <a href="/cookie-hilfe" style="background: #0275d8; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; text-decoration: none;">Mehr erfahren</a>
            <button id="cookieClose" style="background: #721c24; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">Schließen</button>
        </div>
        <div style="clear: both;"></div>
    `;
    
    // Zur Seite hinzufügen
    document.body.appendChild(warningElement);
    
    // Schließen-Button-Handler
    document.getElementById('cookieClose').addEventListener('click', function() {
        document.body.removeChild(warningElement);
        sessionStorage.setItem('cookie_warning_shown', 'true');
    });
} 