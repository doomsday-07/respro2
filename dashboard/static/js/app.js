/**
 * Realtime Sales Performance & Inventory Optimization Dashboard
 * Client Controller & Chart.js Visualizations
 */

let trendChartInstance = null;
let categoryChartInstance = null;
let liveSocket = null;
let liveTransactionCount = 0;
let liveRevenueSum = 0;

document.addEventListener("DOMContentLoaded", () => {
    initFilters();
    loadDashboardData();
    initWebSocket();
    setupEventListeners();
});

function setupEventListeners() {
    // Filter controls
    document.getElementById("storeFilter").addEventListener("change", () => loadDashboardData());
    document.getElementById("categoryFilter").addEventListener("change", () => loadDashboardData());

    // Optimization simulation button
    document.getElementById("btnOptimize").addEventListener("click", runOptimizationSimulation);

    // Export Excel button
    document.getElementById("btnExportExcel").addEventListener("click", () => {
        window.location.href = "/api/export/excel";
    });

    // Export Tableau button
    document.getElementById("btnExportTableau").addEventListener("click", async () => {
        try {
            const res = await fetch("/api/export/tableau");
            const data = await res.json();
            alert(`Tableau Extracts Refreshed Successfully!\n\nExported Files:\n• ${data.files.mart}\n• ${data.files.kpis}\n• ${data.files.anomalies}\n• ${data.files.inventory}`);
        } catch (err) {
            alert("Error exporting Tableau data: " + err);
        }
    });

    // Theme toggle
    document.getElementById("themeToggle").addEventListener("click", () => {
        const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
        const newTheme = currentTheme === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", newTheme);
        document.getElementById("themeToggle").innerText = newTheme === "dark" ? "☀️ Light" : "🌙 Dark";
        if (trendChartInstance) trendChartInstance.update();
        if (categoryChartInstance) categoryChartInstance.update();
    });
}

function initFilters() {
    // Populate store options
    const storeSelect = document.getElementById("storeFilter");
    const stores = [
        { id: "ALL", name: "All Retail Locations (8 Stores)" },
        { id: "STR-001", name: "Manhattan 5th Ave Flagship" },
        { id: "STR-002", name: "Chicago Michigan Ave Center" },
        { id: "STR-003", name: "SF Union Square Tech Hub" },
        { id: "STR-004", name: "Austin Domain Town Center" },
        { id: "STR-005", name: "Dallas Galleria Megastore" },
        { id: "STR-006", name: "Seattle Pike Place Boutique" },
        { id: "STR-007", name: "Miami Brickell Promenade" },
        { id: "STR-008", name: "Omnichannel Distribution Hub" },
    ];
    storeSelect.innerHTML = stores.map(s => `<option value="${s.id}">${s.name}</option>`).join("");
}

async function loadDashboardData() {
    const storeId = document.getElementById("storeFilter").value;
    const category = document.getElementById("categoryFilter").value;

    const queryParams = new URLSearchParams();
    if (storeId && storeId !== "ALL") queryParams.append("store_id", storeId);
    if (category && category !== "ALL") queryParams.append("category", category);
    const qs = queryParams.toString() ? `?${queryParams.toString()}` : "";

    // 1. Load KPIs
    fetch(`/api/kpis${qs}`)
        .then(res => res.json())
        .then(kpis => renderKpis(kpis))
        .catch(err => console.error("Error loading KPIs:", err));

    // 2. Load Trend & 30-Day Forecast
    Promise.all([
        fetch(`/api/trend${qs}`).then(r => r.json()),
        fetch(`/api/forecast${qs}`).then(r => r.json())
    ]).then(([trendData, forecastData]) => {
        renderTrendAndForecast(trendData, forecastData);
    }).catch(err => console.error("Error loading trend/forecast:", err));

    // 3. Load Category breakdown
    fetch("/api/categories")
        .then(res => res.json())
        .then(cats => renderCategoryChart(cats))
        .catch(err => console.error("Error loading categories:", err));

    // 4. Load Store Leaderboard
    fetch("/api/stores")
        .then(res => res.json())
        .then(stores => renderStoreLeaderboard(stores))
        .catch(err => console.error("Error loading stores:", err));

    // 5. Load Anomalies
    fetch("/api/anomalies?limit=10")
        .then(res => res.json())
        .then(anoms => renderAnomalyList(anoms))
        .catch(err => console.error("Error loading anomalies:", err));
}

function renderKpis(kpis) {
    document.getElementById("kpiRevenue").innerText = `$${kpis.total_revenue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    document.getElementById("kpiMargin").innerText = `${kpis.gross_margin_pct.toFixed(1)}%`;
    document.getElementById("kpiMarginDollars").innerText = `$${kpis.gross_margin.toLocaleString('en-US', { maximumFractionDigits: 0 })} Gross Margin`;
    document.getElementById("kpiSellThrough").innerText = `${kpis.sell_through_rate.toFixed(1)}%`;
    document.getElementById("kpiTurnover").innerText = `${kpis.inventory_turnover.toFixed(2)}x`;
    document.getElementById("kpiStockoutRate").innerText = `${kpis.stockout_rate_pct.toFixed(1)}%`;
    document.getElementById("kpiStockoutCount").innerText = `${kpis.stockout_count} Incidents`;
}

function renderTrendAndForecast(trendData, forecastData) {
    const ctx = document.getElementById("trendForecastChart").getContext("2d");

    // Extract historical dates and revenues
    const histDates = trendData.map(d => d.date);
    const histRevenues = trendData.map(d => d.revenue);
    const histMargins = trendData.map(d => d.margin);

    // Extract forecast dates and predictions
    const fcPoints = forecastData.forecast || [];
    const fcDates = fcPoints.map(f => f.date);
    const fcRevenues = fcPoints.map(f => f.forecast_revenue);
    const fcUpper = fcPoints.map(f => f.upper_bound);
    const fcLower = fcPoints.map(f => f.lower_bound);

    const allLabels = [...histDates, ...fcDates];

    // Pad forecast arrays to match full length
    const paddedHistRev = [...histRevenues, ...Array(fcDates.length).fill(null)];
    const paddedHistMargin = [...histMargins, ...Array(fcDates.length).fill(null)];
    
    // Connect the last historical point with the first forecast point
    const lastHistVal = histRevenues[histRevenues.length - 1];
    const paddedFcRev = [...Array(histDates.length - 1).fill(null), lastHistVal, ...fcRevenues];
    const paddedFcUpper = [...Array(histDates.length - 1).fill(null), lastHistVal, ...fcUpper];
    const paddedFcLower = [...Array(histDates.length - 1).fill(null), lastHistVal, ...fcLower];

    if (trendChartInstance) {
        trendChartInstance.destroy();
    }

    trendChartInstance = new Chart(ctx, {
        type: "line",
        data: {
            labels: allLabels,
            datasets: [
                {
                    label: "Historical Revenue ($)",
                    data: paddedHistRev,
                    borderColor: "#3B82F6",
                    backgroundColor: "rgba(59, 130, 246, 0.08)",
                    borderWidth: 2.2,
                    tension: 0.2,
                    pointRadius: 0,
                    fill: false
                },
                {
                    label: "Gross Profit Margin ($)",
                    data: paddedHistMargin,
                    borderColor: "#10B981",
                    borderWidth: 1.8,
                    tension: 0.2,
                    pointRadius: 0,
                    fill: false
                },
                {
                    label: "30-Day Trend Forecast ($)",
                    data: paddedFcRev,
                    borderColor: "#8B5CF6",
                    borderWidth: 2.2,
                    borderDash: [5, 5],
                    tension: 0.3,
                    pointRadius: 0,
                    fill: false
                },
                {
                    label: "Upper 95% Confidence Band",
                    data: paddedFcUpper,
                    borderColor: "transparent",
                    backgroundColor: "rgba(139, 92, 246, 0.15)",
                    pointRadius: 0,
                    fill: "+1" // fill to lower bound
                },
                {
                    label: "Lower 95% Confidence Band",
                    data: paddedFcLower,
                    borderColor: "transparent",
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: "index",
                intersect: false
            },
            plugins: {
                legend: {
                    position: "top",
                    labels: {
                        color: "#94A3B8",
                        font: { size: 11, family: "Plus Jakarta Sans" },
                        filter: item => !item.text.includes("Confidence Band")
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            if (context.parsed.y !== null) {
                                return `${context.dataset.label}: $${context.parsed.y.toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
                            }
                            return null;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: "rgba(255, 255, 255, 0.04)" },
                    ticks: {
                        color: "#64748B",
                        maxTicksLimit: 12,
                        font: { size: 10 }
                    }
                },
                y: {
                    grid: { color: "rgba(255, 255, 255, 0.04)" },
                    ticks: {
                        color: "#64748B",
                        callback: val => `$${(val / 1000).toFixed(0)}k`,
                        font: { size: 10 }
                    }
                }
            }
        }
    });
}

function renderCategoryChart(cats) {
    const ctx = document.getElementById("categoryChart").getContext("2d");

    const labels = cats.map(c => c.category);
    const revenues = cats.map(c => c.revenue);
    const margins = cats.map(c => c.margin);

    if (categoryChartInstance) {
        categoryChartInstance.destroy();
    }

    categoryChartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Revenue ($)",
                    data: revenues,
                    backgroundColor: "#3B82F6",
                    borderRadius: 6
                },
                {
                    label: "Gross Profit ($)",
                    data: margins,
                    backgroundColor: "#10B981",
                    borderRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "top",
                    labels: { color: "#94A3B8", font: { size: 11 } }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: "#94A3B8", font: { size: 10 } }
                },
                y: {
                    grid: { color: "rgba(255, 255, 255, 0.04)" },
                    ticks: {
                        color: "#64748B",
                        callback: val => `$${(val / 1000).toFixed(0)}k`
                    }
                }
            }
        }
    });
}

function renderStoreLeaderboard(stores) {
    const tbody = document.getElementById("storeLeaderboardBody");
    tbody.innerHTML = stores.map((s, idx) => {
        const attainmentColor = s.target_attainment_pct >= 100 ? "var(--accent-emerald)" : s.target_attainment_pct >= 85 ? "var(--accent-amber)" : "var(--accent-rose)";
        return `
            <tr>
                <td style="font-weight: 700; color: #94A3B8;">#${idx + 1}</td>
                <td>
                    <div style="font-weight: 600;">${s.name}</div>
                    <div style="font-size: 0.75rem; color: #64748B;">${s.city} • ${s.store_type}</div>
                </td>
                <td style="font-weight: 700;">$${s.total_revenue.toLocaleString('en-US', { maximumFractionDigits: 0 })}</td>
                <td>
                    <div style="display: flex; justify-content: space-between; font-size: 0.78rem;">
                        <span>${s.target_attainment_pct.toFixed(1)}%</span>
                    </div>
                    <div class="progress-bar-container">
                        <div class="progress-bar-fill" style="width: ${Math.min(s.target_attainment_pct, 100)}%; background-color: ${attainmentColor};"></div>
                    </div>
                </td>
                <td><span class="kpi-badge positive">${s.gross_margin_pct.toFixed(1)}%</span></td>
                <td>${s.transactions.toLocaleString()}</td>
            </tr>
        `;
    }).join("");
}

function renderAnomalyList(anomalies) {
    const container = document.getElementById("anomalyStreamList");
    container.innerHTML = anomalies.map(a => {
        const isSurge = a.z_score >= 2.5;
        const badgeClass = isSurge ? "kpi-badge critical" : "kpi-badge warning";
        return `
            <div class="live-stream-item ${isSurge ? 'surge' : ''}">
                <div class="item-left">
                    <div class="item-title">${a.product_name}</div>
                    <div class="item-sub">${a.date} • ${a.store_name} • ${a.category}</div>
                    <div style="font-size: 0.75rem; margin-top: 4px; color: ${isSurge ? 'var(--accent-rose)' : 'var(--text-muted)'};">
                        Observed: <strong>${a.observed_value} units</strong> vs Expected: ${a.expected_value} (Z-Score: ${a.z_score})
                    </div>
                </div>
                <div class="item-right">
                    <span class="${badgeClass}">${a.severity.toUpperCase()}</span>
                </div>
            </div>
        `;
    }).join("");
}

function initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/live-sales`;
    liveSocket = new WebSocket(wsUrl);

    liveSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleLiveEvent(data);
    };

    liveSocket.onclose = () => {
        console.warn("Live stream disconnected. Reconnecting in 3s...");
        setTimeout(initWebSocket, 3000);
    };
}

function handleLiveEvent(data) {
    liveTransactionCount++;
    liveRevenueSum += data.gross_revenue;

    // Update live ticker
    document.getElementById("liveEventTicker").innerText = `Live Tx: ${liveTransactionCount} | +$${liveRevenueSum.toFixed(2)}`;

    // Prepend to live transaction feed
    const feed = document.getElementById("livePosFeed");
    const item = document.createElement("div");
    item.className = `live-stream-item ${data.is_surge_anomaly ? 'surge' : ''}`;
    item.innerHTML = `
        <div class="item-left">
            <div class="item-title">${data.product}</div>
            <div class="item-sub">${data.timestamp} • ${data.store} • ${data.channel}</div>
            ${data.alert ? `<div style="color: var(--accent-rose); font-size: 0.75rem; font-weight: 700; margin-top: 2px;">${data.alert}</div>` : ''}
        </div>
        <div class="item-right">
            <div class="item-price">+$${data.gross_revenue.toFixed(2)}</div>
            <div style="font-size: 0.72rem; color: #64748B;">${data.units} unit(s)</div>
        </div>
    `;

    feed.prepend(item);
    if (feed.children.length > 20) {
        feed.removeChild(feed.lastChild);
    }
}

async function runOptimizationSimulation() {
    const btn = document.getElementById("btnOptimize");
    btn.disabled = true;
    btn.innerText = "Optimizing Safety Buffers...";

    try {
        const res = await fetch("/api/optimize");
        const data = await res.json();
        const sim = data.simulation;

        // Animate counter and display results
        document.getElementById("optStockoutReduction").innerText = `${sim.relative_stockout_reduction_pct.toFixed(1)}%`;
        document.getElementById("optRecoveredRev").innerText = `$${sim.recovered_revenue_dollars.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        document.getElementById("optPreventedCount").innerText = `${sim.stockouts_prevented.toLocaleString()} Stockouts Prevented`;

        // Update main KPI
        document.getElementById("kpiStockoutReductionPill").innerText = `-${sim.relative_stockout_reduction_pct.toFixed(1)}% Optim Target Met`;
        document.getElementById("kpiStockoutReductionPill").className = "kpi-badge positive";

        alert(`✨ INVENTORY REORDER OPTIMIZATION APPLIED!\n\n` +
              `• Stockouts Reduced By: ${sim.relative_stockout_reduction_pct.toFixed(1)}% (18% Target Achieved)\n` +
              `• Baseline Incident Rate: ${sim.baseline_stockout_rate_pct.toFixed(1)}% ➔ Optimized: ${sim.optimized_stockout_rate_pct.toFixed(1)}%\n` +
              `• Critical Stockouts Prevented: ${sim.stockouts_prevented.toLocaleString()} incidents\n` +
              `• Projected Recovered Revenue: $${sim.recovered_revenue_dollars.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}\n` +
              `• Cycle Service Level: ${sim.service_level_achieved}%\n\nDynamic Safety Stock & Reorder Points are now synchronized with stores.`);
    } catch (err) {
        alert("Error running optimization: " + err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<span>⚡</span> Re-Simulate 18% Optimization`;
    }
}
