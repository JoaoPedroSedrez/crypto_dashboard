# 🚀 Crypto Dashboard

Um dashboard completo para consulta de preços, histórico e previsões de criptomoedas e ações em tempo real.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![MongoDB](https://img.shields.io/badge/MongoDB-4.4+-brightgreen.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Funcionalidades

### Crypto Dashboard

- 📊 **Preços em tempo real** de criptomoedas e ações
- 📈 **Gráficos interativos** com histórico de preços
- 🔮 **Previsões** usando machine learning (regressão linear)
- 📋 **Análise técnica** com indicadores como RSI, médias móveis
- 🌐 **API REST** completa com documentação automática
- 💾 **Cache inteligente** com MongoDB
- 🎨 **Interface moderna** e responsiva
- ⚡ **Performance otimizada** com tempo de resposta < 1s

### myWallet
- 💰 **Gerenciamento de portfólio** de ações e FIIs
- ➕ **Adicionar, listar e remover transações** (compra/venda)
- 📊 **Resumo executivo** do wallet (valor total, investido, P&L)
- 🔄 **Atualização automática** dos preços e P&L dos ativos
- 🏆 **Identificação do melhor e pior desempenho** no portfólio

## 🛠️ Tecnologias Utilizadas

### Backend
- **FastAPI** - Framework web moderno e rápido
- **Python 3.8+** - Linguagem principal
- **MongoDB** - Banco de dados NoSQL para cache
- **yfinance** - Dados de ações em tempo real
- **CoinGecko API** - Dados de criptomoedas
- **scikit-learn** - Machine learning para previsões
- **pandas** - Manipulação de dados
- **matplotlib** - Geração de gráficos

### Frontend
- **HTML5/CSS3** - Interface responsiva
- **JavaScript ES6+** - Interatividade
- **Chart.js** - Gráficos interativos
- **Font Awesome** - Ícones

## 🚀 Instalação e Setup

### Pré-requisitos
- Python 3.8 ou superior
- MongoDB 4.4 ou superior
- Git

### 1. Clonar o repositório
```bash
git clone <seu-repositorio>
cd crypto_dashboard
```

### 2. Criar ambiente virtual
```bash
python -m venv venv

# Windows
venv\\Scripts\\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar MongoDB

**Windows:**
1. Baixe e instale o MongoDB Community Server
2. Inicie o serviço MongoDB
3. MongoDB rodará em `mongodb://localhost:27017`

**Linux/Mac:**
```bash
# Ubuntu/Debian
sudo apt install mongodb

# Mac (Homebrew)
brew install mongodb-community
brew services start mongodb-community
```

### 5. Configurar variáveis de ambiente
```bash
cp .env.example .env
# Edite o arquivo .env conforme necessário
```

### 6. Executar a aplicação
```bash
python main.py
```

A aplicação estará disponível em: http://localhost:8000

## 📡 Endpoints da API

### Preços
- `GET /api/v1/price?symbol=BTC` - Preço atual de um ativo
- `GET /api/v1/price/multiple?symbols=BTC,ETH,AAPL` - Múltiplos preços

### Histórico
- `GET /api/v1/history?symbol=BTC&days=30` - Histórico de preços
- `GET /api/v1/history/summary` - Resumo do mercado

### Previsões
- `GET /api/v1/prediction?symbol=BTC&days=3` - Previsão de preços
- `GET /api/v1/prediction/analysis?symbol=BTC` - Análise técnica

### Sistema
- `GET /health` - Status da aplicação
- `GET /api/v1/assets` - Ativos suportados
- `GET /api/v1/status` - Status detalhado da API


### myWallet
- `POST /api/v1/wallet/transactions`- Adicionar transação
- `GET /api/v1/wallet/transactions` - Listar transação
- `GET /api/v1/wallet/holdings` - Listar ativos e valores atualizados
- `GET /api/v1/wallet/summary` - Resumo do myWallet