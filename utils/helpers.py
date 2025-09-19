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

class DatabaseManager:
    def __init__(self):
        self.client = MongoClient(Config.MONGODB_URL)
        self.db = self.client[Config.DATABASE_NAME]
        self.prices_collection = self.db.prices
        self.cache_collection = self.db.cache
    
    def save_price_data(self, symbol, data, asset_type):
        """Salva dados de preço no MongoDB"""
        try:
            document = {
                "symbol": symbol,
                "asset_type": asset_type,
                "data": data,
                "timestamp": datetime.now(),
                "expires_at": datetime.now() + timedelta(minutes=Config.CACHE_EXPIRY_MINUTES)
            }
            self.cache_collection.replace_one(
                {"symbol": symbol}, 
                document, 
                upsert=True
            )
            logger.info(f"Dados salvos para {symbol}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar dados para {symbol}: {e}")
            return False
    
    def get_cached_data(self, symbol):
        """Busca dados em cache"""
        try:
            cached = self.cache_collection.find_one({
                "symbol": symbol,
                "expires_at": {"$gt": datetime.now()}
            })
            return cached['data'] if cached else None
        except Exception as e:
            logger.error(f"Erro ao buscar cache para {symbol}: {e}")
            return None
    
    def save_historical_data(self, symbol, historical_data):
        """Salva dados históricos"""
        try:
            for date, data in historical_data.items():
                document = {
                    "symbol": symbol,
                    "date": date,
                    "open": data.get('open'),
                    "high": data.get('high'), 
                    "low": data.get('low'),
                    "close": data.get('close'),
                    "volume": data.get('volume'),
                    "timestamp": datetime.now()
                }
                self.prices_collection.replace_one(
                    {"symbol": symbol, "date": date},
                    document,
                    upsert=True
                )
            logger.info(f"Dados históricos salvos para {symbol}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar histórico para {symbol}: {e}")
            return False

class DataFetcher:
    def __init__(self):
        self.db = DatabaseManager()
    
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
                
                response = requests.get(url, params=params)
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
                    'asset_type': 'crypto'
                }
                
                # Salvar no cache
                self.db.save_price_data(symbol, result, 'crypto')
                
            else:
                # Dados históricos - usar market_chart
                url = f"{Config.COINGECKO_URL}/coins/{symbol}/market_chart"
                params = {
                    "vs_currency": "usd", 
                    "days": days,
                    "interval": "daily" if days > 1 else "hourly"
                }
                
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if 'prices' not in data:
                    return None
                
                prices = data['prices']  # [[timestamp, price], ...]
                result = {
                    'symbol': symbol,
                    'prices': prices,
                    'asset_type': 'crypto'
                }
            
            logger.info(f"Dados de crypto obtidos para {symbol} ({days} dias)")
            return result
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados crypto para {symbol}: {e}")
            return None
    
    def fetch_stock_data(self, symbol, days=1):
        """Busca dados de ação via yfinance"""
        try:
            # Verificar cache primeiro
            cached_data = self.db.get_cached_data(symbol)
            if cached_data and days == 1:
                return cached_data
            
            ticker = yf.Ticker(symbol)
            
            if days == 1:
                # Dados atuais
                hist = ticker.history(period="2d")  # 2 dias para calcular variação
                if len(hist) < 2:
                    return None
                
                current_price = float(hist['Close'].iloc[-1])
                previous_price = float(hist['Close'].iloc[-2])
                price_change_24h = ((current_price - previous_price) / previous_price) * 100
                
                result = {
                    'symbol': symbol,
                    'current_price': current_price,
                    'price_change_24h': price_change_24h,
                    'asset_type': 'stock'
                }
                
                # Salvar no cache
                self.db.save_price_data(symbol, result, 'stock')
                
            else:
                # Dados históricos
                period = f"{days}d" if days <= 60 else "3mo"
                hist = ticker.history(period=period)
                
                prices_data = []
                for date, row in hist.iterrows():
                    prices_data.append([
                        int(date.timestamp() * 1000),  # timestamp em milliseconds
                        float(row['Close'])
                    ])
                
                result = {
                    'symbol': symbol,
                    'prices': prices_data,
                    'asset_type': 'stock'
                }
                
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
            
            logger.info(f"Dados de ação obtidos para {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados de ação para {symbol}: {e}")
            return None
    
    def get_asset_data(self, symbol, days=1):
        """Identifica se é crypto ou stock e busca dados apropriados"""
        # Primeiro tenta como crypto
        if symbol.lower() in [crypto.lower() for crypto in Config.CRYPTO_SYMBOLS]:
            return self.fetch_crypto_data(symbol.lower(), days)
        
        # Depois tenta como stock
        if symbol.upper() in Config.STOCK_SYMBOLS:
            return self.fetch_stock_data(symbol.upper(), days)
        
        # Tenta ambos se não estiver na lista conhecida
        crypto_data = self.fetch_crypto_data(symbol.lower(), days)
        if crypto_data:
            return crypto_data
        
        stock_data = self.fetch_stock_data(symbol.upper(), days)
        if stock_data:
            return stock_data
        
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