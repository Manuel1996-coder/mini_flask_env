/**
 * Auth-Required.js
 * 
 * Stellt sicher, dass Benutzer authentifiziert sind, bevor sie mit der UI interagieren können.
 * Wenn keine Authentifizierung vorliegt, wird die UI blockiert und eine Weiterleitung zur 
 * OAuth-Seite angezeigt.
 */

(function() {
    // Funktion zum Überprüfen des Auth-Status
    async function checkAuthStatus() {
        try {
            console.log("Überprüfe Authentifizierungsstatus...");
            
            // Prüfe, ob wir uns auf einer Seite befinden, die keine Authentifizierung benötigt
            const currentPath = window.location.pathname;
            const exemptPaths = ['/install', '/auth/callback', '/oauth-error', '/error'];
            
            // Wenn wir auf einer ausgenommenen Seite sind, nicht prüfen
            if (exemptPaths.some(path => currentPath.startsWith(path))) {
                console.log("Seite erfordert keine Authentifizierung");
                return;
            }
            
            // Versuche, die Authentifizierung zu überprüfen
            const response = await fetch('/api/auth-check');
            const data = await response.json();
            
            if (!data.authenticated) {
                console.log("Nicht authentifiziert, blockiere UI und leite weiter");
                blockUIAndRedirect();
            } else {
                console.log("Authentifiziert, UI freigeben");
                // UI ist bereits verfügbar, nichts zu tun
            }
        } catch (error) {
            console.error("Fehler bei der Authentifizierungsprüfung:", error);
            // Im Zweifelsfall UI blockieren
            blockUIAndRedirect();
        }
    }
    
    // Funktion zum Blockieren der UI und Weiterleiten zur Authentifizierung
    function blockUIAndRedirect() {
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
            <div style="text-align: center; max-width: 400px; padding: 20px;">
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
            // Shop-Parameter aus der URL oder Session extrahieren
            const urlParams = new URLSearchParams(window.location.search);
            const shop = urlParams.get('shop');
            
            if (shop) {
                window.location.href = `/install?shop=${shop}`;
            } else {
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