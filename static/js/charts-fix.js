/**
 * ShopPulseAI Chart.js Bugfix-Modul
 * 
 * Dieses Modul löst Probleme mit Chart.js, insbesondere:
 * - "Canvas is already in use" Fehler
 * - Mehrfache Chart-Initialisierungen auf denselben Canvas-Elementen
 * - Memory Leaks durch nicht zerstörte Chart-Instanzen
 */

// Globales Registry für alle erstellten Charts
window.ShopPulseCharts = window.ShopPulseCharts || {
    instances: {},
    
    // Registriert ein neues Chart im Registry
    register: function(id, chartInstance) {
        console.log(`Chart '${id}' registriert`);
        this.instances[id] = chartInstance;
        return chartInstance;
    },
    
    // Entfernt ein Chart aus dem Registry und zerstört es
    destroy: function(id) {
        if (this.instances[id]) {
            console.log(`Chart '${id}' wird zerstört`);
            this.instances[id].destroy();
            delete this.instances[id];
            return true;
        }
        return false;
    },
    
    // Erstellt ein neues Chart, zerstört aber zuerst ein evtl. vorhandenes altes
    create: function(ctx, config) {
        const id = ctx.id || 'chart-' + Math.random().toString(36).substr(2, 9);
        
        // Wenn ein Chart mit dieser ID bereits existiert, zerstöre es zuerst
        if (this.instances[id]) {
            this.destroy(id);
        }
        
        // Sicherheitscheck für andere Chart-Instanzen auf demselben Canvas
        if (Chart.getChart(ctx)) {
            console.warn(`Anderes Chart auf Canvas '${id}' gefunden, wird zerstört`);
            Chart.getChart(ctx).destroy();
        }
        
        // Neues Chart erstellen und registrieren
        const newChart = new Chart(ctx, config);
        return this.register(id, newChart);
    },
    
    // Sicherheitsfunktion zum Bereinigen aller Charts (z.B. vor Seitenwechsel)
    destroyAll: function() {
        for (const id in this.instances) {
            this.destroy(id);
        }
        console.log('Alle Charts zerstört');
    }
};

// Event-Listener für Seitenwechsel, um alle Charts zu bereinigen
window.addEventListener('beforeunload', function() {
    window.ShopPulseCharts.destroyAll();
});

// Monkey-Patch der Chart.js-Initialisierung, um unsere Wrapper-Funktion zu verwenden
document.addEventListener('DOMContentLoaded', function() {
    // Originale Chart-Konstruktor speichern
    const OriginalChart = window.Chart;
    
    // Chart-Konstruktor überschreiben
    window.Chart = function(ctx, config) {
        // Wenn direkt aufgerufen, verwende unseren sicheren Wrapper
        if (this instanceof window.Chart) {
            // Prüfe, ob der Kontext ein gültiges Canvas-Element ist
            if (ctx && ctx.getContext) {
                // Falls ein anderes Chart auf diesem Canvas existiert, zerstöre es
                const existingChart = OriginalChart.getChart(ctx);
                if (existingChart) {
                    console.warn(`Existierendes Chart auf Canvas gefunden, wird zerstört`);
                    existingChart.destroy();
                }
                
                // Originalen Konstruktor aufrufen
                return new OriginalChart(ctx, config);
            } else {
                console.error('Ungültiger Canvas-Kontext:', ctx);
                throw new Error('Chart.js benötigt einen gültigen Canvas-Kontext');
            }
        } else {
            // Wenn als Funktion aufgerufen, erzwinge den richtigen Aufruf mit "new"
            return new window.Chart(ctx, config);
        }
    };
    
    // Statische Methoden vom Original kopieren
    for (const key in OriginalChart) {
        if (OriginalChart.hasOwnProperty(key)) {
            window.Chart[key] = OriginalChart[key];
        }
    }
    
    // Prototyp vom Original kopieren
    window.Chart.prototype = OriginalChart.prototype;
    
    console.log('Chart.js Bugfix-Modul erfolgreich initialisiert');
});

// Sicheres Erstellen eines Charts
function createSafeChart(canvasId, type, data, options) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`Canvas mit ID '${canvasId}' nicht gefunden`);
        return null;
    }
    
    return window.ShopPulseCharts.create(canvas, {
        type: type,
        data: data,
        options: options || {}
    });
}