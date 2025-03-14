(function() {
    console.log("WIZARD AI TRACKING initialized");
    
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
        }
        return sessionId;
    }
    
    const sessionId = getSessionId();
    
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
    console.log("Using base URL for tracking:", baseUrl);
    
    // Send pageview event
    function trackPageview() {
      fetch(baseUrl + '/collect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: 'page_view',
          page_url: window.location.href,
          page: window.location.pathname,
          timestamp: Date.now(),
          session_id: sessionId
        }),
        mode: 'cors'
      })
      .then(response => {
        if (response.ok) console.log("Pageview tracked successfully");
        else console.error("Pageview tracking failed:", response.status);
      })
      .catch(err => console.error('Pageview tracking failed:', err));
    }
    
    // Send click event
    function setupClickTracking() {
      document.addEventListener('click', function(evt) {
        fetch(baseUrl + '/collect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            event_type: 'click',
            page_url: window.location.href,
            page: window.location.pathname,
            clicked_tag: evt.target.tagName,
            timestamp: Date.now(),
            session_id: sessionId
          }),
          mode: 'cors'
        })
        .then(response => {
          if (response.ok) console.log("Click tracked successfully");
          else console.error("Click tracking failed:", response.status);
        })
        .catch(err => console.error('Click tracking failed:', err));
      });
    }
    
    // Wait for DOM to be fully loaded
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function() {
        trackPageview();
        setupClickTracking();
      });
    } else {
      trackPageview();
      setupClickTracking();
    }
  })();