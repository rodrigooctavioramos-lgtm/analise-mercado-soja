// Global dashboard variables
let quotesData = null;
let currentChartTicker = 'soja_grao';
let quotesChartInstance = null;
let cropsChartInstance = null;
let exportsGrainsChartInstance = null;
let exportsOilChartInstance = null;
let oilsComparisonChartInstance = null;

// Map locations for Windy (Corrected to use embed.windy.com/embed2.html)
const MAP_LOCATIONS = {
    brazil: {
        title: "Radar Meteorológico - América do Sul (Brasil)",
        url: "https://embed.windy.com/embed2.html?lat=-13.149&lon=-52.603&detailLat=-13.149&detailLon=-52.603&width=650&height=450&zoom=5&level=surface&overlay=rain&product=ecmwf&menu=&message=true&marker=&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=km%2Fh&metricTemp=%C2%B0C&radarRange=-1"
    },
    usa: {
        title: "Radar Meteorológico - Cinturão Agrícola (EUA)",
        url: "https://embed.windy.com/embed2.html?lat=41.500&lon=-93.500&detailLat=41.500&detailLon=-93.500&width=650&height=450&zoom=5&level=surface&overlay=rain&product=ecmwf&menu=&message=true&marker=&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=km%2Fh&metricTemp=%C2%B0C&radarRange=-1"
    }
};

document.addEventListener("DOMContentLoaded", () => {
    // 1. Tab Switching
    setupTabNavigation();

    // 2. Load Initial Data
    loadQuotes();
    loadCrops();
    loadExports();
    loadForecast();
    loadOilComparison();

    // 3. Setup Calculator Events
    setupCalculator();

    // 4. Start Quote & Forecast Polling (every 3 seconds for UI polling)
    setInterval(loadQuotes, 3000);
    setInterval(loadForecast, 10000); // Forecast updates every 10s
});

// Setup sidebar tab navigation
function setupTabNavigation() {
    const navItems = document.querySelectorAll(".nav-item");
    const tabContents = document.querySelectorAll(".tab-content");

    navItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            
            // Remove active class from all nav items
            navItems.forEach(nav => nav.classList.remove("active"));
            // Add active class to clicked item
            item.classList.add("active");

            // Hide all tabs
            tabContents.forEach(tab => tab.classList.remove("active"));
            
            // Show corresponding tab
            const targetTabId = item.getAttribute("data-tab");
            const targetTab = document.getElementById(targetTabId);
            if (targetTab) {
                targetTab.classList.add("active");
            }
        });
    });
}

// Fetch Quotes from Backend API
async function loadQuotes() {
    try {
        const response = await fetch("/api/quotes");
        if (!response.ok) throw new Error("Erro de conexão ao carregar cotações");
        
        const data = await response.json();
        
        // Save globally
        const oldQuotesData = quotesData;
        quotesData = data.quotes;
        
        // Update DOM Elements
        updateQuotesUI(oldQuotesData);
        updateTickerTape();
        
        // Build or Update Chart
        renderQuotesChart();
        
        // Prefill Parity Calculator on First Load
        if (!oldQuotesData) {
            prefillCalculator();
        }
        
        document.getElementById("connection-status").textContent = "Online (Live API)";
        document.getElementById("connection-status").parentElement.querySelector('span').style.backgroundColor = "var(--accent-green)";
    } catch (error) {
        console.error("Erro ao carregar cotações:", error);
        document.getElementById("connection-status").textContent = "Erro de Sincronização";
        document.getElementById("connection-status").parentElement.querySelector('span').style.backgroundColor = "var(--accent-red)";
    }
}

// Update Quote KPIs on UI
function updateQuotesUI(oldData) {
    if (!quotesData) return;

    const items = ["soja_grao", "soja_b3_calculada", "soja3_b3", "soja_oleo", "soja_farelo", "dolar"];
    
    items.forEach(key => {
        const item = quotesData[key];
        if (!item) return;

        const valElem = document.getElementById(`val-${key.replaceAll("_", "-")}`);
        const chgElem = document.getElementById(`chg-${key.replaceAll("_", "-")}`);
        
        if (!valElem || !chgElem) return;

        // Formatted Values
        let formattedPrice = "";
        let formattedChange = "";
        
        if (key === "soja_grao") {
            formattedPrice = item.price.toFixed(2);
            formattedChange = `${item.change >= 0 ? '+' : ''}${item.change.toFixed(2)} (${item.pct_change.toFixed(2)}%)`;
        } else if (key === "soja_b3_calculada") {
            formattedPrice = `R$ ${item.price.toFixed(2)}`;
            formattedChange = `${item.change >= 0 ? '+' : ''}${item.change.toFixed(2)} (${item.pct_change.toFixed(2)}%)`;
        } else if (key === "soja3_b3") {
            formattedPrice = `R$ ${item.price.toFixed(2)}`;
            formattedChange = `${item.change >= 0 ? '+' : ''}${item.change.toFixed(2)} (${item.pct_change.toFixed(2)}%)`;
        } else if (key === "soja_oleo") {
            formattedPrice = item.price.toFixed(2);
            formattedChange = `${item.change >= 0 ? '+' : ''}${item.change.toFixed(2)} (${item.pct_change.toFixed(2)}%)`;
        } else if (key === "soja_farelo") {
            formattedPrice = item.price.toFixed(1);
            formattedChange = `${item.change >= 0 ? '+' : ''}${item.change.toFixed(1)} (${item.pct_change.toFixed(2)}%)`;
        } else if (key === "dolar") {
            formattedPrice = `R$ ${item.price.toFixed(4)}`;
            formattedChange = `${item.change >= 0 ? '+' : ''}${item.change.toFixed(4)} (${item.pct_change.toFixed(2)}%)`;
        }

        // Check for price changes and trigger blink animations
        const priceChanged = oldData && oldData[key] && oldData[key].price !== item.price;
        if (priceChanged) {
            const isUp = item.price > oldData[key].price;
            valElem.className = "kpi-val";
            valElem.classList.add(isUp ? "blink-up" : "blink-down");
            setTimeout(() => {
                valElem.className = "kpi-val";
            }, 800);
        }

        valElem.textContent = formattedPrice;
        chgElem.textContent = formattedChange;
        
        // Colors
        chgElem.className = "kpi-change " + (item.change >= 0 ? "up" : "down");
    });
}

// Update Ticker Tape Elements
function updateTickerTape() {
    if (!quotesData) return;

    const tickerTape = document.getElementById("ticker-tape");
    if (!tickerTape) return;

    let tickerHTML = "";
    
    // Define clean display labels
    const labels = {
        soja_grao: "SOJA CHICAGO (ZS)",
        soja_b3_calculada: "SOJA B3 (CALC)",
        soja3_b3: "BOA SAFRA (SOJA3)",
        soja_oleo: "ÓLEO DE SOJA (ZL)",
        soja_farelo: "FARELO DE SOJA (ZM)",
        dolar: "USD/BRL"
    };

    const keys = ["soja_grao", "soja_b3_calculada", "soja3_b3", "soja_oleo", "soja_farelo", "dolar"];
    
    // Generate one set of items
    let itemsHTML = "";
    keys.forEach(key => {
        const item = quotesData[key];
        if (!item) return;

        const isUp = item.change >= 0;
        const changeClass = isUp ? "up" : "down";
        const icon = isUp ? "fa-caret-up" : "fa-caret-down";
        
        let priceStr = "";
        let changeStr = "";
        
        if (key === "dolar") {
            priceStr = item.price.toFixed(4);
            changeStr = `${isUp ? '+' : ''}${item.change.toFixed(4)} (${item.pct_change.toFixed(2)}%)`;
        } else if (key === "soja_b3_calculada" || key === "soja3_b3") {
            priceStr = `R$ ${item.price.toFixed(2)}`;
            changeStr = `${isUp ? '+' : ''}${item.change.toFixed(2)} (${item.pct_change.toFixed(2)}%)`;
        } else {
            priceStr = item.price.toFixed(2);
            changeStr = `${isUp ? '+' : ''}${item.change.toFixed(2)} (${item.pct_change.toFixed(2)}%)`;
        }

        itemsHTML += `
            <div class="ticker-item ${changeClass}">
                <span class="ticker-label">${labels[key]}</span>
                <span class="ticker-val">${priceStr}</span>
                <span class="ticker-change">
                    <i class="fa-solid ${icon}"></i> ${changeStr}
                </span>
            </div>
        `;
    });

    // Duplicate ticker items to ensure infinite seamless scrolling effect
    tickerTape.innerHTML = itemsHTML + itemsHTML + itemsHTML;
}

// Draw or Update CBOT Prices Charts
function renderQuotesChart() {
    if (!quotesData) return;

    const ctx = document.getElementById("chart-quotes-history");
    if (!ctx) return;

    const selectedData = quotesData[currentChartTicker];
    if (!selectedData || !selectedData.history_6m) return;

    const history = selectedData.history_6m;
    const labels = history.map(h => {
        const parts = h.date.split("-");
        return `${parts[2]}/${parts[1]}`;
    });
    const values = history.map(h => h.value);

    // Dynamic Chart Labels/Titles
    const chartLabels = {
        soja_grao: "Soja Grão CBOT (US¢/bu)",
        soja_b3_calculada: "Soja Físico B3 Paridade (R$/sc 60kg)",
        soja3_b3: "Ação Boa Safra SOJA3.SA (R$)",
        soja_oleo: "Óleo de Soja CBOT (US¢/lb)",
        dolar: "USD/BRL (Câmbio)"
    };

    if (quotesChartInstance) {
        // Update existing chart instance to prevent canvas rendering errors
        quotesChartInstance.data.labels = labels;
        quotesChartInstance.data.datasets[0].label = chartLabels[currentChartTicker] || "Histórico";
        quotesChartInstance.data.datasets[0].data = values;
        quotesChartInstance.update();
    } else {
        // Create new chart instance
        quotesChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: chartLabels[currentChartTicker] || "Histórico",
                    data: values,
                    borderColor: '#C89B3C',
                    backgroundColor: 'rgba(200, 155, 60, 0.08)',
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.35,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#C89B3C',
                    pointHoverBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        labels: {
                            color: '#94a3b8',
                            font: { family: 'Outfit', size: 12 }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(6, 11, 19, 0.95)',
                        titleColor: '#fff',
                        bodyColor: '#f8fafc',
                        titleFont: { family: 'Outfit', weight: 'bold' },
                        bodyFont: { family: 'JetBrains Mono' },
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        displayColors: false
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: {
                            color: '#94a3b8',
                            maxTicksLimit: 12,
                            font: { family: 'Outfit', size: 10 }
                        }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: {
                            color: '#94a3b8',
                            font: { family: 'Outfit', size: 10 }
                        }
                    }
                }
            }
        });
    }
}

// Switch between Ticker chart series
function switchChartTicker(key) {
    currentChartTicker = key;
    renderQuotesChart();
}

// Calculator logic
function setupCalculator() {
    const fields = ["calc-cbot", "calc-premium", "calc-freight", "calc-usd"];
    
    fields.forEach(id => {
        const elem = document.getElementById(id);
        if (elem) {
            elem.addEventListener("input", calculateParity);
        }
    });
}

function prefillCalculator() {
    if (!quotesData) return;
    
    const soja = quotesData["soja_grao"];
    const dolar = quotesData["dolar"];

    if (soja) {
        document.getElementById("calc-cbot").value = soja.price.toFixed(2);
    }
    if (dolar) {
        document.getElementById("calc-usd").value = dolar.price.toFixed(4);
    }

    calculateParity();
}

function calculateParity() {
    const cbotVal = parseFloat(document.getElementById("calc-cbot").value) || 0;
    const premiumVal = parseFloat(document.getElementById("calc-premium").value) || 0;
    const freightVal = parseFloat(document.getElementById("calc-freight").value) || 0;
    const usdVal = parseFloat(document.getElementById("calc-usd").value) || 0;

    // Formula: ( (CBOT + Premium - Freight) / 100 ) * 2.20462 * Câmbio
    const usdPerBushel = (cbotVal + premiumVal - freightVal) / 100;
    const usdPerBag = usdPerBushel * 2.20462;
    const brlPerBag = usdPerBag * usdVal;

    const resultVal = document.getElementById("calc-result-brl");
    if (resultVal) {
        resultVal.innerHTML = `R$ ${brlPerBag.toFixed(2)} <span style="font-size: 13px; font-weight: normal; color: var(--text-secondary);">/ sc 60kg</span>`;
    }
}

// Force Refresh Quotes manually
async function forceReloadQuotes() {
    const btn = document.querySelector(".header-actions button");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Atualizando...`;
    }
    
    try {
        await fetch("/api/reload");
        await loadQuotes();
        await loadForecast();
        await loadOilComparison();
    } catch(e) {
        console.error("Erro ao recarregar:", e);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-rotate"></i> Atualizar Agora`;
        }
    }
}

// Fetch Crops Data
async function loadCrops() {
    try {
        const response = await fetch("/api/crops");
        if (!response.ok) throw new Error("Erro ao buscar dados de safra");
        const data = await response.json();
        
        renderCropsChart(data);
        renderCropsTable(data);
    } catch (e) {
        console.error("Erro ao processar dados de safra:", e);
    }
}

function renderCropsChart(data) {
    const ctx = document.getElementById("chart-crops-production");
    if (!ctx) return;

    cropsChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.anos,
            datasets: [
                {
                    label: 'Brasil',
                    data: data.brasil_prod,
                    backgroundColor: 'rgba(90, 158, 111, 0.7)',
                    borderColor: 'rgba(90, 158, 111, 1)',
                    borderWidth: 1.5
                },
                {
                    label: 'EUA',
                    data: data.eua_prod,
                    backgroundColor: 'rgba(200, 155, 60, 0.7)',
                    borderColor: 'rgba(200, 155, 60, 1)',
                    borderWidth: 1.5
                },
                {
                    label: 'Argentina',
                    data: data.argentina_prod,
                    backgroundColor: 'rgba(239, 68, 68, 0.7)',
                    borderColor: 'rgba(239, 68, 68, 1)',
                    borderWidth: 1.5
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#94a3b8',
                        font: { family: 'Outfit', size: 12 }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(6, 11, 19, 0.95)',
                    titleColor: '#fff',
                    bodyColor: '#f8fafc',
                    titleFont: { family: 'Outfit', weight: 'bold' },
                    bodyFont: { family: 'JetBrains Mono' },
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: {
                        color: '#94a3b8',
                        font: { family: 'Outfit', size: 11 }
                    }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: {
                        color: '#94a3b8',
                        font: { family: 'Outfit', size: 11 }
                    },
                    title: {
                        display: true,
                        text: 'Milhões de Toneladas (mt)',
                        color: '#94a3b8',
                        font: { family: 'Outfit', size: 12 }
                    }
                }
            }
        }
    });
}

function renderCropsTable(data) {
    const tableBody = document.querySelector("#table-crops-data tbody");
    if (!tableBody) return;

    let rowsHTML = "";
    for (let i = data.anos.length - 1; i >= 0; i--) {
        rowsHTML += `
            <tr>
                <td style="font-weight: 600; color: var(--accent-gold);">${data.anos[i]}</td>
                <td style="font-family: monospace; font-weight: 500;">${data.brasil_prod[i].toFixed(1)} Mt</td>
                <td style="font-family: monospace; font-weight: 500;">${data.eua_prod[i].toFixed(1)} Mt</td>
                <td style="font-family: monospace; font-weight: 500;">${data.argentina_prod[i].toFixed(1)} Mt</td>
            </tr>
        `;
    }
    tableBody.innerHTML = rowsHTML;
}

// Fetch Exports Data
async function loadExports() {
    try {
        const response = await fetch("/api/exports");
        if (!response.ok) throw new Error("Erro ao buscar dados de exportação");
        const data = await response.json();
        
        renderExportsCharts(data);
    } catch(e) {
        console.error("Erro ao carregar exportações:", e);
    }
}

function renderExportsCharts(data) {
    const ctxGrains = document.getElementById("chart-exports-grains");
    const ctxOil = document.getElementById("chart-exports-oil");
    
    if (ctxGrains && !exportsGrainsChartInstance) {
        exportsGrainsChartInstance = new Chart(ctxGrains, {
            type: 'line',
            data: {
                labels: data.anos,
                datasets: [{
                    label: 'Exportado Soja Grão (Mt)',
                    data: data.soja_grao,
                    borderColor: 'rgba(90, 158, 111, 1)',
                    backgroundColor: 'rgba(90, 158, 111, 0.08)',
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.35,
                    pointRadius: 4,
                    pointBackgroundColor: 'rgba(90, 158, 111, 1)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(6, 11, 19, 0.95)',
                        bodyFont: { family: 'JetBrains Mono' }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: { color: '#94a3b8', font: { family: 'Outfit', size: 11 } }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: { color: '#94a3b8', font: { family: 'Outfit', size: 11 } }
                    }
                }
            }
        });
    }

    if (ctxOil && !exportsOilChartInstance) {
        exportsOilChartInstance = new Chart(ctxOil, {
            type: 'line',
            data: {
                labels: data.anos,
                datasets: [{
                    label: 'Exportado Óleo (Mt)',
                    data: data.soja_oleo,
                    borderColor: 'rgba(200, 155, 60, 1)',
                    backgroundColor: 'rgba(200, 155, 60, 0.08)',
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.35,
                    pointRadius: 4,
                    pointBackgroundColor: 'rgba(200, 155, 60, 1)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(6, 11, 19, 0.95)',
                        bodyFont: { family: 'JetBrains Mono' }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: { color: '#94a3b8', font: { family: 'Outfit', size: 11 } }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: { color: '#94a3b8', font: { family: 'Outfit', size: 11 } }
                    }
                }
            }
        });
    }
}

// Fetch Weekly Technical Forecast
async function loadForecast() {
    try {
        const response = await fetch("/api/forecast");
        if (!response.ok) throw new Error("Erro ao carregar previsão semanal");
        const data = await response.json();
        
        updateForecastUI(data);
    } catch(e) {
        console.error("Erro ao processar previsão semanal:", e);
    }
}

function updateForecastUI(data) {
    const trendElem = document.getElementById("forecast-trend");
    const probElem = document.getElementById("forecast-prob");
    const cbotElem = document.getElementById("forecast-cbot-range");
    const parityElem = document.getElementById("forecast-parity-range");
    const rationaleElem = document.getElementById("forecast-rationale");
    const timeElem = document.getElementById("forecast-timestamp");

    if (!trendElem) return;

    // Trend direction styling
    const isUp = data.direction === "Alta";
    trendElem.textContent = `Tendência: ${data.direction}`;
    trendElem.className = `forecast-badge ${isUp ? 'alta' : 'baixa'}`;
    
    // Confidence and ranges
    probElem.textContent = `${data.probability}%`;
    probElem.style.color = isUp ? "var(--accent-green)" : "var(--accent-red)";
    cbotElem.textContent = `${data.cbot_range_min.toFixed(2)} - ${data.cbot_range_max.toFixed(2)} ¢/bu`;
    parityElem.textContent = `R$ ${data.parity_range_min.toFixed(2)} - R$ ${data.parity_range_max.toFixed(2)}`;
    rationaleElem.textContent = data.commentary;
    timeElem.textContent = `Atualizado em: ${data.calculated_at}`;
}

// Fetch and Render Vegetable Oils Comparison
async function loadOilComparison() {
    try {
        const response = await fetch("/api/oil-comparison");
        if (!response.ok) throw new Error("Erro ao buscar comparação de óleos");
        const data = await response.json();
        
        renderOilComparisonChart(data);
    } catch(e) {
        console.error("Erro ao renderizar gráfico comparativo de óleos:", e);
    }
}

function renderOilComparisonChart(data) {
    const ctx = document.getElementById("chart-oils-comparison");
    if (!ctx) return;

    const series = data.series;
    const labels = series.map(s => {
        const parts = s.date.split("-");
        return `${parts[2]}/${parts[1]}`;
    });
    
    const sojaValues = series.map(s => s.soja);
    const palmaValues = series.map(s => s.palma);
    const algodaoValues = series.map(s => s.algodao);

    if (oilsComparisonChartInstance) {
        oilsComparisonChartInstance.data.labels = labels;
        oilsComparisonChartInstance.data.datasets[0].data = sojaValues;
        oilsComparisonChartInstance.data.datasets[1].data = palmaValues;
        oilsComparisonChartInstance.data.datasets[2].data = algodaoValues;
        oilsComparisonChartInstance.update();
    } else {
        oilsComparisonChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Óleo de Soja (CBOT)',
                        data: sojaValues,
                        borderColor: '#C89B3C',
                        backgroundColor: 'rgba(200, 155, 60, 0.03)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.35,
                        pointRadius: 0
                    },
                    {
                        label: 'Óleo de Palma (MDEX)',
                        data: palmaValues,
                        borderColor: '#5a9e6f',
                        backgroundColor: 'rgba(90, 158, 111, 0.03)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.35,
                        pointRadius: 0
                    },
                    {
                        label: 'Óleo de Algodão (ICE)',
                        data: algodaoValues,
                        borderColor: '#5bc0be',
                        backgroundColor: 'rgba(91, 192, 190, 0.03)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.35,
                        pointRadius: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#94a3b8',
                            font: { family: 'Outfit', size: 11 }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(6, 11, 19, 0.95)',
                        titleColor: '#fff',
                        bodyColor: '#f8fafc',
                        titleFont: { family: 'Outfit', weight: 'bold' },
                        bodyFont: { family: 'JetBrains Mono' },
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(context.parsed.y) + '/t';
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: {
                            color: '#94a3b8',
                            maxTicksLimit: 12,
                            font: { family: 'Outfit', size: 10 }
                        }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: {
                            color: '#94a3b8',
                            font: { family: 'Outfit', size: 10 }
                        },
                        title: {
                            display: true,
                            text: 'USD / Tonelada',
                            color: '#94a3b8',
                            font: { family: 'Outfit', size: 12 }
                        }
                    }
                }
            }
        });
    }
}

// Weather Maps Switch Focus
function setWeatherMapFocus(region) {
    const iframe = document.getElementById("windy-iframe");
    const cardTitle = document.getElementById("weather-card-title");
    
    if (!iframe || !cardTitle) return;
    
    const config = MAP_LOCATIONS[region];
    if (config) {
        iframe.src = config.url;
        cardTitle.querySelector("h3").textContent = config.title;
    }
}
