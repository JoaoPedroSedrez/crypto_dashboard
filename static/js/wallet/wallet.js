    const transactionModal = document.getElementById('transaction-modal');
    const transactionForm = document.getElementById('transaction-form');

    

    // Abrir modal
    function openAddTransactionModal() {
        transactionModal.style.display = 'block';
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
        const grid = document.getElementById('holdings-grid');
        grid.innerHTML = '<div class="loading">Carregando holdings...</div>';

        try {
            const res = await fetch('/api/v1/wallet/holdings');
            const data = await res.json();

            if (data.assets && data.assets.length) {
                grid.innerHTML = '';
                data.assets.forEach(asset => {
                    const card = document.createElement('div');
                    card.className = 'holding-card';
                    card.innerHTML = `
                        <div class="holding-header">
                            <div class="asset-info">
                                <div class="asset-symbol">${asset.symbol}</div>
                                <div class="asset-type">
                                    ${asset.asset_type === 'stock' ? 'Ação' : asset.asset_type === 'fii' ? 'Fundo imobiliário' : asset.asset_type}
                                </div>
                            </div>
                            <div class="stat-value">R$${asset.current_value.toFixed(2)}</div>
                        </div>
                        <div class="holding-stats">
                            <div class="stat-item">
                                <div class="stat-label">Quantidade</div>
                                <div class="stat-value">${asset.total_quantity}</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-label">Preço Atual</div>
                                <div class="stat-value">R$${asset.current_price.toFixed(2)}</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-label">Preço Médio</div>
                                <div class="stat-value">R$${asset.average_buy_price.toFixed(2)}</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-label">P&L</div>
                                <div class="stat-value ${asset.profit_loss >= 0 ? 'positive' : 'negative'}">R$${asset.profit_loss.toFixed(2)} (${asset.profit_loss_percent.toFixed(2)}%)</div>
                            </div>
                        </div>
                    `;
                    grid.appendChild(card);
                });

                // Atualizar resumo
                const totalValueAccount = data.summary.total_value;
                document.getElementById('total-value').innerText = `R$${totalValueAccount.toFixed(2)}`;

                const totalValueInvested = data.summary.total_invested;
                document.getElementById('total-invested').innerText = `R$${totalValueInvested.toFixed(2)}`;

                const totalAssetsAccount = data.summary.assets_count;
                document.getElementById('assets-count').innerText = totalAssetsAccount;

                const totalPnL = data.summary.total_profit_loss;
                document.getElementById('total-pnl').innerText = `R$${totalPnL.toFixed(2)}`;
                
                const totalPLPercent = data.summary.total_profit_loss_percent;
                const pnlPercentEl = document.getElementById('total-pnl-percent');

                pnlPercentEl.classList.remove('positive', 'negative');

                pnlPercentEl.classList.add(totalPLPercent >= 0 ? 'positive' : 'negative');

                pnlPercentEl.innerText = `${totalPLPercent.toFixed(2)}%`;

            } else {
                grid.innerHTML = '<div class="empty-state"><i class="fas fa-coins"></i><p>Nenhum ativo encontrado</p></div>';
            }
        } catch (err) {
            console.error(err);
            grid.innerHTML = '<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>Erro ao carregar holdings</p></div>';
        }
    }


    // Carregar dados ao iniciar
    window.onload = () => refreshWallet();