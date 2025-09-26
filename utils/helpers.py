from utils.db import DatabaseManager
import logging
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timedelta
from pymongo import MongoClient
from config import Config
import matplotlib.pyplot as plt
import base64
import io

# Configurar logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataFetcher:
    def __init__(self):
        self.db = DatabaseManager()
    
    def _is_brazilian_asset(self, symbol):
        """Verifica se é um ativo brasileiro"""
        return symbol.upper().endswith(".SA") 
    
    def _get_currency_info(self, symbol):
        """Retorna informações de moeda baseado no símbolo"""
        if self._is_brazilian_asset(symbol):
            return "BRL", "R$"
        return "USD", "$"
    
    def fetch_crypto_data(self, symbol, days=1):
        """Busca dados de criptomoeda via CoinGecko"""
        try:
            # Verificar cache primeiro (apenas para dados atuais)
            if days == 1:
                cached_data = self.db.get_cached_data(symbol)
                if cached_data:
                    return cached_data
            
            if days == 1:
                # Dados atuais - usar endpoint simples
                url = f"{Config.COINGECKO_URL}/simple/price"
                params = {
                    "ids": symbol,
                    "vs_currencies": "usd",
                    "include_24hr_change": "true"
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if symbol not in data:
                    return None
                
                current_price = data[symbol]['usd']
                price_change_24h = data[symbol].get('usd_24h_change', 0)
                
                result = {
                    'symbol': symbol,
                    'current_price': current_price,
                    'price_change_24h': price_change_24h,
                    'asset_type': 'cryptocurrency',
                    'currency': 'USD'  # Cryptos sempre em USD
                }
                
                # Salvar no cache
                self.db.save_price_data(symbol, result, 'cryptocurrency')
                
            else:
                # Dados históricos - usar market_chart
                url = f"{Config.COINGECKO_URL}/coins/{symbol}/market_chart"
                params = {
                    "vs_currency": "usd", 
                    "days": days,
                    "interval": "daily" if days > 1 else "hourly"
                }
                
                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                if 'prices' not in data or not data['prices']:
                    logger.warning(f"Nenhum dado de preço retornado para {symbol}")
                    return None
                
                prices = data['prices']  # [[timestamp, price], ...]
                
                # Buscar preço atual para incluir na resposta
                current_price = prices[-1][1] if prices else 0
                price_change_24h = 0
                
                # Calcular mudança de 24h se possível
                if len(prices) >= 2:
                    price_24h_ago = prices[-2][1] if len(prices) > 1 else prices[0][1]
                    price_change_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100
                
                result = {
                    'symbol': symbol,
                    'prices': prices,
                    'current_price': current_price,
                    'price_change_24h': price_change_24h,
                    'asset_type': 'cryptocurrency',
                    'currency': 'USD'  # Cryptos sempre em USD
                }
                
                logger.info(f"Dados históricos crypto obtidos: {symbol} - {len(prices)} pontos para {days} dias")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados crypto para {symbol}: {e}")
            return None
    
    def fetch_stock_data(self, symbol, days=1):
        """Busca dados de ação via yfinance"""
        try:
            # Verificar cache primeiro
            if days == 1:
                cached_data = self.db.get_cached_data(symbol)
                if cached_data:
                    return cached_data
            
            ticker = yf.Ticker(symbol)
            
            # Determinar moeda baseado no símbolo
            currency_code, currency_symbol = self._get_currency_info(symbol)
            
            if days == 1:
                # Dados atuais
                hist = ticker.history(period="5d")  # 5 dias para garantir dados suficientes
                if len(hist) < 2:
                    logger.warning(f"Dados insuficientes para {symbol}")
                    return None
                
                current_price = float(hist['Close'].iloc[-1])
                previous_price = float(hist['Close'].iloc[-2])
                price_change_24h = ((current_price - previous_price) / previous_price) * 100
                
                result = {
                    'symbol': symbol,
                    'current_price': current_price,
                    'price_change_24h': price_change_24h,
                    'asset_type': 'stock',
                    'currency': currency_code,
                }
                
                # Salvar no cache
                self.db.save_price_data(symbol, result, 'stock')
                
            else:
                # CORREÇÃO PRINCIPAL: Melhorar o período para dados históricos
                if days <= 30:
                    period = "1mo"
                elif days <= 90:
                    period = "3mo"
                elif days <= 180:
                    period = "6mo"
                elif days <= 365:
                    period = "1y"
                else:
                    period = "2y"
                
                # Usar start e end dates para maior precisão
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days + 5)  # +5 dias buffer para fins de semana
                
                hist = ticker.history(start=start_date, end=end_date, interval="1d")
                
                if hist.empty:
                    logger.warning(f"Nenhum dado histórico retornado para {symbol}")
                    return None
                
                # Limitar aos dias solicitados
                hist = hist.tail(days) if len(hist) > days else hist
                
                prices_data = []
                for date, row in hist.iterrows():
                    prices_data.append([
                        int(date.timestamp() * 1000),  # timestamp em milliseconds
                        float(row['Close'])
                    ])
                
                # Calcular preço atual e mudança de 24h
                current_price = float(hist['Close'].iloc[-1]) if not hist.empty else 0
                price_change_24h = 0
                
                if len(hist) >= 2:
                    previous_price = float(hist['Close'].iloc[-2])
                    price_change_24h = ((current_price - previous_price) / previous_price) * 100
                
                result = {
                    'symbol': symbol,
                    'prices': prices_data,
                    'current_price': current_price,
                    'price_change_24h': price_change_24h,
                    'asset_type': 'stock',
                    'currency': currency_code,
                }
                
                logger.info(f"Dados históricos stock obtidos: {symbol} - {len(prices_data)} pontos para {days} dias")
                
                # Salvar dados históricos
                historical_data = {}
                for date, row in hist.iterrows():
                    historical_data[date.strftime('%Y-%m-%d')] = {
                        'open': float(row['Open']),
                        'high': float(row['High']),
                        'low': float(row['Low']),
                        'close': float(row['Close']),
                        'volume': int(row['Volume'])
                    }
                self.db.save_historical_data(symbol, historical_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados de ação para {symbol}: {e}")
            return None
    
    def get_asset_data(self, symbol, days=1):
        """
        Retorna dados de qualquer ativo: crypto, stock ou FII.
        Protege contra tentativas de buscar cripto no yfinance.
        """
        logger.info(f"Buscando dados para {symbol} - {days} dias")
        
        asset_type = self.determine_asset_type(symbol)
        
        try:
            # 🔹 Criptomoedas
            if asset_type == 'crypto':
                data = self.fetch_crypto_data(symbol.lower(), days)
                if data:
                    logger.info(f"Dados crypto encontrados para {symbol}")
                    return data
                else:
                    logger.warning(f"Nenhum dado crypto encontrado para {symbol}")
                    return None
            
            # Preparar símbolo para yfinance
            yf_symbol = symbol.upper()
            if not yf_symbol.endswith(".SA"):
                yf_symbol += ".SA"
            
            # 🔹 FII
            if asset_type == 'fii':
                data = self.fetch_stock_data(yf_symbol, days)
                if data:
                    data["asset_type"] = "fii"
                    logger.info(f"Dados FII encontrados para {symbol}")
                    return data
                else:
                    logger.warning(f"Nenhum dado FII encontrado para {symbol}")
                    return None
            
            # 🔹 Stock
            if asset_type == 'stock':
                data = self.fetch_stock_data(yf_symbol, days)
                if data:
                    data["asset_type"] = "stock"
                    logger.info(f"Dados stock encontrados para {symbol}")
                    return data
                else:
                    logger.warning(f"Nenhum dado stock encontrado para {symbol}")
                    return None
            
            # 🔹 Fallback automático (somente se não for cripto)
            logger.warning(f"Símbolo {symbol} não categorizado, tentando fallback automático")
            # Tentativa automática só se não for cripto
            if symbol.lower() not in [c.lower() for c in Config.CRYPTO_SYMBOLS]:
                data = self.fetch_stock_data(yf_symbol, days)
                if data:
                    logger.info(f"Dados stock encontrados no fallback para {symbol}")
                    return data
            
            logger.warning(f"Nenhum dado encontrado para {symbol}")
            return None

        except Exception as e:
            logger.error(f"Erro ao buscar dados para {symbol}: {e}")
            return None


    def generate_chart(prices_data, symbol, days=7):
        """Gera gráfico de preços"""
        try:
            # Converter dados para DataFrame
            df = pd.DataFrame(prices_data, columns=['timestamp', 'price'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Criar gráfico
            plt.figure(figsize=(12, 6))
            plt.plot(df['timestamp'], df['price'], linewidth=2, color='#1f77b4')
            plt.title(f'{symbol.upper()} - Últimos {days} dias', fontsize=16, fontweight='bold')
            plt.xlabel('Data', fontsize=12)
            plt.ylabel('Preço (USD)', fontsize=12)
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Converter para base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
            
            return image_base64
            
        except Exception as e:
            logger.error(f"Erro ao gerar gráfico para {symbol}: {e}")
            return None
        
    def determine_asset_type(self, symbol: str) -> str:
        """Retorna o tipo de ativo: 'crypto', 'stock' ou 'fii'"""
        sym_upper = symbol.upper()
        sym_lower = symbol.lower()

        # Crypto
        if sym_lower in [crypto.lower() for crypto in Config.CRYPTO_SYMBOLS]:
            return 'crypto'

        # Normalizar FII
        yf_symbol = sym_upper
        if yf_symbol.endswith('11') and not yf_symbol.endswith('.SA'):
            yf_symbol += '.SA'

        # FII
        if yf_symbol in Config.FII_SYMBOLS:
            return 'fii'

        # Stock
        if yf_symbol in Config.STOCK_SYMBOLS or yf_symbol.endswith('.SA'):
            return 'stock'

        # fallback
        return 'unknown'