(function () {
  "use strict";

  const MBA_OPTIONS = ["SE1", "SE2", "SE3", "SE4"];

  const SOURCES = [
    { key: "hydro",          label: "Hydro",           color: "#2196F3" },
    { key: "wind",           label: "Wind",            color: "#009688" },
    { key: "wind_offshore",  label: "Wind Offshore",   color: "#00695C" },
    { key: "solar",          label: "Solar",           color: "#FFC107" },
    { key: "nuclear",        label: "Nuclear",         color: "#9C27B0" },
    { key: "thermal",        label: "Thermal",         color: "#795548" },
    { key: "energy_storage", label: "Energy Storage",  color: "#00BCD4" },
    { key: "other",          label: "Other",           color: "#9E9E9E" },
  ];

  const CHART_GRID_COLOR = "rgba(42, 48, 69, 0.6)";
  const CHART_TICK_COLOR = "#8892a8";

  let productionChart = null;
  let priceChart = null;

  let mbaSelect, startInput, endInput, goBtn;
  let errorBanner, statsGrid;

  async function fetchEndpoint(path, mba, start, end) {
    const params = new URLSearchParams({
      mba: mba,
      start: start.toISOString(),
      end: end.toISOString(),
      page_size: "10000",
    });
    const res = await fetch(path + "?" + params);
    if (!res.ok) {
      throw new Error("API error " + res.status + " from " + path);
    }
    const json = await res.json();
    return json.data;
  }

  const fetchProduction  = (mba, start, end) => fetchEndpoint("/api/production", mba, start, end);
  const fetchConsumption = (mba, start, end) => fetchEndpoint("/api/consumption", mba, start, end);
  const fetchPrices      = (mba, start, end) => fetchEndpoint("/api/prices", mba, start, end);

  function renderProductionChart(prodData, consData) {
    const ctx = document.getElementById("production-chart");

    if (productionChart) {
      productionChart.destroy();
      productionChart = null;
    }

    const datasets = SOURCES.map((src, i) => ({
      label: src.label,
      data: prodData.map((d) => ({ x: d.time, y: d[src.key] || 0 })),
      backgroundColor: src.color + "CC",
      borderColor: src.color,
      borderWidth: 1,
      pointRadius: 0,
      pointHitRadius: 6,
      fill: i === 0 ? "origin" : "-1",
      stack: "production",
      order: SOURCES.length - i,
    }));

    datasets.push({
      label: "Consumption",
      data: consData.map((d) => ({ x: d.time, y: d.total || 0 })),
      borderColor: "#ffffff",
      borderWidth: 2,
      borderDash: [6, 3],
      pointRadius: 0,
      pointHitRadius: 6,
      fill: false,
      yAxisID: "y",
      order: 0,
    });

    productionChart = new Chart(ctx, {
      type: "line",
      data: { datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: {
            type: "time",
            time: { unit: "hour", displayFormats: { hour: "MMM d HH:mm" } },
            grid: { color: CHART_GRID_COLOR },
            ticks: { color: CHART_TICK_COLOR, font: { family: "JetBrains Mono", size: 10 }, maxRotation: 45 },
          },
          y: {
            stacked: true,
            title: { display: true, text: "MWh", color: CHART_TICK_COLOR, font: { family: "JetBrains Mono", size: 11 } },
            grid: { color: CHART_GRID_COLOR },
            ticks: { color: CHART_TICK_COLOR, font: { family: "JetBrains Mono", size: 10 } },
          },
        },
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              color: CHART_TICK_COLOR,
              font: { family: "DM Sans", size: 11 },
              boxWidth: 12,
              padding: 16,
            },
          },
          tooltip: {
            mode: "index",
            intersect: false,
            backgroundColor: "#1a2035ee",
            titleFont: { family: "JetBrains Mono", size: 11 },
            bodyFont: { family: "DM Sans", size: 12 },
            borderColor: "#2a3045",
            borderWidth: 1,
            padding: 10,
          },
        },
      },
    });
  }

  function renderPriceChart(priceData) {
    const ctx = document.getElementById("price-chart");

    if (priceChart) {
      priceChart.destroy();
      priceChart = null;
    }

    priceChart = new Chart(ctx, {
      type: "line",
      data: {
        datasets: [
          {
            label: "Up-regulation",
            data: priceData.map((d) => ({ x: d.time, y: d.up_reg_price })),
            borderColor: "#1565C0",
            backgroundColor: "#1565C044",
            borderWidth: 1.5,
            pointRadius: 0,
            pointHitRadius: 6,
            fill: true,
          },
          {
            label: "Down-regulation",
            data: priceData.map((d) => ({ x: d.time, y: d.down_reg_price })),
            borderColor: "#E65100",
            backgroundColor: "#E6510044",
            borderWidth: 1.5,
            pointRadius: 0,
            pointHitRadius: 6,
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: {
            type: "time",
            time: { unit: "hour", displayFormats: { hour: "MMM d HH:mm" } },
            grid: { color: CHART_GRID_COLOR },
            ticks: { color: CHART_TICK_COLOR, font: { family: "JetBrains Mono", size: 10 }, maxRotation: 45 },
          },
          y: {
            title: { display: true, text: "EUR/MWh", color: CHART_TICK_COLOR, font: { family: "JetBrains Mono", size: 11 } },
            grid: { color: CHART_GRID_COLOR },
            ticks: { color: CHART_TICK_COLOR, font: { family: "JetBrains Mono", size: 10 } },
          },
        },
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              color: CHART_TICK_COLOR,
              font: { family: "DM Sans", size: 11 },
              boxWidth: 12,
              padding: 16,
            },
          },
          tooltip: {
            mode: "index",
            intersect: false,
            backgroundColor: "#1a2035ee",
            titleFont: { family: "JetBrains Mono", size: 11 },
            bodyFont: { family: "DM Sans", size: 12 },
            borderColor: "#2a3045",
            borderWidth: 1,
            padding: 10,
          },
        },
      },
    });
  }

  function createStatCard(label, value, detail, accentColor) {
    const card = document.createElement("div");
    card.className = "stat-card";
    card.style.setProperty("--accent-color", accentColor);

    const labelEl = document.createElement("div");
    labelEl.className = "stat-label";
    labelEl.textContent = label;

    const valueEl = document.createElement("div");
    valueEl.className = "stat-value";
    if (typeof value === "string") {
      valueEl.textContent = value;
    } else {
      valueEl.appendChild(value);
    }

    card.appendChild(labelEl);
    card.appendChild(valueEl);

    if (detail) {
      const detailEl = document.createElement("div");
      detailEl.className = "stat-detail";
      detailEl.textContent = detail;
      card.appendChild(detailEl);
    }

    return card;
  }

  function findPeakProduction(prodData) {
    if (!prodData.length) return { value: 0, source: "-", time: "-" };
    let peak = prodData[0];
    for (let i = 1; i < prodData.length; i++) {
      if ((prodData[i].total || 0) > (peak.total || 0)) {
        peak = prodData[i];
      }
    }

    let dominant = { key: "-", val: 0 };
    SOURCES.forEach((src) => {
      const v = peak[src.key] || 0;
      if (v > dominant.val) {
        dominant = { key: src.label, val: v };
      }
    });

    return {
      value: (peak.total || 0) / 1000,
      source: dominant.key,
      time: new Date(peak.time).toLocaleString(),
    };
  }

  function computeNetBalance(prodData, consData) {
    let totalProd = 0;
    let totalCons = 0;
    prodData.forEach((d) => { totalProd += d.total || 0; });
    consData.forEach((d) => { totalCons += d.total || 0; });
    return (totalProd - totalCons) / 1000;
  }

  function computeAvgPrice(priceData) {
    if (!priceData.length) return 0;
    let sum = 0;
    let count = 0;
    priceData.forEach((d) => {
      if (d.up_reg_price != null) {
        sum += d.up_reg_price;
        count++;
      }
    });
    return count > 0 ? sum / count : 0;
  }

  function computeConsumptionMix(consData) {
    let total = 0;
    let metered = 0;
    let profiled = 0;
    let flex = 0;
    consData.forEach((d) => {
      total += d.total || 0;
      metered += d.metered || 0;
      profiled += d.profiled || 0;
      flex += d.flex || 0;
    });
    if (total === 0) return { metered: 0, profiled: 0, flex: 0 };
    return {
      metered: Math.round((metered / total) * 100),
      profiled: Math.round((profiled / total) * 100),
      flex: Math.round((flex / total) * 100),
    };
  }

  function renderSummary(prodData, consData, priceData) {
    statsGrid.innerHTML = "";

    const peak = findPeakProduction(prodData);
    statsGrid.appendChild(
      createStatCard(
        "PEAK PRODUCTION",
        peak.value.toFixed(1) + " GWh",
        peak.source + " dominant",
        "#4fc3f7"
      )
    );

    const balance = computeNetBalance(prodData, consData);
    const balanceStr = (balance >= 0 ? "+" : "") + balance.toFixed(1) + " GWh";
    const balanceEl = document.createElement("span");
    balanceEl.textContent = balanceStr;
    balanceEl.style.color = balance >= 0 ? "#4caf50" : "#ef5350";
    statsGrid.appendChild(
      createStatCard(
        "NET BALANCE",
        balanceEl,
        balance >= 0 ? "Surplus (export)" : "Deficit (import)",
        balance >= 0 ? "#4caf50" : "#ef5350"
      )
    );

    const avgPrice = computeAvgPrice(priceData);
    statsGrid.appendChild(
      createStatCard(
        "AVG UP-REG PRICE",
        "\u20AC" + avgPrice.toFixed(1) + "/MWh",
        priceData.length + " hours",
        "#1565C0"
      )
    );

    const mix = computeConsumptionMix(consData);
    statsGrid.appendChild(
      createStatCard(
        "CONSUMPTION MIX",
        mix.metered + "% metered",
        mix.profiled + "% profiled / " + mix.flex + "% flex",
        "#E65100"
      )
    );
  }

  function showLoading() {
    document.getElementById("prod-loading").hidden = false;
    document.getElementById("price-loading").hidden = false;
    goBtn.disabled = true;
    goBtn.textContent = "LOADING\u2026";
  }

  function hideLoading() {
    document.getElementById("prod-loading").hidden = true;
    document.getElementById("price-loading").hidden = true;
    goBtn.disabled = false;
    goBtn.textContent = "GO";
  }

  function showError(msg) {
    errorBanner.textContent = msg;
    errorBanner.hidden = false;
  }

  function clearError() {
    errorBanner.hidden = true;
    errorBanner.textContent = "";
  }

  async function loadDashboard() {
    clearError();

    const mba = mbaSelect.value;
    const startStr = startInput.value;
    const endStr = endInput.value;

    if (!mba || !startStr || !endStr) {
      showError("Please select an MBA and date range.");
      return;
    }

    const start = new Date(startStr + "T00:00:00Z");
    const end = new Date(endStr + "T23:59:59Z");

    if (start >= end) {
      showError("Start date must be before end date.");
      return;
    }

    showLoading();

    try {
      const results = await Promise.all([
        fetchProduction(mba, start, end),
        fetchConsumption(mba, start, end),
        fetchPrices(mba, start, end),
      ]);

      const prodData = results[0];
      const consData = results[1];
      const priceData = results[2];

      if (!prodData.length && !consData.length && !priceData.length) {
        statsGrid.innerHTML = "";
        if (productionChart) { productionChart.destroy(); productionChart = null; }
        if (priceChart) { priceChart.destroy(); priceChart = null; }
        showError("No data available for " + mba + " in the selected date range.");
        hideLoading();
        return;
      }

      renderProductionChart(prodData, consData);
      renderPriceChart(priceData);
      renderSummary(prodData, consData, priceData);
    } catch (err) {
      showError(err.message || "Failed to load dashboard data.");
    } finally {
      hideLoading();
    }
  }

  function initControls() {
    mbaSelect = document.getElementById("mba-select");
    startInput = document.getElementById("start-date");
    endInput = document.getElementById("end-date");
    goBtn = document.getElementById("go-btn");
    errorBanner = document.getElementById("error-banner");
    statsGrid = document.getElementById("stats-grid");

    MBA_OPTIONS.forEach((mba) => {
      const opt = document.createElement("option");
      opt.value = mba;
      opt.textContent = mba;
      mbaSelect.appendChild(opt);
    });
    mbaSelect.value = "SE3";

    const now = new Date();
    const end = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 7);
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 14);
    const pad = (n) => String(n).padStart(2, "0");
    const fmt = (d) => d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
    startInput.value = fmt(start);
    endInput.value = fmt(end);

    goBtn.addEventListener("click", loadDashboard);
    errorBanner.addEventListener("click", clearError);

    const onEnter = (e) => { if (e.key === "Enter") loadDashboard(); };
    startInput.addEventListener("keydown", onEnter);
    endInput.addEventListener("keydown", onEnter);
  }

  document.addEventListener("DOMContentLoaded", () => {
    initControls();
    loadDashboard();
  });
})();
