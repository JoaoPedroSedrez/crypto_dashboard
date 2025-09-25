# utils/db.py
import logging
from pymongo import MongoClient
from datetime import datetime, timedelta
from config import Config

# Configurar logging
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.client = MongoClient(Config.MONGODB_URL)
        self.db = self.client[Config.DATABASE_NAME]
        self.prices_collection = self.db.prices
        self.cache_collection = self.db.cache
        self.wallet_transactions = self.db.wallet_transactions

    def update_holding(self, symbol: str, holding_doc: dict):
        """Atualiza ou cria o holding de um ativo"""
        self.db.wallet_holdings.update_one(
            {"symbol": symbol.lower()},
            {"$set": holding_doc},
            upsert=True  # Cria se não existir
        )

    def save_price_data(self, symbol, data, asset_type):
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
                self.db.prices.replace_one(
                    {"symbol": symbol, "date": date},
                    document,
                    upsert=True
                )
            logger.info(f"Dados históricos salvos para {symbol}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar histórico para {symbol}: {e}")
            return False
    
    def delete_holding(self, symbol: str):
        """
        Deleta um holding do banco de dados pelo símbolo.
        Retorna True se algum documento foi deletado, False caso contrário.
        """
        try:
            result = self.db.wallet_holdings.delete_one({"symbol": symbol.lower()})
            if result.deleted_count > 0:
                logger.info(f"Holding {symbol} deletado com sucesso.")
                return True
            else:
                logger.warning(f"Holding {symbol} não encontrado.")
                return False
        except Exception as e:
            logger.error(f"Erro ao deletar holding {symbol}: {e}")
            return False
