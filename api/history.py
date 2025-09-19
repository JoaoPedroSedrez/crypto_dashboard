from fastapi import APIRouter, HTTPException, Query
from utils.helpers import DataFetcher, logger
import time

router = APIRouter()
data_fetcher = DataFetcher()

@router.get("/price")
async def get_current_price(
    symbol: str = Query(..., description="Símbolo do ativo (ex: BTC, AAPL)")
):
    """
    Retorna o preço atual e variação de 24h de um ativo
    
    Args:
        symbol: Símbolo da criptomoeda ou ação
    
    Returns:
        JSON com preço atual, variação 24h e tipo de ativo
    """
    start_time = time.time()
    
    try:
        logger.info(f"Buscando preço para: {symbol}")
        
        # Buscar dados do ativo
        asset_data = data_fetcher.get_asset_data(symbol, days=1)
        
        if not asset_data:
            raise HTTPException(
                status_code=404, 
                detail=f"Ativo '{symbol}' não encontrado ou indisponível"
            )
        
        # Calcular tempo de resposta
        response_time = round((time.time() - start_time) * 1000, 2)
        
        # Formatar resposta
        response = {
            "symbol": asset_data['symbol'],
            "asset_type": asset_data['asset_type'],
            "current_price": round(asset_data['current_price'], 2),
            "price_change_24h": round(asset_data['price_change_24h'], 2),
            "currency": "USD",
            "response_time_ms": response_time,
            "cached": True if response_time < 100 else False  # Estimativa de cache
        }
        
        logger.info(f"Preço obtido para {symbol}: ${asset_data['current_price']}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar preço para {symbol}: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Erro interno do servidor"
        )

@router.get("/price/multiple")
async def get_multiple_prices(
    symbols: str = Query(..., description="Símbolos separados por vírgula (ex: BTC,ETH,AAPL)")
):
    """
    Retorna preços de múltiplos ativos
    
    Args:
        symbols: Lista de símbolos separados por vírgula
    
    Returns:
        JSON com preços de todos os ativos solicitados
    """
    try:
        symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
        
        if len(symbol_list) > 10:
            raise HTTPException(
                status_code=400,
                detail="Máximo de 10 símbolos por requisição"
            )
        
        results = []
        errors = []
        
        for symbol in symbol_list:
            try:
                asset_data = data_fetcher.get_asset_data(symbol, days=1)
                if asset_data:
                    results.append({
                        "symbol": asset_data['symbol'],
                        "asset_type": asset_data['asset_type'],
                        "current_price": round(asset_data['current_price'], 2),
                        "price_change_24h": round(asset_data['price_change_24h'], 2)
                    })
                else:
                    errors.append(f"Ativo '{symbol}' não encontrado")
            except Exception as e:
                errors.append(f"Erro ao buscar '{symbol}': {str(e)}")
        
        response = {
            "results": results,
            "total_requested": len(symbol_list),
            "total_found": len(results),
            "errors": errors if errors else None
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar múltiplos preços: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno do servidor"
        )