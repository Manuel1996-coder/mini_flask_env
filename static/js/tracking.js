(function() {
    console.log("WIZARD AI TRACKING initialized - Debug Version");
    
    // Generiere eine eindeutige Session-ID
    function generateSessionId() {
        return 'session_' + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    }
    
    // Hole oder erstelle Session-ID
    function getSessionId() {
        let sessionId = localStorage.getItem('wizard_ai_session_id');
        if (!sessionId) {
            sessionId = generateSessionId();
            localStorage.setItem('wizard_ai_session_id', sessionId);
            console.log("🆕 Neue Session ID generiert:", sessionId);
        }
        return sessionId;
    }
    
    const sessionId = getSessionId();
    console.log("🔑 Session ID:", sessionId);
    
    // Shopify-Shop prüfen
    if (typeof Shopify === 'undefined' || !Shopify.shop) {
        console.error("❌ FEHLER: Shopify-Objekt nicht gefunden. Tracking wird nicht funktionieren!");
        console.log("🔍 Window-Objekte:", Object.keys(window).filter(key => key.includes('shop')));
        // Manuelles Fallback - nur für Debug-Zwecke
        window.Shopify = window.Shopify || { shop: 'test-shop.example.com' };
        console.log("⚠️ Fallback-Shop gesetzt:", window.Shopify.shop);
    } else {
        console.log("✅ Shopify Shop erkannt:", Shopify.shop);
    }
    
    // Bestimme die Basis-URL basierend auf der aktuellen Umgebung
    function getBaseUrl() {
        // Wenn wir lokal sind, verwende die lokale URL
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            return window.location.origin;
        }
        // Ansonsten verwende die Railway-URL
        return 'https://miniflaskenv-production.up.railway.app';
    }
    
    const baseUrl = getBaseUrl();
    console.log("🌐 Using base URL for tracking:", baseUrl);
    
    // Send pageview event
    function trackPageview() {
      const data = {
        event_type: 'page_view',
        page_url: window.location.href,
        page: window.location.pathname,
        timestamp: Date.now(),
        session_id: sessionId,
        shop_domain: Shopify.shop
      };
      
      console.log("📊 Sending pageview data:", data);
      
      fetch(baseUrl + '/collect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
        mode: 'cors'
      })
      .then(response => {
        if (response.ok) {
          console.log("✅ Pageview tracked successfully");
          return response.json();
        } else {
          console.error("❌ Pageview tracking failed:", response.status);
          // Zusätzliches Debugging
          response.text().then(text => {
            console.error("Response Text:", text);
          });
          throw new Error("Pageview tracking failed: " + response.status);
        }
      })
      .then(data => {
        console.log("🔄 Server response:", data);
      })
      .catch(err => {
        console.error('❌ Pageview tracking failed:', err);
      });
    }
    
    // Send click event
    function setupClickTracking() {
      document.addEventListener('click', function(evt) {
        const data = {
          event_type: 'click',
          page_url: window.location.href,
          page: window.location.pathname,
          clicked_tag: evt.target.tagName,
          timestamp: Date.now(),
          session_id: sessionId,
          shop_domain: Shopify.shop
        };
        
        console.log("👆 Sending click data:", data);
        
        fetch(baseUrl + '/collect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
          mode: 'cors'
        })
        .then(response => {
          if (response.ok) {
            console.log("✅ Click tracked successfully");
            return response.json();
          } else {
            console.error("❌ Click tracking failed:", response.status);
            // Zusätzliches Debugging
            response.text().then(text => {
              console.error("Response Text:", text);
            });
            throw new Error("Click tracking failed: " + response.status);
          }
        })
        .then(data => {
          console.log("🔄 Server response:", data);
        })
        .catch(err => {
          console.error('❌ Click tracking failed:', err);
        });
      });
    }
    
    // Füge manuelles Tracking für Testzwecke hinzu
    window.manualTrack = function(eventType) {
      console.log("🧪 Manual tracking requested:", eventType);
      
      if (eventType === 'pageview') {
        trackPageview();
      } else if (eventType === 'click') {
        const data = {
          event_type: 'click',
          page_url: window.location.href,
          page: window.location.pathname,
          clicked_tag: 'MANUAL',
          timestamp: Date.now(),
          session_id: sessionId,
          shop_domain: Shopify.shop
        };
        
        console.log("🔧 Sending manual click data:", data);
        
        fetch(baseUrl + '/collect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
          mode: 'cors'
        })
        .then(response => {
          if (response.ok) {
            console.log("✅ Manual click tracked successfully");
            return response.json();
          } else {
            console.error("❌ Manual click tracking failed:", response.status);
            // Zusätzliches Debugging
            response.text().then(text => {
              console.error("Response Text:", text);
            });
            throw new Error("Manual click tracking failed: " + response.status);
          }
        })
        .then(data => {
          console.log("🔄 Server response:", data);
        })
        .catch(err => {
          console.error('❌ Manual click tracking failed:', err);
        });
      }
    };
    
    // Testet den Status der Verbindung zum Server
    function testServerConnection() {
      console.log("🔄 Testing server connection...");
      fetch(baseUrl + '/ping', { mode: 'cors' })
        .then(response => {
          if (response.ok) {
            console.log("✅ Server is reachable");
            return response.text();
          } else {
            console.warn("⚠️ Server responded with status:", response.status);
            throw new Error("Server responded with status: " + response.status);
          }
        })
        .then(data => {
          console.log("📡 Server response:", data);
        })
        .catch(err => {
          console.error("❌ Cannot reach server:", err);
          console.log("⚙️ Will try to continue tracking anyway");
        });
    }
    
    // Testen der Verbindung
    testServerConnection();
    
    // Wait for DOM to be fully loaded
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function() {
        console.log("📄 DOM fully loaded, initializing tracking");
        trackPageview();
        setupClickTracking();
      });
    } else {
      console.log("📄 DOM already loaded, initializing tracking");
      trackPageview();
      setupClickTracking();
    }
    
    console.log("✅ WIZARD AI TRACKING setup complete");
  })();