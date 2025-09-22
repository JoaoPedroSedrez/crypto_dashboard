from fastapi import APIRouter, HTTPException, Query
from utils.helpers import DataFetcher, logger
import time
import statistics
from typing import List, Dict, Any

router = APIRouter()
data_fetcher = DataFetcher()

@router.get("/history")
async def get_price_history(
    symbol: str = Query(..., description="Símbolo do ativo (ex: BTC, AAPL)"),
    days: int = Query(7, ge=1, le=365, description="Número de dias de histórico")
):
    """
    Retorna histórico de preços de um ativo
    
    Args:
        symbol: Símbolo da criptomoeda ou ação
        days: Número de dias de histórico
    
    Returns:
        JSON com histórico de preços e estatísticas
    """
    start_time = time.time()
    
    try:
        logger.info(f"Buscando histórico para: {symbol} ({days} dias)")
        
        # Buscar dados do ativo
        asset_data = data_fetcher.get_asset_data(symbol, days=days)
        
        if not asset_data:
            raise HTTPException(
                status_code=404, 
                detail=f"Ativo '{symbol}' não encontrado ou indisponível"
            )
        
        if 'prices' not in asset_data or not asset_data['prices']:
            raise HTTPException(
                status_code=404,
                detail=f"Dados históricos não disponíveis para '{symbol}'"
            )
        
        # Processar dados históricos
        prices_data = asset_data['prices']
        price_values = [price[1] for price in prices_data]  # Extrair apenas os preços
        
        # Calcular estatísticas
        if len(price_values) > 0:
            min_price = min(price_values)
            max_price = max(price_values)
            avg_price = sum(price_values) / len(price_values)
            
            # Calcular volatilidade (desvio padrão)
            if len(price_values) > 1:
                volatility = statistics.stdev(price_values)
                volatility_percent = (volatility / avg_price) * 100
            else:
                volatility = 0
                volatility_percent = 0
            
            # Calcular variação total do período
            first_price = price_values[0]
            last_price = price_values[-1]
            total_change_percent = ((last_price - first_price) / first_price) * 100
            
            stats = {
                "min_price": round(min_price, 2),
                "max_price": round(max_price, 2),
                "avg_price": round(avg_price, 2),
                "volatility": round(volatility_percent, 2),
                "total_change_percent": round(total_change_percent, 2)
            }
        else:
            stats = {
                "min_price": 0,
                "max_price": 0,
                "avg_price": 0,
                "volatility": 0,
                "total_change_percent": 0
            }
        
        # Calcular tempo de resposta
        response_time = round((time.time() - start_time) * 1000, 2)
        
        # Formatar dados de preços para o frontend
        formatted_prices = []
        for timestamp, price in prices_data:
            formatted_prices.append({
                "timestamp": timestamp,
                "price": round(price, 2)
            })
        
        # Formatar resposta
        response = {
            "symbol": asset_data['symbol'],
            "asset_type": asset_data['asset_type'],
            "period_days": days,
            "data_points": len(formatted_prices),
            "prices": formatted_prices,
            "statistics": stats,
            "current_price": round(asset_data.get('current_price', last_price), 2),
            "price_change_24h": round(asset_data.get('price_change_24h', 0), 2),
            "response_time_ms": response_time
        }
        
        logger.info(f"Histórico obtido para {symbol}: {len(formatted_prices)} pontos")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar histórico para {symbol}: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Erro interno do servidor"
        )

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

@router.get("/summary")
async def get_market_summary(
    symbols: str = Query(
        "bitcoin,ethereum,cardano,solana,dogecoin,AAPL,GOOGL,MSFT,TSLA,NVDA", 
        description="Símbolos separados por vírgula para resumo do mercado"
    )
):
    """
    Retorna resumo do mercado com múltiplos ativos
    
    Args:
        symbols: Lista de símbolos separados por vírgula
    
    Returns:
        JSON com resumo de mercado
    """
    try:
        logger.info("Gerando resumo do mercado")
        
        symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
        
        if len(symbol_list) > 20:
            raise HTTPException(
                status_code=400,
                detail="Máximo de 20 símbolos para resumo do mercado"
            )
        
        assets_data = []
        total_market_cap = 0
        
        for symbol in symbol_list:
            try:
                # Buscar dados do ativo com histórico de 7 dias para estatísticas
                asset_data = data_fetcher.get_asset_data(symbol, days=7)
                
                if asset_data and 'prices' in asset_data and asset_data['prices']:
                    price_values = [price[1] for price in asset_data['prices']]
                    
                    # Calcular estatísticas básicas
                    min_price = min(price_values) if price_values else 0
                    max_price = max(price_values) if price_values else 0
                    current_price = asset_data.get('current_price', price_values[-1] if price_values else 0)
                    change_percent = asset_data.get('price_change_24h', 0)
                    
                    # Determinar performance emoji
                    if change_percent > 5:
                        performance = "🚀"
                    elif change_percent > 0:
                        performance = "📈"
                    elif change_percent < -5:
                        performance = "📉"
                    else:
                        performance = "➡️"
                    
                    assets_data.append({
                        "symbol": asset_data['symbol'],
                        "asset_type": asset_data['asset_type'],
                        "current_price": round(current_price, 2),
                        "change_percent": round(change_percent, 2),
                        "min_price": round(min_price, 2),
                        "max_price": round(max_price, 2),
                        "performance": performance
                    })
                    
                    # Simular market cap (apenas para demonstration)
                    if asset_data['asset_type'] == 'cryptocurrency':
                        total_market_cap += current_price * 1000000  # Simulação
                
            except Exception as e:
                logger.warning(f"Erro ao buscar dados para {symbol} no resumo: {e}")
                continue
        
        # Calcular estatísticas gerais do mercado
        if assets_data:
            total_assets = len(assets_data)
            positive_change = len([a for a in assets_data if a['change_percent'] > 0])
            negative_change = len([a for a in assets_data if a['change_percent'] < 0])
            
            # Tendência geral do mercado
            avg_change = sum([a['change_percent'] for a in assets_data]) / total_assets
            if avg_change > 2:
                market_sentiment = "Bullish 🐂"
            elif avg_change < -2:
                market_sentiment = "Bearish 🐻"
            else:
                market_sentiment = "Neutral ⚖️"
        else:
            total_assets = 0
            positive_change = 0
            negative_change = 0
            market_sentiment = "Unknown"
            avg_change = 0
        
        response = {
            "market_summary": {
                "total_assets": total_assets,
                "positive_assets": positive_change,
                "negative_assets": negative_change,
                "neutral_assets": total_assets - positive_change - negative_change,
                "average_change": round(avg_change, 2),
                "market_sentiment": market_sentiment,
                "last_updated": int(time.time() * 1000)
            },
            "assets": assets_data[:15],  # Limitar a 15 ativos na resposta
            "total_requested": len(symbol_list),
            "total_found": len(assets_data)
        }
        
        logger.info(f"Resumo do mercado gerado com {len(assets_data)} ativos")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar resumo do mercado: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno do servidor"
        )