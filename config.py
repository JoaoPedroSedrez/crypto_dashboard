import os
from dotenv import load_dotenv

#Carregar variáveis de ambiente do arquivo .env
load_dotenv()

class Config():
    # MongoDB
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "crypto_dashboard")

    # Cache settings
    CACHE_EXPIRY_MINUTES = 10

    # API Rate Limits
    API_RATE_LIMIT = 100 # requests por minuto

    # Logging
    LOG_LEVEL = "INFO"
    LOG_FILE = "crypto_dashboard.log"

    # Externa APIs
    COINGECKO_URL = "https://api.coingecko.com/api/v3"

    # Supported assets
    CRYPTO_SYMBOLS = ['bitcoin', 'ethereum']
    STOCK_SYMBOLS = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA', 'AMZN', 'META', 'NFLX', 'AMD']