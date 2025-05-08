/**
 * ShopPulseAI - Modern UI Components
 * Stellt erweiterte UI-Komponenten und Interaktionen für eine verbesserte Benutzeroberfläche bereit
 */

// Globales Namespace für ShopPulseAI
window.ShopPulseAI = window.ShopPulseAI || {};

// UI-Module
ShopPulseAI.UI = (function() {
  'use strict';
  
  // Cache DOM-Selektoren für häufig verwendete Elemente
  const DOM = {
    body: document.body,
    sidebar: document.querySelector('.sidebar'),
    content: document.querySelector('.content'),
    charts: document.querySelectorAll('.chart-container'),
    kpiCards: document.querySelectorAll('.kpi-card')
  };
  
  /**
   * Initialisiert alle UI-Komponenten
   */
  function init() {
    initSidebarToggle();
    initTooltips();
    initCharts();
    initDataRefresh();
    initSkeletonLoaders();
    initMobileResponsiveness();
    initAnimations();
    initErrorHandlers();
    
    // Event-Listener für dynamische Komponenten hinzufügen
    window.addEventListener('resize', handleResize);
    document.addEventListener('DOMContentLoaded', onDOMReady);
    
    console.log('ShopPulseAI UI erfolgreich initialisiert');
  }
  
  /**
   * Initialisiert die Seitenleitenfunktionalität für mobile Geräte
   */
  function initSidebarToggle() {
    const sidebarToggle = document.createElement('button');
    sidebarToggle.className = 'sidebar-toggle';
    sidebarToggle.innerHTML = '<i class="fas fa-bars"></i>';
    sidebarToggle.setAttribute('aria-label', 'Seitenleiste umschalten');
    
    // Füge den Toggle-Button zum Header hinzu
    const header = document.querySelector('header');
    if (header) {
      const container = header.querySelector('.container-fluid');
      if (container) {
        container.prepend(sidebarToggle);
      } else {
        // Fallback: Falls kein Container gefunden wird, füge es direkt zum Header hinzu
        header.prepend(sidebarToggle);
      }
    } else {
      // Fallback: Wenn kein Header gefunden wurde, füge es zum Body hinzu
      const body = document.querySelector('body');
      if (body) {
        body.insertAdjacentElement('afterbegin', sidebarToggle);
      }
      console.warn('Header für Sidebar-Toggle nicht gefunden, verwende Fallback');
    }
    
    // Überprüfe, ob DOM.sidebar existiert, bevor wir es verwenden
    if (!DOM.sidebar) {
      console.warn('Sidebar-Element nicht gefunden, Sidebar-Funktionalität deaktiviert');
      return;
    }
    
    // Event-Listener für Seitenleisten-Toggle
    sidebarToggle.addEventListener('click', function() {
      DOM.sidebar.classList.toggle('open');
      this.setAttribute('aria-expanded', DOM.sidebar.classList.contains('open'));
    });
    
    // Schließe die Seitenleiste, wenn außerhalb geklickt wird
    document.addEventListener('click', function(event) {
      if (!DOM.sidebar) return;
      const isClickInside = DOM.sidebar.contains(event.target) || sidebarToggle.contains(event.target);
      if (!isClickInside && DOM.sidebar.classList.contains('open')) {
        DOM.sidebar.classList.remove('open');
        sidebarToggle.setAttribute('aria-expanded', 'false');
      }
    });
  }
  
  /**
   * Initialisiert Tooltips für Informationen
   */
  function initTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    
    tooltipElements.forEach(element => {
      const tooltipText = element.getAttribute('data-tooltip');
      const tooltipContent = document.createElement('span');
      tooltipContent.className = 'tooltip-content';
      tooltipContent.textContent = tooltipText;
      
      element.classList.add('tooltip');
      element.appendChild(tooltipContent);
    });
  }
  
  /**
   * Optimiert die Charts und stellt sicher, dass sie responsiv sind
   */
  function initCharts() {
    if (typeof Chart !== 'undefined') {
      // Globale Chart.js-Optionen für einheitliches Styling
      Chart.defaults.font.family = getComputedStyle(document.body).getPropertyValue('--font-family');
      Chart.defaults.color = getComputedStyle(document.body).getPropertyValue('--gray-600');
      Chart.defaults.elements.line.borderWidth = 2;
      Chart.defaults.elements.point.radius = 3;
      Chart.defaults.elements.point.hoverRadius = 4;
      Chart.defaults.plugins.tooltip.backgroundColor = getComputedStyle(document.body).getPropertyValue('--gray-800');
      Chart.defaults.plugins.tooltip.padding = 10;
      Chart.defaults.plugins.tooltip.cornerRadius = 4;
      Chart.defaults.responsive = true;
      Chart.defaults.maintainAspectRatio = false;
      
      // Fallback für Chart.js-Fehler hinzufügen
      DOM.charts.forEach(container => {
        const canvas = container.querySelector('canvas');
        if (canvas) {
          canvas.addEventListener('error', function() {
            handleChartError(container);
          });
        }
      });
    }
  }
  
  /**
   * Initialisiert Mechanismen zur Aktualisierung von Daten
   */
  function initDataRefresh() {
    // Finde alle Refresh-Buttons
    const refreshButtons = document.querySelectorAll('.refresh-btn');
    
    refreshButtons.forEach(button => {
      button.addEventListener('click', function(e) {
        e.preventDefault();
        
        // Finde den zugehörigen Datencontainer
        const targetId = this.getAttribute('data-target');
        const targetContainer = targetId ? document.getElementById(targetId) : this.closest('.card, .chart-container');
        
        if (targetContainer) {
          refreshData(targetContainer);
        }
      });
    });
  }
  
  /**
   * Simuliert die Aktualisierung von Daten mit einem Ladeindikator
   */
  function refreshData(container) {
    // Lade-Overlay erstellen
    const overlay = document.createElement('div');
    overlay.className = 'data-loading-overlay';
    overlay.innerHTML = '<div class="loading-spinner"></div>';
    
    // Füge das Overlay zum Container hinzu
    container.style.position = 'relative';
    container.appendChild(overlay);
    
    // Simuliere Ladezeit (kann durch tatsächliche API-Anfrage ersetzt werden)
    setTimeout(() => {
      container.removeChild(overlay);
      
      // Optionale Callback-Funktion für spezifische Datenaktualisierungen
      const dataLoadedEvent = new CustomEvent('data-loaded', {
        bubbles: true,
        detail: { container }
      });
      container.dispatchEvent(dataLoadedEvent);
    }, 1500);
  }
  
  /**
   * Fügt Skeleton-Loader für Inhalte hinzu, die geladen werden
   */
  function initSkeletonLoaders() {
    const contentContainers = document.querySelectorAll('[data-loading="true"]');
    
    contentContainers.forEach(container => {
      const dataType = container.getAttribute('data-type') || 'default';
      
      // Erstelle den entsprechenden Skeleton-Loader
      switch (dataType) {
        case 'kpi':
          createKPISkeleton(container);
          break;
        case 'chart':
          createChartSkeleton(container);
          break;
        case 'table':
          createTableSkeleton(container);
          break;
        default:
          createDefaultSkeleton(container);
      }
      
      // Entferne die Skeleton-Loader, wenn die Daten geladen sind
      container.addEventListener('data-loaded', () => {
        container.querySelectorAll('.skeleton').forEach(skeleton => {
          skeleton.classList.add('fade-out');
          setTimeout(() => {
            skeleton.remove();
          }, 300);
        });
        container.removeAttribute('data-loading');
      });
    });
  }
  
  /**
   * Erstellt einen KPI-Karten-Skeleton-Loader
   */
  function createKPISkeleton(container) {
    container.innerHTML = `
      <div class="skeleton kpi-skeleton">
        <div class="skeleton-avatar"></div>
        <div class="skeleton-content">
          <div class="skeleton-text"></div>
          <div class="skeleton-text" style="width: 60%;"></div>
        </div>
      </div>
    `;
  }
  
  /**
   * Erstellt einen Chart-Skeleton-Loader
   */
  function createChartSkeleton(container) {
    container.innerHTML = `
      <div class="skeleton chart-skeleton">
        <div class="skeleton-text" style="width: 30%; margin-bottom: 1rem;"></div>
        <div class="skeleton" style="width: 100%; height: 200px; border-radius: 4px;"></div>
      </div>
    `;
  }
  
  /**
   * Erstellt einen Tabellen-Skeleton-Loader
   */
  function createTableSkeleton(container) {
    let rows = '';
    for (let i = 0; i < 5; i++) {
      rows += `
        <div class="skeleton-row">
          <div class="skeleton-cell" style="width: 20%;"></div>
          <div class="skeleton-cell" style="width: 40%;"></div>
          <div class="skeleton-cell" style="width: 15%;"></div>
          <div class="skeleton-cell" style="width: 15%;"></div>
        </div>
      `;
    }
    
    container.innerHTML = `
      <div class="skeleton table-skeleton">
        <div class="skeleton-header">
          <div class="skeleton-cell" style="width: 20%;"></div>
          <div class="skeleton-cell" style="width: 40%;"></div>
          <div class="skeleton-cell" style="width: 15%;"></div>
          <div class="skeleton-cell" style="width: 15%;"></div>
        </div>
        ${rows}
      </div>
    `;
  }
  
  /**
   * Erstellt einen Standardskeleton-Loader
   */
  function createDefaultSkeleton(container) {
    container.innerHTML = `
      <div class="skeleton">
        <div class="skeleton-text"></div>
        <div class="skeleton-text"></div>
        <div class="skeleton-text"></div>
        <div class="skeleton-text" style="width: 80%;"></div>
      </div>
    `;
  }
  
  /**
   * Initialisiert die mobile Ansichtsanpassung
   */
  function initMobileResponsiveness() {
    // Prüfe beim Start die Bildschirmgröße
    handleResize();
    
    // Füge Klassen für verbesserte mobile Darstellung hinzu
    if (window.innerWidth < 768) {
      DOM.body.classList.add('mobile-view');
    }
  }
  
  /**
   * Behandelt Größenänderungen des Fensters
   */
  function handleResize() {
    if (window.innerWidth < 768) {
      DOM.body.classList.add('mobile-view');
      if (DOM.sidebar) {
        DOM.sidebar.classList.remove('open');
      }
    } else {
      DOM.body.classList.remove('mobile-view');
    }
    
    // Aktualisiere Chart-Größen, wenn verfügbar
    if (typeof Chart !== 'undefined') {
      const charts = Chart.instances;
      for (let i = 0; i < charts.length; i++) {
        charts[i].resize();
      }
    }
  }
  
  /**
   * Fügt Eingangsanimationen für Elemente hinzu
   */
  function initAnimations() {
    // Karten-Eingangsanimation
    const cards = document.querySelectorAll('.card:not(.no-animation)');
    
    cards.forEach((card, index) => {
      card.style.opacity = '0';
      card.style.transform = 'translateY(20px)';
      
      setTimeout(() => {
        card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        card.style.opacity = '1';
        card.style.transform = 'translateY(0)';
      }, 100 * index); // Gestaffelte Animation
    });
    
    // KPI-Karten-Animationen
    DOM.kpiCards.forEach((kpiCard, index) => {
      const kpiValue = kpiCard.querySelector('.kpi-value');
      if (kpiValue) {
        animateCounter(kpiValue);
      }
    });
  }
  
  /**
   * Animiert einen Zahlenwert bis zum Zielwert
   */
  function animateCounter(element) {
    const finalValue = parseFloat(element.textContent.replace(/[^\d.-]/g, ''));
    const units = element.textContent.replace(/[\d.-]/g, '');
    
    if (isNaN(finalValue)) return;
    
    let startValue = 0;
    const duration = 1500;
    const startTime = performance.now();
    
    function updateCounter(currentTime) {
      const elapsedTime = currentTime - startTime;
      const progress = Math.min(elapsedTime / duration, 1);
      
      // Easing-Funktion für eine natürlichere Animation
      const easedProgress = 1 - Math.pow(1 - progress, 3);
      
      const currentValue = Math.floor(startValue + (finalValue - startValue) * easedProgress);
      element.textContent = currentValue + units;
      
      if (progress < 1) {
        requestAnimationFrame(updateCounter);
      } else {
        element.textContent = finalValue + units;
      }
    }
    
    requestAnimationFrame(updateCounter);
  }
  
  /**
   * Fügt benutzerfreundliche Fehlerbehandlung für UI-Komponenten hinzu
   */
  function initErrorHandlers() {
    // Abfangen fehlerhafter API-Anfragen
    const originalFetch = window.fetch;
    window.fetch = async function(...args) {
      try {
        const response = await originalFetch(...args);
        
        if (!response.ok) {
          const targetElement = document.querySelector(`[data-api-target="${args[0]}"]`);
          if (targetElement) {
            showErrorState(targetElement, response.status, response.statusText);
          }
        }
        
        return response;
      } catch (error) {
        console.error('Fetch-Fehler:', error);
        
        // Finde das Zielelement, falls vorhanden
        const url = typeof args[0] === 'string' ? args[0] : args[0].url;
        const targetElement = document.querySelector(`[data-api-target="${url}"]`);
        if (targetElement) {
          showErrorState(targetElement, 0, 'Netzwerkfehler');
        }
        
        throw error;
      }
    };
    
    // Bild-Fehlerbehandlung hinzufügen
    const images = document.querySelectorAll('img:not([data-no-error-handling])');
    images.forEach(img => {
      img.addEventListener('error', function() {
        this.src = '/static/img/fallback-image.png';
        this.classList.add('image-error');
      });
    });
  }
  
  /**
   * Zeigt einen Fehlerzustand für einen Container an
   */
  function showErrorState(container, statusCode, statusText) {
    container.innerHTML = `
      <div class="error-state">
        <div class="error-icon">
          <i class="fas fa-exclamation-circle"></i>
        </div>
        <div class="error-title">Fehler beim Laden der Daten</div>
        <div class="error-message">
          ${statusCode ? `Status: ${statusCode} ${statusText}` : 'Verbindungsfehler aufgetreten'}
        </div>
        <button class="btn btn-outline-primary btn-sm retry-btn">
          <i class="fas fa-sync-alt"></i> Erneut laden
        </button>
      </div>
    `;
    
    // Retry-Button-Funktionalität
    const retryButton = container.querySelector('.retry-btn');
    if (retryButton) {
      retryButton.addEventListener('click', () => {
        refreshData(container);
      });
    }
  }
  
  /**
   * Behandelt Fehler bei Chart-Darstellungen
   */
  function handleChartError(container) {
    container.innerHTML = `
      <div class="error-state">
        <div class="error-icon">
          <i class="fas fa-chart-bar"></i>
        </div>
        <div class="error-title">Fehler bei der Diagramm-Darstellung</div>
        <div class="error-message">
          Die Daten konnten nicht visualisiert werden.
        </div>
      </div>
    `;
  }
  
  /**
   * DOMContentLoaded-Handler
   */
  function onDOMReady() {
    // Setze Fallback-Daten für leere KPI-Elemente
    const emptyKPIs = document.querySelectorAll('.kpi-value:empty');
    emptyKPIs.forEach(kpi => {
      kpi.textContent = '0';
    });
    
    // LocalStorage verwenden, um die Benutzereinstellungen zu speichern
    loadUserPreferences();
  }
  
  /**
   * Lädt Benutzereinstellungen aus dem lokalen Speicher
   */
  function loadUserPreferences() {
    try {
      const preferences = JSON.parse(localStorage.getItem('shopPulseAI_userPreferences')) || {};
      
      // Wende gespeicherte Präferenzen an (z.B. Darkmode, Spracheinstellungen)
      if (preferences.darkMode) {
        DOM.body.classList.add('dark-mode');
      }
      
      // Weitere Präferenzen anwenden...
    } catch (error) {
      console.error('Fehler beim Laden der Benutzereinstellungen:', error);
    }
  }
  
  /**
   * Speichert Benutzereinstellungen im lokalen Speicher
   */
  function saveUserPreferences(preferences) {
    try {
      const currentPreferences = JSON.parse(localStorage.getItem('shopPulseAI_userPreferences')) || {};
      const updatedPreferences = { ...currentPreferences, ...preferences };
      
      localStorage.setItem('shopPulseAI_userPreferences', JSON.stringify(updatedPreferences));
    } catch (error) {
      console.error('Fehler beim Speichern der Benutzereinstellungen:', error);
    }
  }
  
  // Öffentliche API
  return {
    init,
    refreshData,
    saveUserPreferences,
    showErrorState
  };
})();

// Daten-Module (für Caching und Offline-Unterstützung)
ShopPulseAI.Data = (function() {
  'use strict';
  
  const cache = {};
  
  /**
   * Initialisiert das Daten-Modul
   */
  function init() {
    console.log('ShopPulseAI Daten-Modul initialisiert');
  }
  
  /**
   * Holt Daten mit Caching-Unterstützung
   */
  async function fetchWithCache(url, options = {}, cacheDuration = 300000) {
    const cacheKey = `${url}-${JSON.stringify(options)}`;
    
    // Prüfe, ob wir gültige gecachte Daten haben
    if (cache[cacheKey] && cache[cacheKey].timestamp > Date.now() - cacheDuration) {
      console.log('Verwende gecachte Daten für:', url);
      return cache[cacheKey].data;
    }
    
    try {
      const response = await fetch(url, options);
      
      if (!response.ok) {
        throw new Error(`API-Fehler: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      
      // Cache die Daten
      cache[cacheKey] = {
        data,
        timestamp: Date.now()
      };
      
      // Speichere im LocalStorage für Offline-Fälle
      try {
        localStorage.setItem(`shopPulseAI_data_${cacheKey}`, JSON.stringify(cache[cacheKey]));
      } catch (e) {
        console.warn('LocalStorage konnte nicht verwendet werden:', e);
      }
      
      return data;
    } catch (error) {
      console.error('Fehler beim Abrufen der Daten:', error);
      
      // Versuche, aus dem LocalStorage zu laden, wenn online nicht verfügbar
      try {
        const savedData = localStorage.getItem(`shopPulseAI_data_${cacheKey}`);
        if (savedData) {
          const parsedData = JSON.parse(savedData);
          console.log('Verwende Offline-Daten für:', url);
          return parsedData.data;
        }
      } catch (e) {
        console.error('Fehler beim Lesen von Offline-Daten:', e);
      }
      
      throw error;
    }
  }
  
  /**
   * Löscht den Daten-Cache
   */
  function clearCache(urlPattern) {
    if (urlPattern) {
      // Lösche nur bestimmte URL-Muster aus dem Cache
      Object.keys(cache).forEach(key => {
        if (key.includes(urlPattern)) {
          delete cache[key];
        }
      });
    } else {
      // Lösche den gesamten Cache
      Object.keys(cache).forEach(key => {
        delete cache[key];
      });
    }
  }
  
  // Öffentliche API
  return {
    init,
    fetchWithCache,
    clearCache
  };
})();

// Initialisiere die Module bei Dokumentenladung
document.addEventListener('DOMContentLoaded', function() {
  // Initialisiere UI-Komponenten
  ShopPulseAI.UI.init();
  
  // Initialisiere Daten-Modul
  ShopPulseAI.Data.init();
  
  // Fallback für Chart.js, falls nicht vorhanden
  if (typeof Chart === 'undefined') {
    console.warn('Chart.js nicht geladen, einige Funktionen sind möglicherweise eingeschränkt');
    
    // Lade Chart.js dynamisch, falls nötig
    const chartScript = document.createElement('script');
    chartScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.7.0/chart.min.js';
    chartScript.async = true;
    document.body.appendChild(chartScript);
    
    chartScript.onload = function() {
      console.log('Chart.js erfolgreich nachgeladen');
      ShopPulseAI.UI.init(); // Neu initialisieren mit Chart.js
    };
  }
}); 