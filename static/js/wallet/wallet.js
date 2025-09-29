
const transactionModal = document.getElementById('transaction-modal');
const transactionForm = document.getElementById('transaction-form');

// Abrir modal
function openAddTransactionModal() {
    transactionModal.style.display = 'flex';
}

// Fechar modal
function closeTransactionModal() {
    transactionModal.style.display = 'none';
    transactionForm.reset();
}

// Fechar modal ao clicar fora
window.onclick = function(event) {
    if (event.target == transactionModal) {
        closeTransactionModal();
    }
}

// Submeter formulário
transactionForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const data = {
        symbol: document.getElementById('symbol').value.trim(),
        transaction_type: document.getElementById('transaction-type').value,
        quantity: parseFloat(document.getElementById('quantity').value),
        price_per_unit: parseFloat(document.getElementById('price-per-unit').value),
        total_value: parseFloat(document.getElementById('quantity').value) * parseFloat(document.getElementById('price-per-unit').value),
        asset_type: document.getElementById('asset-type').value,
        date: new Date(document.getElementById('transaction-date').value).toISOString(),
    };

    try {
        const res = await fetch('/api/v1/wallet/transactions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();

        if (res.ok) {
            alert(result.message || 'Transação adicionada com sucesso');
            closeTransactionModal();
            refreshWallet();
        } else {
            alert(result.detail || 'Erro ao adicionar transação');
        }
    } catch (err) {
        console.error(err);
        alert('Erro na requisição');
    }
});

// Atualizar holdings e transações
async function refreshWallet() {
    await loadHoldings();
}

async function loadHoldings() {
    const stocksTableBody = document.getElementById('stocks-table-body');
    const fiisTableBody = document.getElementById('fiis-table-body');
    
    stocksTableBody.innerHTML = '<tr><td colspan="6" class="loading">Carregando ações...</td></tr>';
    fiisTableBody.innerHTML = '<tr><td colspan="6" class="loading">Carregando FIIs...</td></tr>';

    try {
        const res = await fetch('/api/v1/wallet/holdings');
        const data = await res.json();

        if (data.assets && data.assets.length) {
            // Separar ativos por tipo
            const stocks = data.assets.filter(asset => asset.asset_type === 'stock');
            const fiis = data.assets.filter(asset => asset.asset_type === 'fii');

            // Renderizar ações
            if (stocks.length > 0) {
                stocksTableBody.innerHTML = '';
                stocks.forEach(asset => {
                    const row = document.createElement('tr');
                    const pnlClass = asset.profit_loss >= 0 ? 'pnl-positive' : 'pnl-negative';
                    const pnlSign = asset.profit_loss >= 0 ? '+' : '';
                    
                    row.innerHTML = `
                        <td class="ticker-cell">${asset.symbol}</td>
                        <td class="quantity-cell">${asset.total_quantity}</td>
                        <td class="value-cell">R$ ${asset.current_value.toFixed(2)}</td>
                        <td class="price-cell">R$ ${asset.current_price.toFixed(2)}</td>
                        <td class="price-cell">R$ ${asset.average_buy_price.toFixed(2)}</td>
                        <td class="pnl-cell ${pnlClass}">${pnlSign}R$ ${asset.profit_loss.toFixed(2)} (${pnlSign}${asset.profit_loss_percent.toFixed(2)}%)</td>
                    `;
                    stocksTableBody.appendChild(row);
                });
            } else {
                stocksTableBody.innerHTML = '<tr><td colspan="6" class="empty-state">Nenhuma ação encontrada</td></tr>';
            }

            // Renderizar FIIs
            if (fiis.length > 0) {
                fiisTableBody.innerHTML = '';
                fiis.forEach(asset => {
                    const row = document.createElement('tr');
                    const pnlClass = asset.profit_loss >= 0 ? 'pnl-positive' : 'pnl-negative';
                    const pnlSign = asset.profit_loss >= 0 ? '+' : '';
                    
                    row.innerHTML = `
                        <td class="ticker-cell">${asset.symbol}</td>
                        <td class="quantity-cell">${asset.total_quantity}</td>
                        <td class="value-cell">R$ ${asset.current_value.toFixed(2)}</td>
                        <td class="price-cell">R$ ${asset.current_price.toFixed(2)}</td>
                        <td class="price-cell">R$ ${asset.average_buy_price.toFixed(2)}</td>
                        <td class="pnl-cell ${pnlClass}">${pnlSign}R$ ${asset.profit_loss.toFixed(2)} (${pnlSign}${asset.profit_loss_percent.toFixed(2)}%)</td>
                    `;
                    fiisTableBody.appendChild(row);
                });
            } else {
                fiisTableBody.innerHTML = '<tr><td colspan="6" class="empty-state">Nenhum FII encontrado</td></tr>';
            }

            // Atualizar resumo
            document.getElementById('total-value').innerText = `R$ ${data.summary.total_value.toFixed(2)}`;
            document.getElementById('total-invested').innerText = `R$ ${data.summary.total_invested.toFixed(2)}`;
            document.getElementById('assets-count').innerText = data.summary.assets_count;
            document.getElementById('total-pnl').innerText = `R$ ${data.summary.total_profit_loss.toFixed(2)}`;
            
            const pnlPercentEl = document.getElementById('total-pnl-percent');
            const roundedPercent = Number(data.summary.total_profit_loss_percent.toFixed(2));
            
            pnlPercentEl.classList.remove('positive', 'negative');
            if (roundedPercent > 0) {
                pnlPercentEl.classList.add('positive');
                pnlPercentEl.innerText = `+${roundedPercent}%`;
            } else if (roundedPercent < 0) {
                pnlPercentEl.classList.add('negative');
                pnlPercentEl.innerText = `${roundedPercent}%`;
            } else {
                pnlPercentEl.innerText = `${roundedPercent}%`;
            }

            renderCharts(stocks, fiis);


        } else {
            stocksTableBody.innerHTML = '<tr><td colspan="6" class="empty-state">Nenhuma ação encontrada</td></tr>';
            fiisTableBody.innerHTML = '<tr><td colspan="6" class="empty-state">Nenhum FII encontrado</td></tr>';
        }
    } catch (err) {
        console.error(err);
        stocksTableBody.innerHTML = '<tr><td colspan="6" class="empty-state">Erro ao carregar ações</td></tr>';
        fiisTableBody.innerHTML = '<tr><td colspan="6" class="empty-state">Erro ao carregar FIIs</td></tr>';
    }
}

let overallChart, stocksChart, fiisChart;

const chartColors = [
    '#22d3ee', // cyan
    '#f472b6', // rosa
    '#fcd34d', // amarelo
    '#34d399', // verde
    '#818cf8', // azul suave
    '#f87171'  // vermelho suave
];


function renderCharts(stocks, fiis) {
    // Valores gerais
    const totalStocksValue = stocks.reduce((sum, a) => sum + a.current_value, 0);
    const totalFiisValue = fiis.reduce((sum, a) => sum + a.current_value, 0);

    // Apagar gráficos antigos
    if (overallChart) overallChart.destroy();
    if (stocksChart) stocksChart.destroy();
    if (fiisChart) fiisChart.destroy();

    // Gráfico geral (Ações x FIIs)
    const overallCtx = document.getElementById('overallChart').getContext('2d');
    overallChart = new Chart(overallCtx, {
        type: 'pie',
        data: {
            labels: ['Ações', 'FIIs'],
            datasets: [{
                data: [totalStocksValue, totalFiisValue],
                backgroundColor: ['#4ade80', '#60a5fa']
            }]
        },
        options: {
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                        const value = context.raw;
                        const label = context.label;
                        const dataset = context.dataset.data;
                        const total = dataset.reduce((a, b) => a + b, 0);
                        const percentage = ((value / total) * 100).toFixed(2);

                        return `${label}: R$ ${value.toLocaleString('pt-BR', { minimumFractionDigits: 2 })} (${percentage}%)`;
                        }
                    }
                },
                datalabels: {
                    color: '#fff',
                    font: {
                        weight: 'bold'
                    },
                    formatter: (value, context) => {
                        const label = context.chart.data.labels[context.dataIndex];
                        return label
                    }
                }
            }
        },
        plugins: [ChartDataLabels]
    });

    // Gráfico de Ações
const stocksCtx = document.getElementById('stocksChart').getContext('2d');
stocksChart = new Chart(stocksCtx, {
    type: 'pie',
    data: {
        labels: stocks.map(a => a.symbol),
        datasets: [{
            data: stocks.map(a => a.current_value),
            backgroundColor: stocks.map((_, i) => chartColors[i % chartColors.length])
        }]
    },
    options: {
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        const value = context.raw;
                        const label = context.label;
                        const dataset = context.dataset.data;
                        const total = dataset.reduce((a, b) => a + b, 0);
                        const percentage = ((value / total) * 100).toFixed(2);
                        return `${label}: R$ ${value.toLocaleString('pt-BR', {minimumFractionDigits: 2})} (${percentage}%)`;
                    }
                }
            },
            datalabels: {
                color: '#fff',
                font: {
                    weight: 'bold',
                    size: 12
                },
                formatter: (value, context) => {
                    const dataset = context.chart.data.datasets[0].data;
                    const total = dataset.reduce((a, b) => a + b, 0);
                    const percentage = (value / total) * 100;
                    return percentage >= 10
                        ? context.chart.data.labels[context.dataIndex] 
                        : '';
                }
            }
        }
    },
    plugins: [ChartDataLabels]
});

// Gráfico de FIIs
const fiisCtx = document.getElementById('fiisChart').getContext('2d');
fiisChart = new Chart(fiisCtx, {
    type: 'pie',
    data: {
        labels: fiis.map(a => a.symbol),
        datasets: [{
            data: fiis.map(a => a.current_value),
            backgroundColor: fiis.map((_, i) => chartColors[i % chartColors.length])
        }]
    },
    options: {
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        const value = context.raw;
                        const label = context.label;
                        const dataset = context.dataset.data;
                        const total = dataset.reduce((a, b) => a + b, 0);
                        const percentage = ((value / total) * 100).toFixed(2);
                        return `${label}: R$ ${value.toLocaleString('pt-BR', {minimumFractionDigits: 2})} (${percentage}%)`;
                    }
                }
            },
            datalabels: {
                color: '#fff',
                font: {
                    weight: 'bold',
                    size: 12
                },
                formatter: (value, context) => {
                    const dataset = context.chart.data.datasets[0].data;
                    const total = dataset.reduce((a, b) => a + b, 0);
                    const percentage = (value / total) * 100;
                    return percentage >= 10 
                        ? context.chart.data.labels[context.dataIndex] 
                        : '';
                }
            }
        }
    },
    plugins: [ChartDataLabels]
});

    
}


// Carregar dados ao iniciar
window.onload = () => refreshWallet();
