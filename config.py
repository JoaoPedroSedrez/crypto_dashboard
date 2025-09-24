import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

class Config:
    # MongoDB
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "crypto_dashboard")

    # Cache settings
    CACHE_EXPIRY_MINUTES = int(os.getenv("CACHE_EXPIRY_MINUTES", 10))

    # API Rate Limits
    API_RATE_LIMIT = int(os.getenv("API_RATE_LIMIT", 100))  # requests por minuto

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "crypto_dashboard.log")

    # Externa APIs
    COINGECKO_URL = "https://api.coingecko.com/api/v3"
    
    # Alpha Vantage (para ações - opcional)
    ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"

    # Supported assets - nomes corretos para APIs
    CRYPTO_SYMBOLS = [
        'bitcoin',
        'ethereum', 
        'dogecoin' 
    ]
    
    # Display names para o frontend
    CRYPTO_DISPLAY_SYMBOLS = [
        'BITCOIN',
        'ETHEREUM', 
        'DOGECOIN'
    ]
    
    STOCK_SYMBOLS = [
        'BBAS3.SA', 
        'PETR4.SA',  
        'SAPR11.SA', 
        'CMIG4.SA',  
        'VALE3.SA',  
        'ROXO34.SA'  
    ]

    FII_SYMBOLS = [
        "KNCR11.SA", "GARE11.SA", "MXRF11.SA", 
        "XPML11.SA", "VISC11.SA", "BTLG11.SA"
    ]
    
    # Mapeamento de símbolos curtos para nomes completos (cryptos)
    CRYPTO_SYMBOL_MAP = {
        'btc': 'bitcoin',
        'eth': 'ethereum',
        'doge': 'dogecoin'
    }
    
    # URLs de APIs externas
    COINGECKO_ENDPOINTS = {
        'price': f"{COINGECKO_URL}/simple/price",
        'history': f"{COINGECKO_URL}/coins/{{symbol}}/market_chart",
        'coins_list': f"{COINGECKO_URL}/coins/list"
    }
    
    # Configurações de timeout
    API_TIMEOUT = 15  # segundos
    
    # Configurações de retry
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # segundos
    
    # Configurações de desenvolvimento
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    DEVELOPMENT = os.getenv("ENVIRONMENT", "development") == "development"