// ShopPulseAI Dashboard JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Dashboard-Daten aus Datenattributen laden
    initDashboardData();
    
    // Initialisiere alle Charts
    initCharts();
    
    // Event-Listener für Filter-Dropdowns
    initFilterListeners();
    
    // Event-Listener für Tasks
    initTaskActions();
});

// Lade Dashboard-Daten aus DOM-Attributen
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
    
    // Versuche Daten aus Attributen zu laden
    try {
        if (dataElement.dataset.trafficDates) {
            window.dashboardData.trafficDates = JSON.parse(dataElement.dataset.trafficDates);
        }
        
        if (dataElement.dataset.trafficData) {
            window.dashboardData.trafficData = JSON.parse(dataElement.dataset.trafficData);
        }
        
        if (dataElement.dataset.deviceData) {
            window.dashboardData.deviceData = JSON.parse(dataElement.dataset.deviceData);
        }
        
        console.log("Dashboard-Daten erfolgreich geladen:", window.dashboardData);
    } catch (error) {
        console.error("Fehler beim Parsen der Dashboard-Daten:", error);
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
}

// Geräte-Verteilung Chart
function initDeviceChart() {
    const ctx = document.getElementById('deviceChart');
    
    if (!ctx) return;
    
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