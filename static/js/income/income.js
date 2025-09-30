const incomeModal = document.getElementById('income-modal');
const incomeForm = document.getElementById('income-form');
const incomeTableBody = document.getElementById('income-table-body');
const deleteModal = document.getElementById('delete-modal');
let currentIncomeId = null;
let incomeToDelete = null;

// =============================================================================
// 1. GESTÃO DO MODAL DE ADICIONAR/EDITAR
// =============================================================================

function openAddIncomeModal() {
    currentIncomeId = null;
    incomeForm.reset();
    
    // Define a data de pagamento para hoje por padrão
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('payment-date').value = today;
    
    // Habilita todas as opções de tipo de provento
    const incomeTypeSelect = document.getElementById('income-type');
    Array.from(incomeTypeSelect.options).forEach(opt => opt.disabled = false);

    incomeModal.style.display = 'flex';
}

function openEditIncomeModal(income) {
    currentIncomeId = income.id;

    // Preenche o formulário
    document.getElementById('asset-code').value = income.asset_code;
    document.getElementById('asset-type').value = income.asset_type;
    document.getElementById('income-type').value = income.income_type;
    document.getElementById('quantity').value = income.quantity;
    document.getElementById('value-per-unit').value = income.value_per_unit;
    
    // Formatação da data ISO para input[type="date"]
    const paymentDate = new Date(income.payment_date).toISOString().split('T')[0];
    document.getElementById('payment-date').value = paymentDate;
    
    // Ajusta as opções de tipo de provento baseado no tipo de ativo
    updateIncomeTypeOptions(income.asset_type);

    incomeModal.style.display = 'flex';
}

function closeIncomeModal() {
    incomeModal.style.display = 'none';
    incomeForm.reset();
    currentIncomeId = null;
}

// =============================================================================
// 2. GESTÃO DO MODAL DE EXCLUSÃO
// =============================================================================

function openDeleteModal(id, assetCode) {
    incomeToDelete = { id, assetCode };
    deleteModal.style.display = 'flex';
}

function closeDeleteModal() {
    deleteModal.style.display = 'none';
    incomeToDelete = null;
}

async function confirmDelete() {
    if (!incomeToDelete) return;
    
    try {
        const res = await fetch(`/api/v1/income/${incomeToDelete.id}`, {
            method: 'DELETE'
        });
        const result = await res.json();

        if (res.ok) {
            alert(result.message || 'Provento removido com sucesso!');
            closeDeleteModal();
            loadIncomes();
        } else {
            alert(result.detail || 'Erro ao remover provento.');
        }

    } catch (err) {
        console.error("Erro ao deletar provento:", err);
        alert('Erro na requisição de exclusão.');
    }
}

// Adiciona evento ao botão de confirmar exclusão
document.getElementById('confirm-delete-btn')?.addEventListener('click', confirmDelete);

// =============================================================================
// 3. AJUSTE DINÂMICO DE TIPO DE PROVENTO
// =============================================================================

// Atualiza as opções de tipo de provento baseado no tipo de ativo selecionado
function updateIncomeTypeOptions(assetType) {
    const incomeTypeSelect = document.getElementById('income-type');
    const dividendsOpt = incomeTypeSelect.querySelector('option[value="dividends"]');
    const jcpOpt = incomeTypeSelect.querySelector('option[value="jcp"]');
    const yieldOpt = incomeTypeSelect.querySelector('option[value="yield"]');
    
    if (assetType === 'stock') {
        // Para ações: habilita Dividendos e JCP, desabilita Rendimento
        if (dividendsOpt) dividendsOpt.disabled = false;
        if (jcpOpt) jcpOpt.disabled = false;
        if (yieldOpt) {
            yieldOpt.disabled = true;
            if (incomeTypeSelect.value === 'yield') {
                incomeTypeSelect.value = '';
            }
        }
    } else if (assetType === 'fii') {
        // Para FIIs: habilita apenas Rendimento, desabilita Dividendos e JCP
        if (yieldOpt) yieldOpt.disabled = false;
        if (dividendsOpt) {
            dividendsOpt.disabled = true;
            if (incomeTypeSelect.value === 'dividends') {
                incomeTypeSelect.value = '';
            }
        }
        if (jcpOpt) {
            jcpOpt.disabled = true;
            if (incomeTypeSelect.value === 'jcp') {
                incomeTypeSelect.value = '';
            }
        }
    } else {
        // Se não houver tipo selecionado, habilita tudo
        if (dividendsOpt) dividendsOpt.disabled = false;
        if (jcpOpt) jcpOpt.disabled = false;
        if (yieldOpt) yieldOpt.disabled = false;
    }
}

// Listener para mudança de tipo de ativo
document.getElementById('asset-type')?.addEventListener('change', function() {
    updateIncomeTypeOptions(this.value);
});

// =============================================================================
// 4. SUBMISSÃO DO FORMULÁRIO (CRIAR/EDITAR)
// =============================================================================

incomeForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const isEditing = !!currentIncomeId;
    
    const data = {
        asset_code: document.getElementById('asset-code').value.trim().toUpperCase(),
        asset_type: document.getElementById('asset-type').value,
        income_type: document.getElementById('income-type').value,
        quantity: parseFloat(document.getElementById('quantity').value),
        value_per_unit: parseFloat(document.getElementById('value-per-unit').value),
        payment_date: new Date(document.getElementById('payment-date').value).toISOString(),
    };

    if (isEditing) {
        data.id = currentIncomeId;
    }

    const method = isEditing ? 'PUT' : 'POST';
    const url = '/api/v1/income/';

    try {
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();

        if (res.ok) {
            alert(result.message || `Provento ${isEditing ? 'atualizado' : 'adicionado'} com sucesso!`);
            closeIncomeModal();
            loadIncomes();
        } else {
            alert(result.detail || `Erro ao ${isEditing ? 'atualizar' : 'adicionar'} provento.`);
        }
    } catch (err) {
        console.error(err);
        alert('Erro na requisição da API.');
    }
});

// =============================================================================
// 5. CARREGAMENTO DE DADOS
// =============================================================================

async function loadIncomes() {
    incomeTableBody.innerHTML = '<tr><td colspan="8" class="loading">Carregando proventos...</td></tr>';
    
    try {
        const res = await fetch('/api/v1/income/');
        const data = await res.json();
        
        if (res.ok) {
            renderSummary(data.summary);
            renderIncomeTable(data.incomes);
        } else {
            incomeTableBody.innerHTML = '<tr><td colspan="8" class="empty-state">Erro ao carregar proventos.</td></tr>';
            alert(data.detail || "Falha ao buscar proventos.");
        }
    } catch (err) {
        console.error("Erro na requisição de proventos:", err);
        incomeTableBody.innerHTML = '<tr><td colspan="8" class="empty-state">Erro de conexão com a API.</td></tr>';
    }
}

// =============================================================================
// 6. RENDERIZAÇÃO
// =============================================================================

function formatCurrency(value) {
    return `R$ ${value.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleDateString('pt-BR', { year: 'numeric', month: '2-digit', day: '2-digit' });
}

function renderSummary(summary) {
    document.getElementById('total-income').innerText = formatCurrency(summary.total_income);
    document.getElementById('income-stocks').innerText = formatCurrency(summary.income_stocks);
    document.getElementById('income-fiis').innerText = formatCurrency(summary.income_fiis);
    
    const lastMonthEl = document.getElementById('income-last-month');
    lastMonthEl.innerText = formatCurrency(summary.income_last_month);
    
    lastMonthEl.classList.remove('positive', 'negative');
    if (summary.income_last_month > 0) {
         lastMonthEl.classList.add('positive');
    }
}

function renderIncomeTable(incomes) {
    incomeTableBody.innerHTML = '';

    if (incomes.length === 0) {
        incomeTableBody.innerHTML = '<tr><td colspan="8" class="empty-state"><i class="fas fa-hand-holding-usd"></i><p>Nenhum provento registrado ainda.</p></td></tr>';
        return;
    }

    incomes.forEach(income => {
        const row = document.createElement('tr');
        
        let incomeLabel = '';
        if (income.income_type === 'dividends') {
            incomeLabel = 'Dividendo';
        } else if (income.income_type === 'jcp') {
            incomeLabel = 'JCP';
        } else if (income.income_type === 'yield') {
            incomeLabel = 'Rendimento';
        }

        // Escapar dados para JSON dentro do HTML
        const incomeJson = JSON.stringify(income).replace(/'/g, '&apos;');

        row.innerHTML = `
            <td class="ticker-cell">${formatDate(income.payment_date)}</td>
            <td class="ticker-cell">${income.asset_code}</td>
            <td class="quantity-cell">${income.asset_type === 'stock' ? 'Ação' : 'FII'}</td>
            <td>${incomeLabel}</td>
            <td class="quantity-cell">${income.quantity.toFixed(0)}</td>
            <td class="price-cell">${formatCurrency(income.value_per_unit)}</td>
            <td class="value-cell pnl-positive">${formatCurrency(income.total_value)}</td>
            <td class="actions-cell">
                <button class="btn btn-action btn-edit" onclick='openEditIncomeModal(${incomeJson})' title="Editar">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-action btn-delete" onclick="openDeleteModal('${income.id}', '${income.asset_code}')" title="Excluir">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </td>
        `;
        incomeTableBody.appendChild(row);
    });
}

// =============================================================================
// 7. FECHAR MODAIS AO CLICAR FORA
// =============================================================================

window.onclick = function(event) {
    if (event.target === incomeModal) {
        closeIncomeModal();
    }
    if (event.target === deleteModal) {
        closeDeleteModal();
    }
}

// =============================================================================
// 8. FUNCIONALIDADE DE ABRIR/FECHAR TABELA
// =============================================================================

function toggleIncomeTable() {
    const wrapper = document.getElementById('income-table-wrapper');
    const icon = document.getElementById('table-toggle-icon');
    
    if (!wrapper || !icon) {
        console.error('Elementos não encontrados: income-table-wrapper ou table-toggle-icon');
        return;
    }
    
    wrapper.classList.toggle('collapsed');
    icon.classList.toggle('rotated');
}

// Opcional: Iniciar com a tabela fechada ao carregar a página
// Descomente as linhas abaixo se quiser que a tabela inicie recolhida

window.addEventListener('DOMContentLoaded', function() {
    const wrapper = document.getElementById('income-table-wrapper');
    const icon = document.getElementById('table-toggle-icon');
    
    if (wrapper && icon) {
        wrapper.classList.add('collapsed');
        icon.classList.add('rotated');
    }
});


// =============================================================================
// 9. INICIALIZAÇÃO
// =============================================================================

window.onload = () => {
    loadIncomes();
};