/**
 * Auth-Required.js
 * 
 * Stellt sicher, dass Benutzer authentifiziert sind, bevor sie mit der UI interagieren können.
 * Wenn keine Authentifizierung vorliegt, wird die UI blockiert und eine Weiterleitung zur 
 * OAuth-Seite angezeigt.
 */

(function() {
    // Test, ob Cookies aktiviert sind
    function areCookiesEnabled() {
        try {
            // Versuche, einen Test-Cookie zu setzen
            document.cookie = "test_cookie=1; path=/";
            const haveCookies = document.cookie.indexOf("test_cookie") !== -1;
            
            // Cookie wieder löschen
            document.cookie = "test_cookie=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
            
            return haveCookies;
        } catch (e) {
            console.error("Fehler beim Cookies-Test:", e);
            return false;
        }
    }
    
    // Funktion zum Überprüfen des Auth-Status
    async function checkAuthStatus() {
        try {
            console.log("Überprüfe Authentifizierungsstatus...");
            
            // Prüfe, ob Cookies aktiviert sind
            if (!areCookiesEnabled()) {
                console.error("Cookies sind deaktiviert - Authentifizierung funktioniert nicht ohne Cookies");
                showError("Cookies sind deaktiviert. Bitte aktiviere Cookies in deinem Browser, um diese App nutzen zu können.");
                return;
            }
            
            // Prüfe, ob wir uns auf einer Seite befinden, die keine Authentifizierung benötigt
            const currentPath = window.location.pathname;
            const exemptPaths = ['/install', '/auth/callback', '/oauth-error', '/error'];
            
            // Wenn wir auf einer ausgenommenen Seite sind, nicht prüfen
            if (exemptPaths.some(path => currentPath.startsWith(path))) {
                console.log("Seite erfordert keine Authentifizierung");
                return;
            }
            
            // Prüfen, ob wir uns in einer möglichen Weiterleitungsschleife befinden
            const redirectCount = parseInt(sessionStorage.getItem('redirect_count') || '0', 10);
            if (redirectCount > 5) {
                console.error("Zu viele Weiterleitungen erkannt, mögliche Schleife. Zeige Fehlermeldung an.");
                showError("Zu viele Weiterleitungen. Bitte lade die Seite neu oder versuche es später erneut.");
                return;
            }
            
            // Versuche, den Authorization-Header aus der lokalen Speicherung zu erhalten
            let authHeader = '';
            if (window.sessionStorage) {
                const storedToken = sessionStorage.getItem('shopify_token');
                if (storedToken) {
                    authHeader = `Bearer ${storedToken}`;
                    console.log("Token aus Session Storage verwendet");
                }
            }
            
            // API-Anfrage mit optionalem Bearer-Token
            const headers = new Headers();
            if (authHeader) {
                headers.append('Authorization', authHeader);
            }
            
            // Versuche, die Authentifizierung zu überprüfen
            const response = await fetch('/api/auth-check', {
                method: 'GET',
                headers: headers,
                credentials: 'include' // Cookies senden
            });
            
            if (!response.ok) {
                console.error(`Fehler bei der Authentifizierungsprüfung: ${response.status} ${response.statusText}`);
                throw new Error(`HTTP-Fehler: ${response.status}`);
            }
            
            const data = await response.json();
            
            console.log("Authentifizierungsantwort erhalten:", data);
            
            if (!data.authenticated) {
                console.log("Nicht authentifiziert, blockiere UI und leite weiter");
                
                // Erhöhe den Weiterleitungszähler
                sessionStorage.setItem('redirect_count', (redirectCount + 1).toString());
                
                // UI blockieren und Weiterleitung anzeigen
                blockUIAndRedirect(data.shop);
            } else {
                console.log("Authentifiziert, UI freigeben");
                
                // Setze den Weiterleitungszähler zurück
                sessionStorage.removeItem('redirect_count');
                
                // Ggf. UI Elemente aktualisieren
                if (data.shop) {
                    console.log(`Authentifiziert für Shop: ${data.shop}`);
                    // Hier könnte man den Shop-Namen in der UI anzeigen
                }
            }
        } catch (error) {
            console.error("Fehler bei der Authentifizierungsprüfung:", error);
            
            // Bei Netzwerkfehlern oder anderen Problemen UI nicht blockieren
            // sondern nur eine Fehlermeldung anzeigen
            if (error.name === 'TypeError' || error.name === 'NetworkError') {
                showError("Verbindungsproblem bei der Authentifizierungsprüfung. Bitte später erneut versuchen.");
            } else {
                // Im Zweifelsfall UI blockieren
                blockUIAndRedirect();
            }
        }
    }
    
    // Zeigt eine Fehlermeldung an, ohne die UI zu blockieren
    function showError(message) {
        // Erstelle ein Fehler-Banner oben auf der Seite
        const errorBanner = document.createElement('div');
        errorBanner.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            background-color: #f8d7da;
            color: #721c24;
            padding: 12px;
            text-align: center;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            z-index: 10000;
            border-bottom: 1px solid #f5c6cb;
        `;
        errorBanner.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span>${message}</span>
                <button style="background: transparent; border: none; color: #721c24; cursor: pointer; font-size: 1.5rem;">&times;</button>
            </div>
        `;
        document.body.prepend(errorBanner);
        
        // Event-Listener zum Schließen des Banners
        errorBanner.querySelector('button').addEventListener('click', () => {
            errorBanner.remove();
        });
    }
    
    // Funktion zum Blockieren der UI und Weiterleiten zur Authentifizierung
    function blockUIAndRedirect(shop = null) {
        // Overlay erstellen, das die gesamte Seite abdeckt
        const overlay = document.createElement('div');
        overlay.id = 'auth-required-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(255, 255, 255, 0.9);
            z-index: 10000;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
        `;
        
        // Inhalt des Overlays
        overlay.innerHTML = `
            <div style="text-align: center; max-width: 400px; padding: 20px; background-color: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <h2 style="color: #2c6ecb; margin-bottom: 1rem;">Authentifizierung erforderlich</h2>
                <p style="margin-bottom: 1.5rem;">Um diese App nutzen zu können, musst du dich zuerst authentifizieren.</p>
                <button id="auth-redirect-btn" style="background-color: #2c6ecb; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: 500;">
                    Jetzt authentifizieren
                </button>
            </div>
        `;
        
        // Overlay an DOM anhängen
        document.body.appendChild(overlay);
        
        // Event-Listener für Button hinzufügen
        document.getElementById('auth-redirect-btn').addEventListener('click', function() {
            // Shop-Parameter aus der URL, übergebenen Parameter oder Session extrahieren
            const urlParams = new URLSearchParams(window.location.search);
            const shopParam = shop || urlParams.get('shop');
            
            if (shopParam) {
                window.location.href = `/install?shop=${shopParam}`;
            } else {
                // Wenn kein Shop-Parameter vorhanden ist, zur allgemeinen Install-Seite weiterleiten
                window.location.href = '/install';
            }
        });
    }
    
    // Führe die Authentifizierungsprüfung durch
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', checkAuthStatus);
    } else {
        checkAuthStatus();
    }
})(); 