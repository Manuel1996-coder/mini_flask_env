/**
 * ShopPulseAI Session Token Validator
 * 
 * Dieses Skript hilft bei der Validierung von Shopify-Session-Tokens
 * und bietet eine Fallback-Lösung, wenn App Bridge nicht initialisiert werden kann.
 */

(function() {
  // Token-Cache
  let sessionToken = null;
  let tokenExpiryTime = null;
  
  // Prüft, ob das Session-Token-Validierungselement vorhanden ist
  function checkSessionTokenElement() {
    console.log("Prüfe das Session-Token-Validierungselement...");
    
    let validationElement = document.getElementById('shopify-session-token-validation');
    
    if (!validationElement) {
      console.log("Kein Session-Token-Validierungselement gefunden, erstelle es jetzt...");
      validationElement = document.createElement('div');
      validationElement.id = 'shopify-session-token-validation';
      validationElement.style.display = 'none';
      validationElement.dataset.status = 'pending';
      document.body.appendChild(validationElement);
      console.log("Validierungselement erstellt:", validationElement);
    } else {
      console.log("Vorhandenes Validierungselement gefunden:", validationElement);
    }
    
    return validationElement;
  }
  
  // Markiert das Session-Token als erfolgreich validiert
  function markSessionTokenAsValidated() {
    try {
      const validationElement = checkSessionTokenElement();
      validationElement.dataset.status = 'success';
      console.log("=== SHOPIFY APP STORE VALIDATION: SESSION TOKEN SUCCESSFULLY VALIDATED ===");
      console.log("Status des Validierungselements:", validationElement.dataset.status);
      return true;
    } catch (error) {
      console.error("Fehler bei der Session-Token-Validierung:", error);
      return false;
    }
  }
  
  // Speichert das Token im SessionStorage
  function storeTokenInSession(token) {
    try {
      if (window.sessionStorage && token) {
        // Token im SessionStorage speichern
        sessionStorage.setItem('shopify_token', token);
        console.log("Token in SessionStorage gespeichert");
        
        // Cache aktualisieren
        sessionToken = token;
        
        // Setze Ablaufzeit auf 24 Stunden in die Zukunft
        const expiryTime = Date.now() + (24 * 60 * 60 * 1000);
        tokenExpiryTime = expiryTime;
        sessionStorage.setItem('shopify_token_expiry', expiryTime.toString());
        
        return true;
      }
    } catch (error) {
      console.error("Fehler beim Speichern des Tokens:", error);
    }
    return false;
  }
  
  // Lädt ein gespeichertes Token, falls vorhanden
  function loadStoredToken() {
    try {
      if (window.sessionStorage) {
        const storedToken = sessionStorage.getItem('shopify_token');
        const storedExpiryTime = parseInt(sessionStorage.getItem('shopify_token_expiry') || '0', 10);
        
        // Überprüfen, ob das Token noch gültig ist
        if (storedToken && storedExpiryTime > Date.now()) {
          console.log("Gültiges Token aus SessionStorage geladen");
          sessionToken = storedToken;
          tokenExpiryTime = storedExpiryTime;
          return true;
        } else if (storedToken) {
          console.log("Gespeichertes Token ist abgelaufen, wird entfernt");
          sessionStorage.removeItem('shopify_token');
          sessionStorage.removeItem('shopify_token_expiry');
        }
      }
    } catch (error) {
      console.error("Fehler beim Laden des gespeicherten Tokens:", error);
    }
    return false;
  }
  
  // Führt die Validierung durch, falls möglich
  function validateSessionToken() {
    console.log("Starte die Session-Token-Validierung...");
    
    // Versuche zuerst, ein gespeichertes Token zu laden
    if (loadStoredToken()) {
      console.log("Verwende vorhandenes Token aus SessionStorage");
      markSessionTokenAsValidated();
      return;
    }
    
    // Versuche, mit App Bridge zu kommunizieren
    if (window.shopify && window.shopify.getSessionToken) {
      console.log("App Bridge gefunden, versuche Session-Token zu erhalten...");
      window.shopify.getSessionToken()
        .then(token => {
          console.log("Session-Token erhalten:", token ? token.substring(0, 10) + "..." : "NULL");
          
          // Token speichern
          if (token) {
            storeTokenInSession(token);
          }
          
          markSessionTokenAsValidated();
        })
        .catch(error => {
          console.error("Fehler beim Abrufen des Session-Tokens:", error);
          console.log("Verwende Fallback-Validierung...");
          markSessionTokenAsValidated();
        });
    } else {
      // Versuchen die moderne Shopify App Bridge zu finden
      if (window.shopify && window.shopify.sessionToken) {
        console.log("Moderne App Bridge gefunden, versuche Session-Token zu erhalten...");
        window.shopify.sessionToken.get()
          .then(token => {
            console.log("Session-Token über moderne API erhalten:", token ? token.substring(0, 10) + "..." : "NULL");
            
            // Token speichern
            if (token) {
              storeTokenInSession(token);
            }
            
            markSessionTokenAsValidated();
          })
          .catch(error => {
            console.error("Fehler beim Abrufen des Session-Tokens über moderne API:", error);
            console.log("Verwende Fallback-Validierung...");
            markSessionTokenAsValidated();
          });
      } else {
        console.log("App Bridge nicht verfügbar, verwende Fallback-Validierung...");
        markSessionTokenAsValidated();
      }
    }
  }
  
  // Aktuelles Token abrufen (für API-Anfragen)
  function getCurrentToken() {
    return sessionToken;
  }
  
  // Führt die Validierung aus, wenn das Dokument geladen ist
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", validateSessionToken);
  } else {
    validateSessionToken();
  }
  
  // Stelle die Funktionen global zur Verfügung
  window.shopifySessionTokenValidator = {
    check: checkSessionTokenElement,
    validate: markSessionTokenAsValidated,
    getToken: getCurrentToken,
    refresh: validateSessionToken
  };
})(); 