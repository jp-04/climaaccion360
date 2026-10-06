const navToggle = document.querySelector('.nav-toggle');
const navLinks = document.querySelector('.nav-links');

if (navToggle && navLinks) {
    navToggle.addEventListener('click', () => {
        const isOpen = navLinks.classList.toggle('is-open');
        navToggle.setAttribute('aria-expanded', String(isOpen));
    });

    navLinks.querySelectorAll('a').forEach((link) => {
        link.addEventListener('click', () => {
            navLinks.classList.remove('is-open');
            navToggle.setAttribute('aria-expanded', 'false');
        });
    });
}

// Punto de extensión para conectar visualizaciones cuando lleguen datos reales.
window.ClimaAccion = window.ClimaAccion || { charts: {} };
window.ClimaAccion.registerChart = (name, chart) => {
    window.ClimaAccion.charts[name] = chart;
};

const solutionTabs = document.querySelectorAll('[data-solution-tab]');

solutionTabs.forEach((tab) => {
    tab.addEventListener('click', () => {
        const selectedPanel = tab.dataset.solutionTab;

        solutionTabs.forEach((item) => {
            const isSelected = item === tab;
            item.classList.toggle('is-selected', isSelected);
            item.setAttribute('aria-selected', String(isSelected));
        });

        document.querySelectorAll('[role="tabpanel"]').forEach((panel) => {
            const isVisible = panel.id === selectedPanel;
            panel.classList.toggle('is-visible', isVisible);
            panel.hidden = !isVisible;
        });
    });
});

const dashboard = document.querySelector('[data-dashboard="emissions"]');

if (dashboard) {
    const yearFilter = document.querySelector('#year-filter');
    const chart = document.querySelector('#co2-chart');
    const chartMessage = document.querySelector('#chart-message');
    const dataStatus = document.querySelector('#data-status');
    const seriesStatus = document.querySelector('#series-status');
    let emissions = [];

    const setText = (selector, value) => {
        const element = document.querySelector(selector);
        if (element) element.textContent = value;
    };

    const renderStats = (records) => {
        if (!records.length) {
            setText('#stat-first', 'Sin datos disponibles');
            setText('#stat-latest', 'Sin datos disponibles');
            setText('#stat-year', 'Sin datos disponibles');
            setText('#stat-variation', 'Sin datos disponibles');
            setText('#stat-max', 'Sin datos disponibles');
            setText('#stat-min', 'Sin datos disponibles');
            setText('#stat-average', 'Sin datos disponibles');
            return;
        }

        const ordered = [...records].sort((left, right) => left.Año - right.Año);
        const initialValue = ordered[0].Valor;
        const latestValue = ordered[ordered.length - 1].Valor;
        const average = ordered.reduce((total, record) => total + record.Valor, 0) / ordered.length;
        const variation = initialValue === 0 ? null : ((latestValue - initialValue) / Math.abs(initialValue)) * 100;
        setText('#stat-first', `${initialValue} t CO₂ / cápita`);
        setText('#stat-latest', `${latestValue} t CO₂ / cápita`);
        setText('#stat-year', String(ordered[ordered.length - 1].Año));
        setText('#stat-variation', variation === null ? 'No calculable' : `${variation.toFixed(2)} %`);
        setText('#stat-max', `${Math.max(...ordered.map((record) => record.Valor))} t CO₂ / cápita`);
        setText('#stat-min', `${Math.min(...ordered.map((record) => record.Valor))} t CO₂ / cápita`);
        setText('#stat-average', `${average.toFixed(2)} t CO₂ / cápita`);
    };

    const renderChart = (records) => {
        if (!records.length || !window.Plotly) {
            chartMessage.textContent = records.length ? 'Plotly todavía no está disponible en el navegador.' : 'La gráfica se cargará cuando el endpoint reciba datos reales y documentados.';
            chart.classList.remove('has-chart');
            return;
        }

        chart.classList.add('has-chart');
        chartMessage.textContent = '';
        window.Plotly.newPlot(chart, [{
            x: records.map((record) => record.Año),
            y: records.map((record) => record.Valor),
            type: 'scatter',
            mode: 'lines+markers',
            line: { color: '#236b4f', width: 3 },
            marker: { color: '#f07854', size: 8 },
            hovertemplate: '%{x}: %{y}<extra></extra>',
        }], {
            margin: { t: 20, r: 24, b: 45, l: 55 },
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            font: { family: 'DM Mono, monospace', color: '#667570', size: 11 },
            xaxis: { title: 'Año', gridcolor: 'rgba(82, 116, 100, .12)' },
            yaxis: { title: 't CO₂ per cápita', gridcolor: 'rgba(82, 116, 100, .12)' },
        }, { responsive: true, displayModeBar: false });
        window.ClimaAccion.registerChart('co2-series', chart);
    };

    const updateDashboard = () => {
        const selectedYear = yearFilter.value;
        const filtered = selectedYear === 'all' ? emissions : emissions.filter((record) => String(record.Año) === selectedYear);
        renderStats(filtered);
        renderChart(filtered);
    };

    fetch('/api/emisiones')
        .then(async (response) => {
            const payload = await response.json();
            if (!response.ok || payload.status === 'error') throw new Error(payload.error || 'Error desconocido');
            return payload;
        })
        .then((payload) => {
            emissions = payload.data || [];
            (payload.available_years || []).forEach((year) => {
                const option = document.createElement('option');
                option.value = year;
                option.textContent = year;
                yearFilter.appendChild(option);
            });
            dataStatus.textContent = emissions.length ? `Carga exitosa · ${emissions.length} registros` : 'No existen datos para mostrar';
            seriesStatus.textContent = emissions.length ? `${emissions.length} registros · Colombia` : 'Serie histórica Colombia · sin datos cargados';
            updateDashboard();
        })
        .catch((error) => {
            dataStatus.textContent = 'Error en la carga de datos';
            seriesStatus.textContent = 'No se pudo preparar la serie histórica';
            chartMessage.textContent = error.message;
            renderStats([]);
        });

    yearFilter.addEventListener('change', updateDashboard);
}

const predictionForm = document.querySelector('[data-prediction-form]');

if (predictionForm) {
    const results = document.querySelector('#prediction-results');
    const status = document.querySelector('#prediction-status');
    const submitButton = document.querySelector('#prediction-submit');
    const chart = document.querySelector('#prediction-chart');
    const modelLabels = {
        regresion_lineal: 'Regresión lineal',
        arbol_decision: 'Árbol de decisión',
    };

    const setPredictionText = (selector, value) => {
        const element = document.querySelector(selector);
        if (element) element.textContent = value;
    };

    const renderComparisonChart = (historical, prediction, year) => {
        if (!window.Plotly) {
            status.textContent = 'Predicción calculada. Plotly no está disponible para dibujar el gráfico.';
            return;
        }

        const ordered = [...historical].sort((left, right) => left.Año - right.Año);
        chart.classList.add('has-chart');
        window.Plotly.newPlot(chart, [
            {
                x: ordered.map((record) => record.Año),
                y: ordered.map((record) => record.Valor),
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Datos reales',
                line: { color: '#236b4f', width: 3 },
                marker: { color: '#236b4f', size: 6 },
                hovertemplate: '%{x}: %{y:.3f}<extra>Real</extra>',
            },
            {
                x: [year],
                y: [prediction],
                type: 'scatter',
                mode: 'markers',
                name: 'Predicción',
                marker: { color: '#f07854', size: 13, symbol: 'diamond' },
                hovertemplate: '%{x}: %{y:.3f}<extra>Predicción</extra>',
            },
        ], {
            margin: { t: 20, r: 24, b: 48, l: 55 },
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            font: { family: 'DM Mono, monospace', color: '#667570', size: 11 },
            xaxis: { title: 'Año', gridcolor: 'rgba(82, 116, 100, .12)' },
            yaxis: { title: 't CO₂ per cápita', gridcolor: 'rgba(82, 116, 100, .12)' },
            legend: { orientation: 'h', y: 1.12, x: 0 },
        }, { responsive: true, displayModeBar: false });
        window.ClimaAccion.registerChart('ml-comparison', chart);
    };

    predictionForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const model = document.querySelector('#model-select').value;
        const year = Number(document.querySelector('#target-year').value);
        if (!Number.isInteger(year)) {
            status.textContent = 'Introduce un año entero para realizar la predicción.';
            return;
        }

        submitButton.disabled = true;
        status.textContent = 'Entrenando consulta y preparando comparación...';
        try {
            const query = `/api/prediccion?modelo=${encodeURIComponent(model)}&año=${encodeURIComponent(year)}`;
            const [predictionResponse, emissionsResponse] = await Promise.all([fetch(query), fetch('/api/emisiones')]);
            const predictionPayload = await predictionResponse.json();
            const emissionsPayload = await emissionsResponse.json();
            if (!predictionResponse.ok) throw new Error(predictionPayload.error || 'No fue posible calcular la predicción.');
            if (!emissionsResponse.ok || !emissionsPayload.data?.length) throw new Error('No hay datos históricos disponibles para comparar.');

            setPredictionText('#result-prediction', predictionPayload.prediccion.toFixed(3));
            setPredictionText('#result-year', predictionPayload.año);
            setPredictionText('#result-model', modelLabels[predictionPayload.modelo] || predictionPayload.modelo);
            setPredictionText('#result-r2', predictionPayload.metricas.r2.toFixed(3));
            setPredictionText('#result-mae', predictionPayload.metricas.mae.toFixed(3));
            setPredictionText('#result-rmse', predictionPayload.metricas.rmse.toFixed(3));
            results.hidden = false;
            renderComparisonChart(emissionsPayload.data, predictionPayload.prediccion, predictionPayload.año);
            status.textContent = 'Predicción calculada correctamente.';
        } catch (error) {
            results.hidden = true;
            status.textContent = error.message;
        } finally {
            submitButton.disabled = false;
        }
    });
}

const liveMonitor = document.querySelector('[data-live-monitor]');

if (liveMonitor) {
    const timeElement = liveMonitor.querySelector('[data-monitor-time]');
    const dateElement = liveMonitor.querySelector('[data-monitor-date]');
    const cityElement = liveMonitor.querySelector('[data-monitor-city]');
    const temperatureElement = liveMonitor.querySelector('[data-monitor-temperature]');
    const conditionElement = liveMonitor.querySelector('[data-monitor-condition]');
    const humidityElement = liveMonitor.querySelector('[data-monitor-humidity]');
    const windElement = liveMonitor.querySelector('[data-monitor-wind]');
    const iconElement = liveMonitor.querySelector('[data-monitor-icon]');
    const noteElement = liveMonitor.querySelector('.monitor-note');
    const fixedCity = 'Montería, Córdoba';

    cityElement.textContent = fixedCity;

    const updateClock = () => {
        const now = new Date();
        timeElement.textContent = now.toLocaleTimeString('es-CO', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false,
        });
        dateElement.textContent = now.toLocaleDateString('es-CO', {
            day: '2-digit',
            month: 'long',
            year: 'numeric',
        });
    };

    updateClock();
    window.setInterval(updateClock, 1000);

    fetch('/api/clima')
        .then(async (response) => {
            const payload = await response.json();
            if (!response.ok || payload.status !== 'success') {
                throw new Error(payload.error || 'Clima no disponible');
            }
            return payload;
        })
        .then((weather) => {
            cityElement.textContent = fixedCity;
            temperatureElement.textContent = `${weather.temperatura.toFixed(1)} °C`;
            conditionElement.textContent = weather.condicion;
            humidityElement.textContent = `${weather.humedad}%`;
            windElement.textContent = weather.viento ? `${weather.viento} m/s` : '—';
            iconElement.textContent = '✦';
            noteElement.textContent = `Humedad ${weather.humedad}% · API meteorológica conectada`;
        })
        .catch((error) => {
            temperatureElement.textContent = '—';
            conditionElement.textContent = 'No disponible';
            humidityElement.textContent = '—';
            windElement.textContent = '—';
            noteElement.textContent = error.message;
        });
}