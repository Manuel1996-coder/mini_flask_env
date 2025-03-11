(function() {
    console.log("WIZARD AI TRACKING initialized");
    
    // Send pageview event
    function trackPageview() {
      fetch('https://miniflaskenv-production.up.railway.app/collect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: 'page_view',
          page_url: window.location.href,
          timestamp: new Date().toISOString()
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
        fetch('https://miniflaskenv-production.up.railway.app/collect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            event_type: 'click',
            page_url: window.location.href,
            clicked_tag: evt.target.tagName,
            timestamp: new Date().toISOString()
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