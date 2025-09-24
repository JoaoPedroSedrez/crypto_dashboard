from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import time
from contextlib import asynccontextmanager

# Importar routers
from api.price import router as price_router
from api.history import router as history_router
from api.prediction import router as prediction_router
from api.wallet import router as wallet_router

# Importar configurações
from config import Config
from utils.helpers import logger

# Context manager para startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Iniciando Crypto Dashboard API...")
    logger.info(f"MongoDB URL: {Config.MONGODB_URL}")
    logger.info(f"Database: {Config.DATABASE_NAME}")
    
    # Verificar conexão com MongoDB
    try:
        from utils.helpers import DatabaseManager
        db_manager = DatabaseManager()
        # Teste simples de conexão
        db_manager.client.admin.command('ping')
        logger.info("✅ Conexão com MongoDB estabelecida")
    except Exception as e:
        logger.error(f"❌ Erro na conexão com MongoDB: {e}")
        logger.warning("Continuando sem cache de banco de dados...")
    
    yield
    
    # Shutdown
    logger.info("🔄 Encerrando Crypto Dashboard API...")

# Criar aplicação FastAPI
app = FastAPI(
    title="Crypto Dashboard API",
    description="API para consulta de preços, histórico e previsões de criptomoedas e ações",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique os domínios permitidos
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Middleware para logging de requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log da requisição
    logger.info(f"📥 {request.method} {request.url.path} - Client: {request.client.host}")
    
    response = await call_next(request)
    
    # Log da resposta
    process_time = time.time() - start_time
    logger.info(f"📤 {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")
    
    return response

# Configurar templates e arquivos estáticos
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Incluir routers da API
app.include_router(price_router, prefix="/api/v1", tags=["Preços"])
app.include_router(history_router, prefix="/api/v1", tags=["Histórico"])
app.include_router(prediction_router, prefix="/api/v1", tags=["Previsões"])
app.include_router(wallet_router, prefix="/api/v1/wallet", tags=["Carteira"])  

# Rotas principais
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Página inicial do dashboard"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Crypto Dashboard",
        "crypto_symbols": Config.CRYPTO_SYMBOLS,
        "stock_symbols": Config.STOCK_SYMBOLS
    })

@app.get("/health")
async def health_check():
    """Endpoint de saúde da API"""
    try:
        from utils.helpers import DatabaseManager
        db_manager = DatabaseManager()
        db_manager.client.admin.command('ping')
        db_status = "healthy"
    except:
        db_status = "unhealthy"
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "database": db_status,
        "version": "1.0.0"
    }

@app.get("/api/v1/assets")
async def get_supported_assets():
    """Retorna lista de ativos suportados"""
    return {
        "cryptocurrencies": [crypto.lower() for crypto in Config.CRYPTO_SYMBOLS],  # API espera lowercase
        "stocks": Config.STOCK_SYMBOLS,
        "total_supported": len(Config.CRYPTO_SYMBOLS) + len(Config.STOCK_SYMBOLS),
        "crypto_display": Config.CRYPTO_SYMBOLS,  # Para exibição
        "stock_display": Config.STOCK_SYMBOLS
    }

@app.get("/api/v1/status")
async def get_api_status():
    """Retorna status detalhado da API"""
    try:
        from utils.helpers import DatabaseManager
        db_manager = DatabaseManager()
        
        # Testar MongoDB
        db_manager.client.admin.command('ping')
        
        # Contar documentos em cache
        cache_count = db_manager.cache_collection.count_documents({})
        historical_count = db_manager.prices_collection.count_documents({})
        
        db_info = {
            "status": "connected",
            "cached_assets": cache_count,
            "historical_records": historical_count
        }
    except Exception as e:
        db_info = {
            "status": "disconnected",
            "error": str(e)
        }
    
    return {
        "api_version": "1.0.0",
        "status": "operational",
        "database": db_info,
        "supported_assets": {
            "cryptocurrencies": len(Config.CRYPTO_SYMBOLS),
            "stocks": len(Config.STOCK_SYMBOLS)
        },
        "features": [
            "Current Prices",
            "Historical Data",
            "Price Predictions",
            "Technical Analysis",
            "Market Summary"
        ]
    }

@app.get("/wallet", response_class=HTMLResponse)
async def wallet(request: Request):
    """Página da carteira (myWallet)"""
    return templates.TemplateResponse("wallet.html", {
        "request": request,
        "title": "myWallet"
    })

# Handlers de erro globais
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse("404.html", {
        "request": request,
        "title": "Página não encontrada"
    }, status_code=404)

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"Erro interno: {exc}")
    return {
        "error": "Erro interno do servidor",
        "message": "Tente novamente mais tarde",
        "status_code": 500
    }

# Função para executar a aplicação
def run_server():
    """Executa o servidor de desenvolvimento"""
    logger.info("🎯 Iniciando servidor de desenvolvimento...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    run_server()