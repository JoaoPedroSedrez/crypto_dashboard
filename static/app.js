// ---------------------
// Elementos DOM
// ---------------------
const assetInput = document.getElementById('asset-input');
const searchBtn = document.getElementById('search-btn');
const quickBtns = document.querySelectorAll('.quick-btn');
const resultsSection = document.getElementById('results-section');
const priceCard = document.getElementById('price-card');
const assetNameEl = document.getElementById('asset-name');
const assetTypeEl = document.getElementById('asset-type');
const currentPriceEl = document.getElementById('current-price');
const priceChangeEl = document.getElementById('price-change');
const lastUpdatedEl = document.getElementById('last-updated');
const loadingModal = document.getElementById('loading-modal');
const errorModal = document.getElementById('error-modal');
const errorMessageEl = document.getElementById('error-message');
const periodButtons = document.querySelectorAll('.period-btn');
const technicalAnalysisEl = document.getElementById('technical-analysis');
const predictionAnalysisEl = document.getElementById('prediction-analysis');
const statisticsEl = document.getElementById('statistics');
let chartInstance = null;

// ---------------------
// Funções auxiliares
// ---------------------
function showLoading() {
    loadingModal.style.display = 'flex';
}

function hideLoading() {
    loadingModal.style.display = 'none';
}

function showError(msg) {
    errorMessageEl.textContent = msg;
    errorModal.style.display = 'flex';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function formatPrice(value) {
    return `$${Number(value).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
}

function formatChange(value) {
    const num = Number(value).toFixed(2);
    if (num > 0) return `<span class="price-change positive">+${num}%</span>`;
    if (num < 0) return `<span class="price-change negative">${num}%</span>`;
    return `<span class="price-change">0%</span>`;
}

// ---------------------
// Fetch dados do ativo (sua versão que funcionava)
// ---------------------
async function fetchAssetData(symbol, days=1) {
    try {
        showLoading();
        
        // Buscar dados do preço atual
        const priceRes = await fetch(`/api/v1/price?symbol=${symbol}`);
        if (!priceRes.ok) {
            const errorData = await priceRes.json().catch(() => ({}));
            throw new Error(errorData.detail || `Erro ao buscar dados de ${symbol}`);
        }
        const priceData = await priceRes.json();

        // Se precisar de dados históricos
        let historyData = null;
        if (days > 1) {
            try {
                const historyRes = await fetch(`/api/v1/history?symbol=${symbol}&days=${days}`);
                if (historyRes.ok) {
                    historyData = await historyRes.json();
                }
            } catch (err) {
                console.warn('Erro ao buscar histórico:', err.message);
                // Continue sem dados históricos
            }
        }

        hideLoading();
        return { priceData, historyData };

    } catch (err) {
        hideLoading();
        showError(err.message);
        return null;
    }
}

// ---------------------
// Atualizar UI
// ---------------------
function updatePriceCard(data) {
    assetNameEl.textContent = data.symbol.toUpperCase();
    assetTypeEl.textContent = data.asset_type.toUpperCase();
    currentPriceEl.textContent = formatPrice(data.current_price);
    priceChangeEl.innerHTML = formatChange(data.price_change_24h);
    lastUpdatedEl.textContent = `Última atualização: ${new Date().toLocaleString()}`;
    resultsSection.style.display = 'block';
}

// ---------------------
// Atualizar gráfico
// ---------------------
function updateChart(historyData, symbol, days) {
    if (!historyData || !historyData.prices) {
        // Se não há dados históricos, ocultar seção do gráfico
        const chartSection = document.querySelector('.chart-section');
        if (chartSection) {
            chartSection.style.display = 'none';
        }
        return;
    }

    // Mostrar seção do gráfico
    const chartSection = document.querySelector('.chart-section');
    if (chartSection) {
        chartSection.style.display = 'block';
    }

    const labels = historyData.prices.map(p => new Date(p.timestamp));
    const prices = historyData.prices.map(p => p.price);

    const ctx = document.getElementById('price-chart').getContext('2d');

    if (chartInstance) chartInstance.destroy();

    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: `${symbol.toUpperCase()} - Últimos ${days} dias`,
                data: prices,
                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                borderColor: 'rgba(37, 99, 235, 1)',
                borderWidth: 2,
                pointRadius: 1,
                pointBackgroundColor: 'rgba(37, 99, 235, 1)',
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: days <= 7 ? 'day' : 'day',
                        displayFormats: { day: 'dd MMM' }
                    },
                    grid: { color: '#334155' },
                    ticks: { color: '#94a3b8' }
                },
                y: {
                    grid: { color: '#334155' },
                    ticks: {
                        color: '#94a3b8',
                        callback: (val) => formatPrice(val)
                    }
                }
            }
        }
    });
}

// Função para atualizar estatísticas
function updateStatistics(historyData) {
    if (!historyData || !historyData.statistics) {
        statisticsEl.innerHTML = '<div class="no-data">Dados estatísticos não disponíveis</div>';
        return;
    }

    const stats = historyData.statistics;
    
    statisticsEl.innerHTML = `
        <div class="stats-grid">
            <div class="stat-item">
                <label>Preço Mín:</label>
                <span>${formatPrice(stats.min_price)}</span>
            </div>
            <div class="stat-item">
                <label>Preço Máx:</label>
                <span>${formatPrice(stats.max_price)}</span>
            </div>
            <div class="stat-item">
                <label>Preço Médio:</label>
                <span>${formatPrice(stats.avg_price)}</span>
            </div>
            <div class="stat-item">
                <label>Variação:</label>
                <span class="${stats.total_change_percent >= 0 ? 'positive' : 'negative'}">
                    ${stats.total_change_percent >= 0 ? '+' : ''}${Number(stats.total_change_percent).toFixed(2)}%
                </span>
            </div>
            <div class="stat-item">
                <label>Volatilidade:</label>
                <span>${Number(stats.volatility).toFixed(2)}%</span>
            </div>
            <div class="stat-item">
                <label>Pontos:</label>
                <span>${historyData.data_points}</span>
            </div>
        </div>
    `;
}

// Carregar análises (opcional)
async function loadAnalysisData(symbol) {
    try {
        // Análise técnica
        technicalAnalysisEl.innerHTML = '<div class="loading">Carregando análise técnica...</div>';
        const techRes = await fetch(`/api/v1/prediction/analysis?symbol=${symbol}&days=14`);
        if (techRes.ok) {
            const techData = await techRes.json();
            const indicators = techData.technical_indicators;
            const signals = techData.signals;
            
            technicalAnalysisEl.innerHTML = `
                <div class="indicators-grid">
                    <div class="indicator">
                        <label>SMA 7:</label>
                        <span>${formatPrice(indicators.sma_7)}</span>
                    </div>
                    <div class="indicator">
                        <label>SMA 14:</label>
                        <span>${formatPrice(indicators.sma_14)}</span>
                    </div>
                    <div class="indicator">
                        <label>RSI:</label>
                        <span class="rsi-value">${Number(indicators.rsi).toFixed(1)}</span>
                    </div>
                </div>
                <div class="signals">
                    <h4>Sinais:</h4>
                    <ul>
                        ${signals.slice(0, 3).map(signal => `<li>${signal}</li>`).join('')}
                    </ul>
                </div>
            `;
        } else {
            technicalAnalysisEl.innerHTML = '<div class="error">Análise técnica não disponível</div>';
        }

        // Previsão
        predictionAnalysisEl.innerHTML = '<div class="loading">Carregando previsão...</div>';
        const predRes = await fetch(`/api/v1/prediction?symbol=${symbol}&days=3`);
        if (predRes.ok) {
            const predData = await predRes.json();
            const summary = predData.summary;
            
            predictionAnalysisEl.innerHTML = `
                <div class="prediction-summary">
                    <div class="trend-info">
                        <span class="trend-emoji">${summary.trend_emoji}</span>
                        <span class="trend-text">${summary.trend}</span>
                        <span class="trend-change">${formatChange(summary.total_change_percent)}</span>
                    </div>
                </div>
                <div class="predictions-list">
                    <h4>Próximos 3 dias:</h4>
                    ${predData.predictions.map(pred => `
                        <div class="prediction-item">
                            <span class="pred-date">${pred.date}</span>
                            <span class="pred-price">${formatPrice(pred.predicted_price)}</span>
                        </div>
                    `).join('')}
                </div>
                <div class="disclaimer">
                    <small>Apenas para fins educacionais</small>
                </div>
            `;
        } else {
            predictionAnalysisEl.innerHTML = '<div class="error">Previsão não disponível</div>';
        }

    } catch (error) {
        console.error('Erro ao carregar análises:', error);
        technicalAnalysisEl.innerHTML = '<div class="error">Erro ao carregar análise</div>';
        predictionAnalysisEl.innerHTML = '<div class="error">Erro ao carregar previsão</div>';
    }
}

// ---------------------
// Buscar e atualizar tudo (sua função original melhorada)
// ---------------------
async function loadAsset(symbol, days=7) {
    const result = await fetchAssetData(symbol, days);
    if (!result) return;

    const { priceData, historyData } = result;

    // Atualizar card de preço
    updatePriceCard(priceData);

    // Atualizar gráfico e estatísticas se há dados históricos
    if (historyData) {
        updateChart(historyData, priceData.symbol, days);
        updateStatistics(historyData);
    } else {
        // Ocultar seção do gráfico se não há dados
        const chartSection = document.querySelector('.chart-section');
        if (chartSection) chartSection.style.display = 'none';
        statisticsEl.innerHTML = '<div class="no-data">Dados estatísticos não disponíveis</div>';
    }

    // Carregar análises em background (opcional)
    loadAnalysisData(symbol);
}

// ---------------------
// Eventos
// ---------------------
searchBtn.addEventListener('click', () => {
    const symbol = assetInput.value.trim();
    if (!symbol) return showError('Digite um símbolo válido');
    loadAsset(symbol, getSelectedDays());
});

assetInput.addEventListener('keyup', (e) => {
    if (e.key === 'Enter') searchBtn.click();
});

quickBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        let symbol = btn.dataset.symbol;
        
        // Mapear símbolos para a API correta
        if (btn.classList.contains('crypto-btn')) {
            const cryptoMap = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum',
                'DOGE': 'dogecoin'
            };
            symbol = cryptoMap[symbol.toUpperCase()] || symbol.toLowerCase();
        }
        
        assetInput.value = symbol;
        loadAsset(symbol, getSelectedDays());
    });
});

periodButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        periodButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const days = getSelectedDays();
        const symbol = assetNameEl.textContent;
        if (symbol && symbol !== '-') {
            // Usar o símbolo original do input
            const originalSymbol = assetInput.value || symbol.toLowerCase();
            loadAsset(originalSymbol, days);
        }
    });
});

function getSelectedDays() {
    const activeBtn = document.querySelector('.period-btn.active');
    return activeBtn ? Number(activeBtn.dataset.days) : 7;
}

// Fechar modals
document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
});

// ---------------------
// Inicialização
// ---------------------
document.addEventListener('DOMContentLoaded', () => {

    // Atualizar contagem de ativos
    const cryptoButtons = document.querySelectorAll('.quick-btn.crypto-btn').length;
    const stockButtons = document.querySelectorAll('.quick-btn.stock-btn').length;
    const fiiButtons = document.querySelectorAll('.quick-btn.fii-btn').length;

    document.getElementById('crypto-count').innerText = cryptoButtons;
    document.getElementById('stock-count').innerText = stockButtons;
    document.getElementById('fii-count').innerText = fiiButtons;

    document.getElementById('total-assets').innerText = cryptoButtons + stockButtons + fiiButtons;
    document.querySelector('.stat-card span#total-assets').nextElementSibling.innerText = 'Ativos Favoritos';

    // Carregar primeiro ativo (BTC/bitcoin)
    const quickBtns = document.querySelectorAll('.quick-btn');
    if (quickBtns.length > 0) {
        quickBtns[0].click();
    }
});





