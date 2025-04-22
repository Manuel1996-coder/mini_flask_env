// ShopPulseAI Dashboard JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Lade Echtzeit-Daten, bevor Diagramme initialisiert werden
    loadShopifyData().then(() => {
        // Wenn Daten geladen, Charts initialisieren
        initCharts();
        
        // Event-Listener für Filter-Dropdowns
        initFilterListeners();
        
        // Event-Listener für Tasks
        initTaskActions();
    });
});

// Speichere Chart-Instanzen für späteres Zerstören
window.chartInstances = {};

// Lade Echtzeit-Daten von der API
async function loadShopifyData() {
    try {
        showLoadingState();
        
        // Versuche Daten von der API zu laden
        const response = await fetch('/api/data');
        
        if (!response.ok) {
            throw new Error(`HTTP-Fehler ${response.status}`);
        }
        
        const data = await response.json();
        
        // Wenn Daten gültig sind, aktualisiere dashboardData
        if (data && data.success) {
            window.dashboardData = {
                trafficDates: data.trafficDates || ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
                trafficData: data.trafficData || {
                    pageviews: [450, 520, 480, 630, 580, 520, 680],
                    visitors: [320, 380, 350, 450, 420, 380, 480]
                },
                deviceData: data.deviceData || [45, 40, 15]
            };
            console.log("✅ Echte Shopify-Daten geladen:", window.dashboardData);
        } else {
            // Wenn API keine gültigen Daten zurückgibt, verwende Backup-Daten
            initDashboardData();
            console.warn("⚠️ Echte Daten konnten nicht geladen werden, verwende Backup-Daten");
        }
    } catch (error) {
        console.error("❌ Fehler beim Laden der Shopify-Daten:", error);
        // Im Fehlerfall, lokale Daten verwenden
        initDashboardData();
    } finally {
        hideLoadingState();
    }
}

// Lade Dashboard-Daten aus DOM-Attributen (als Fallback)
function initDashboardData() {
    const dataElement = document.getElementById('dashboard-data');
    
    if (!dataElement) {
        console.warn("Kein Dashboard-Daten-Element gefunden");
        return;
    }
    
    // Globales Objekt mit Standardwerten
    window.dashboardData = {
        trafficDates: ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
        trafficData: {
            pageviews: [450, 520, 480, 630, 580, 520, 680], 
            visitors: [320, 380, 350, 450, 420, 380, 480]
        },
        deviceData: [45, 40, 15]
    };
    
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
    
    // Versuche Daten aus Attributen zu laden
    try {
        if (dataElement.dataset.trafficDates) {
            window.dashboardData.trafficDates = safeJsonParse(dataElement.dataset.trafficDates, window.dashboardData.trafficDates);
        }
        
        if (dataElement.dataset.trafficData) {
            window.dashboardData.trafficData = safeJsonParse(dataElement.dataset.trafficData, window.dashboardData.trafficData);
        }
        
        if (dataElement.dataset.deviceData) {
            window.dashboardData.deviceData = safeJsonParse(dataElement.dataset.deviceData, window.dashboardData.deviceData);
        }
        
        console.log("Dashboard-Daten erfolgreich geladen:", window.dashboardData);
    } catch (error) {
        console.error("Fehler beim Parsen der Dashboard-Daten:", error);
    }
}

// Hilfsfunktion zum Zerstören eines vorhandenen Charts
function destroyChartIfExists(canvasId) {
    if (window.chartInstances[canvasId]) {
        window.chartInstances[canvasId].destroy();
        console.log(`Chart mit ID ${canvasId} zerstört`);
    }
}

// Initialisiere die Charts
function initCharts() {
    initTrafficChart();
    initDeviceChart();
}

// Traffic-Übersicht Chart
function initTrafficChart() {
    const ctx = document.getElementById('trafficChart');
    
    if (!ctx) return;
    
    // Zerstöre vorhandenes Chart
    destroyChartIfExists('trafficChart');
    
    const trafficDates = window.dashboardData?.trafficDates || ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
    const pageviewData = window.dashboardData?.trafficData?.pageviews || [450, 520, 480, 630, 580, 520, 680];
    const visitorData = window.dashboardData?.trafficData?.visitors || [320, 380, 350, 450, 420, 380, 480];
    
    const trafficChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: trafficDates,
            datasets: [
                {
                    label: 'Seitenaufrufe',
                    data: pageviewData,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                },
                {
                    label: 'Besucher',
                    data: visitorData,
                    borderColor: 'rgba(153, 102, 255, 1)',
                    backgroundColor: 'rgba(153, 102, 255, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    mode: 'index',
                    intersect: false
                },
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        boxWidth: 6
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
    
    // Speichere Chart-Instanz
    window.chartInstances['trafficChart'] = trafficChart;
}

// Geräte-Verteilung Chart
function initDeviceChart() {
    const ctx = document.getElementById('deviceChart');
    
    if (!ctx) return;
    
    // Zerstöre vorhandenes Chart
    destroyChartIfExists('deviceChart');
    
    const deviceData = window.dashboardData?.deviceData || [45, 40, 15]; // Mobil, Desktop, Tablet
    
    const deviceChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Mobil', 'Desktop', 'Tablet'],
            datasets: [{
                data: deviceData,
                backgroundColor: [
                    'rgba(255, 99, 132, 0.8)',
                    'rgba(54, 162, 235, 0.8)',
                    'rgba(255, 206, 86, 0.8)'
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        boxWidth: 6
                    }
                }
            },
            cutout: '70%'
        }
    });
    
    // Speichere Chart-Instanz
    window.chartInstances['deviceChart'] = deviceChart;
}

// Initialisiere Filter-Listeners
function initFilterListeners() {
    const periodFilter = document.getElementById('period-filter');
    
    if (periodFilter) {
        periodFilter.addEventListener('change', function() {
            // Hier würde normalerweise ein API-Call erfolgen, um neue Daten zu laden
            // Für diese Demo simulieren wir eine Aktualisierung
            simulateDataUpdate();
        });
    }
}

// Simuliere Datenaktualisierung
function simulateDataUpdate() {
    showLoadingState();
    
    // Simulierte API-Verzögerung
    setTimeout(() => {
        // Aktualisiere Charts mit neuen Daten
        updateCharts();
        hideLoadingState();
        
        // Zeige Erfolgsmeldung
        showNotification('Daten erfolgreich aktualisiert');
    }, 800);
}

// Aktualisiere Charts mit neuen Daten
function updateCharts() {
    // In einer echten Anwendung würden hier die Charts mit neuen Daten aktualisiert werden
    // Für diese Demo tun wir nichts, da wir keine echten Daten haben
}

// Zeige Lade-Zustand
function showLoadingState() {
    document.querySelectorAll('.chart-container').forEach(container => {
        container.classList.add('loading');
    });
    
    document.querySelectorAll('.kpi-card').forEach(card => {
        card.classList.add('loading');
    });
}

// Verstecke Lade-Zustand
function hideLoadingState() {
    document.querySelectorAll('.chart-container').forEach(container => {
        container.classList.remove('loading');
    });
    
    document.querySelectorAll('.kpi-card').forEach(card => {
        card.classList.remove('loading');
    });
}

// Initialisiere Task-Aktionen
function initTaskActions() {
    // Event-Listener für "Erledigt"-Buttons
    document.querySelectorAll('.task-done-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const taskId = this.dataset.taskId;
            markTaskAsDone(taskId, this);
        });
    });
    
    // Event-Listener für "Details"-Buttons
    document.querySelectorAll('.task-details-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const taskId = this.dataset.taskId;
            showTaskDetails(taskId);
        });
    });
}

// Markiere Task als erledigt
function markTaskAsDone(taskId, button) {
    // Simuliere API-Call
    button.innerHTML = '<span class="spinner"></span>';
    button.disabled = true;
    
    setTimeout(() => {
        const row = button.closest('tr');
        row.classList.add('task-completed');
        button.innerHTML = '✓ Erledigt';
        
        // In einer echten Anwendung würde hier ein API-Call erfolgen
        showNotification('Aufgabe als erledigt markiert');
    }, 600);
}

// Zeige Task-Details
function showTaskDetails(taskId) {
    // In einer echten Anwendung würde hier ein Modal oder eine Detailseite geöffnet werden
    // Für diese Demo zeigen wir eine Benachrichtigung
    showNotification('Detailansicht für Aufgabe #' + taskId);
}

// Zeige Benachrichtigung
function showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
} 