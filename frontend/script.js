const API_BASE = 'http://127.0.0.1:5000/api';

// Utility to determine page type
const isPatientsPage = window.location.pathname.includes('patients.html');
const isDashboardPage = window.location.pathname.includes('dashboard.html');

document.addEventListener('DOMContentLoaded', () => {
    if (isPatientsPage) {
        fetchPatients();
        setInterval(fetchPatients, 2000); // Poll every 2 seconds
    } else if (isDashboardPage) {
        const urlParams = new URLSearchParams(window.location.search);
        const patientId = urlParams.get('id');
        if (patientId) {
            fetchPatientDetails(patientId);
            setInterval(() => fetchPatientDetails(patientId), 2000);
        } else {
            alert('No patient ID specified');
            window.location.href = 'patients.html';
        }
    }
});

async function fetchPatients() {
    try {
        const response = await fetch(`${API_BASE}/patients`);
        const patients = await response.json();
        renderPatientsList(patients);
    } catch (error) {
        console.error('Error fetching patients:', error);
    }
}

function renderPatientsList(patients) {
    const grid = document.getElementById('patientsGrid');
    grid.innerHTML = ''; // Clear current list to rebuild (simple approach)

    patients.forEach(p => {
        const isHighRisk = p.risk === 1;
        const statusColor = isHighRisk ? 'var(--secondary-color)' : 'var(--success-color)';
        const borderColor = isHighRisk ? 'var(--secondary-color)' : 'rgba(255,255,255,0.05)';

        const card = document.createElement('div');
        card.className = 'card patient-item';
        card.style.borderColor = borderColor;
        card.style.display = 'block'; // Override flex from class if needed
        card.onclick = () => window.location.href = `dashboard.html?id=${p.id}`;

        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div>
                    <h3 style="margin: 0 0 0.5rem 0;">${p.name}</h3>
                    <p class="text-muted" style="margin: 0; font-size: 0.9rem;">ID: ${p.id}</p>
                </div>
                <div style="text-align: right;">
                    <span style="display: inline-block; padding: 0.25rem 0.75rem; border-radius: 99px; background: ${statusColor}; color: white; font-size: 0.8rem; font-weight: bold;">
                        ${isHighRisk ? 'HIGH RISK' : 'NORMAL'}
                    </span>
                </div>
            </div>
            <div style="margin-top: 1rem; display: flex; justify-content: space-between; color: var(--text-muted); font-size: 0.9rem;">
                <span>❤️ ${p.heart_rate} bpm</span>
                <span>🌡️ ${p.temperature}°C</span>
                <span>💧 ${p.spo2}%</span>
            </div>
        `;
        grid.appendChild(card);
    });
}

async function fetchPatientDetails(id) {
    try {
        const response = await fetch(`${API_BASE}/patient/${id}`);
        if (!response.ok) throw new Error('Patient not found');
        const p = await response.json();
        updateDashboard(p);
    } catch (error) {
        console.error('Error fetching details:', error);
    }
}

function updateDashboard(p) {
    document.getElementById('patientName').innerText = p.name;
    document.getElementById('patientId').innerText = `Patient ID: ${p.id}`;

    // Vitals
    updateVital('hr', p.heart_rate, 100, 60); // High > 100, Low < 60 (simplified logic)
    updateVital('temp', p.temperature, 37.5, 36.0);
    updateVital('spo2', p.spo2, 100, 90, true); // Low is bad for SpO2

    // Risk
    const riskBadge = document.getElementById('riskBadge');
    const aiText = document.getElementById('aiAnalysis');

    if (p.risk === 1) {
        riskBadge.innerText = 'HIGH RISK DETECTED';
        riskBadge.style.background = 'var(--secondary-color)';
        riskBadge.classList.add('animate-pulse');
        aiText.innerText = `⚠️ AI Prediction: High probability of cardiac event or deterioration. Recommended immediate attention. (HR: ${p.heart_rate}, O2: ${p.spo2}%)`;
        aiText.style.color = 'var(--secondary-color)';
    } else {
        riskBadge.innerText = 'VITALS NORMAL';
        riskBadge.style.background = 'var(--success-color)';
        riskBadge.classList.remove('animate-pulse');
        aiText.innerText = '✅ AI Prediction: Vitals are within stable range. No immediate risk detected.';
        aiText.style.color = 'var(--success-color)';
    }

    // Update Forecast
    fetchForecast(p.id);
}

function updateVital(idPrefix, value, highThresh, lowThresh, invert = false) {
    const elValue = document.getElementById(`${idPrefix}Value`);
    const elInd = document.getElementById(`${idPrefix}Indicator`);

    if (elValue) elValue.innerText = value;

    let isBad = false;

    // Check upper bound (if applicable)
    if (highThresh !== null && value > highThresh) isBad = true;

    // Check lower bound (if applicable)
    if (lowThresh !== null && value < lowThresh) isBad = true;

    // Special case for SpO2 where we mainly care about low values
    if (invert) {
        if (value < lowThresh) isBad = true;
        else isBad = false;
    }

    if (isBad) {
        if (elValue) elValue.classList.add('text-danger');
        if (elInd) elInd.className = 'status-indicator status-danger';
    } else {
        if (elValue) elValue.classList.remove('text-danger');
        if (elInd) elInd.className = 'status-indicator status-normal';
    }
}

// --- Digital Twin Logic ---

async function setTrend(trendType) {
    const urlParams = new URLSearchParams(window.location.search);
    const patientId = urlParams.get('id');
    if (!patientId) return;

    try {
        await fetch(`${API_BASE}/patient/${patientId}/trend`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trend: trendType })
        });
        // Immediate refresh
        fetchPatientDetails(patientId);
    } catch (error) {
        console.error('Error setting trend:', error);
    }
}

let mainChart = null;
let currentChartMode = 'forecast'; // 'forecast' or 'history'

function toggleChart(mode) {
    currentChartMode = mode;
    const btnForecast = document.getElementById('btnForecast');
    const btnHistory = document.getElementById('btnHistory');

    if (mode === 'forecast') {
        btnForecast.style.background = 'var(--primary-color)';
        btnHistory.style.background = 'var(--surface-light)';
    } else {
        btnForecast.style.background = 'var(--surface-light)';
        btnHistory.style.background = 'var(--primary-color)';
    }

    // Trigger refresh based on current patient
    const urlParams = new URLSearchParams(window.location.search);
    const patientId = urlParams.get('id');
    if (patientId) {
        if (mode === 'forecast') fetchForecast(patientId);
        else fetchHistory(patientId);
    }
}

async function fetchForecast(patientId) {
    try {
        const response = await fetch(`${API_BASE}/patient/${patientId}/forecast`);
        const data = await response.json();
        renderChart(data.forecast, 'forecast');
    } catch (error) {
        console.error('Error fetching forecast:', error);
    }
}

async function fetchHistory(patientId) {
    try {
        const response = await fetch(`${API_BASE}/patient/${patientId}/history`);
        const data = await response.json();
        // Reverse to show oldest to newest left-to-right
        renderChart(data.reverse(), 'history');
    } catch (error) {
        console.error('Error fetching history:', error);
    }
}

function renderChart(data, mode) {
    const ctx = document.getElementById('mainChart');
    if (!ctx) return;

    let labels, hrData, spo2Data, riskData;

    if (mode === 'forecast') {
        labels = data.map(d => `+${d.minutes_ahead}m`);
        hrData = data.map(d => d.vitals.heart_rate);
        spo2Data = data.map(d => d.vitals.spo2);
        riskData = data.map(d => d.risk);
    } else {
        labels = data.map(d => new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
        hrData = data.map(d => d.heart_rate);
        spo2Data = data.map(d => d.spo2);
        riskData = data.map(d => d.risk);
    }

    if (mainChart) {
        mainChart.destroy();
    }

    mainChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Heart Rate (bpm)',
                    data: hrData,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.4,
                    yAxisID: 'y'
                },
                {
                    label: 'SpO2 (%)',
                    data: spo2Data,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    yAxisID: 'y'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false, // Disable animation for smoother updates
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                y: {
                    beginAtZero: false,
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    ticks: { color: '#9ca3af' }
                },
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    ticks: { color: '#9ca3af' }
                }
            },
            plugins: {
                legend: { labels: { color: '#e5e7eb' } },
                title: {
                    display: true,
                    text: mode === 'forecast' ? 'AI Future Prediction' : 'Historical Vitals (Last 50 pts)',
                    color: '#e5e7eb'
                },
                tooltip: {
                    callbacks: {
                        afterBody: function (context) {
                            const idx = context[0].dataIndex;
                            const risk = riskData[idx];
                            return risk === 1 ? '\n⚠️ HIGH RISK' : '\n✅ Normal';
                        }
                    }
                }
            }
        }
    });
}
