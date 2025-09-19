from fastapi import APIRouter, HTTPException, Query
from utils.helpers import DataFetcher, logger
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import joblib
import os

router = APIRouter()
data_fetcher = DataFetcher()

class PricePredictionModel:
    def __init__(self):
        self.model = LinearRegression()
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def prepare_features(self, prices_data):
        """Prepara features para o modelo de ML"""
        try:
            # Converter para DataFrame
            df = pd.DataFrame(prices_data, columns=['timestamp', 'price'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.sort_values('timestamp')
            
            # Criar features técnicas
            df['price_ma_3'] = df['price'].rolling(window=3).mean()  # Média móvel 3 dias
            df['price_ma_7'] = df['price'].rolling(window=7).mean()  # Média móvel 7 dias
            df['price_change'] = df['price'].pct_change()  # Variação percentual
            df['volatility'] = df['price'].rolling(window=5).std()  # Volatilidade
            
            # Features baseadas em tempo
            df['day_of_week'] = df['timestamp'].dt.dayofweek
            df['hour'] = df['timestamp'].dt.hour
            
            # Features de lag (preços anteriores)
            for i in range(1, 4):  # 3 dias anteriores
                df[f'price_lag_{i}'] = df['price'].shift(i)
            
            # Remover NaN
            df = df.dropna()
            
            if len(df) < 10:  # Mínimo de dados necessários
                return None, None
            
            # Preparar X (features) e y (target)
            feature_columns = [
                'price_ma_3', 'price_ma_7', 'price_change', 'volatility',
                'day_of_week', 'hour', 'price_lag_1', 'price_lag_2', 'price_lag_3'
            ]
            
            X = df[feature_columns].values
            y = df['price'].values
            
            return X, y
            
        except Exception as e:
            logger.error(f"Erro ao preparar features: {e}")
            return None, None
    
    def train_model(self, X, y):
        """Treina o modelo de previsão"""
        try:
            # Normalizar features
            X_scaled = self.scaler.fit_transform(X)
            
            # Treinar modelo
            self.model.fit(X_scaled, y)
            self.is_trained = True
            
            # Calcular métricas de avaliação
            predictions = self.model.predict(X_scaled)
            mse = np.mean((predictions - y) ** 2)
            rmse = np.sqrt(mse)
            mae = np.mean(np.abs(predictions - y))
            
            return {
                'rmse': rmse,
                'mae': mae,
                'r2_score': self.model.score(X_scaled, y)
            }
            
        except Exception as e:
            logger.error(f"Erro ao treinar modelo: {e}")
            return None
    
    def predict_next_prices(self, X_last, days=3):
        """Prevê preços futuros"""
        try:
            if not self.is_trained:
                return None
            
            predictions = []
            current_features = X_last.copy()
            
            for _ in range(days):
                # Normalizar features
                features_scaled = self.scaler.transform([current_features])
                
                # Fazer previsão
                predicted_price = self.model.predict(features_scaled)[0]
                predictions.append(predicted_price)
                
                # Atualizar features para próxima previsão (simulação simples)
                # Em uma implementação mais sofisticada, atualizaríamos todas as features
                current_features[-3:] = [current_features[-2], current_features[-1], predicted_price]
            
            return predictions
            
        except Exception as e:
            logger.error(f"Erro ao fazer previsão: {e}")
            return None

@router.get("/prediction")
async def get_price_prediction(
    symbol: str = Query(..., description="Símbolo do ativo"),
    days: int = Query(3, ge=1, le=7, description="Dias para prever (1-7)")
):
    """
    Retorna previsão de preços usando regressão linear
    
    Args:
        symbol: Símbolo da criptomoeda ou ação
        days: Número de dias para prever
    
    Returns:
        JSON com previsões e métricas do modelo
    """
    try:
        logger.info(f"Gerando previsão para: {symbol} ({days} dias)")
        
        # Buscar dados históricos (30 dias para treinar o modelo)
        asset_data = data_fetcher.get_asset_data(symbol, days=30)
        
        if not asset_data or 'prices' not in asset_data:
            raise HTTPException(
                status_code=404,
                detail=f"Dados históricos insuficientes para '{symbol}'"
            )
        
        # Preparar modelo
        prediction_model = PricePredictionModel()
        
        # Preparar dados
        X, y = prediction_model.prepare_features(asset_data['prices'])
        
        if X is None or len(X) < 10:
            raise HTTPException(
                status_code=400,
                detail="Dados insuficientes para gerar previsão confiável"
            )
        
        # Treinar modelo
        metrics = prediction_model.train_model(X, y)
        
        if not metrics:
            raise HTTPException(
                status_code=500,
                detail="Erro ao treinar modelo de previsão"
            )
        
        # Fazer previsões
        last_features = X[-1]  # Últimas features disponíveis
        predictions = prediction_model.predict_next_prices(last_features, days)
        
        if not predictions:
            raise HTTPException(
                status_code=500,
                detail="Erro ao gerar previsões"
            )
        
        # Preparar resposta
        current_price = asset_data['prices'][-1][1]  # Último preço conhecido
        
        predicted_data = []
        for i, pred_price in enumerate(predictions):
            future_date = datetime.now() + timedelta(days=i+1)
            predicted_data.append({
                "day": i + 1,
                "date": future_date.strftime('%Y-%m-%d'),
                "predicted_price": round(pred_price, 2),
                "change_from_current": round(((pred_price - current_price) / current_price) * 100, 2)
            })
        
        # Calcular tendência geral
        total_change = ((predictions[-1] - current_price) / current_price) * 100
        trend = "Alta" if total_change > 2 else "Baixa" if total_change < -2 else "Estável"
        trend_emoji = "📈" if total_change > 2 else "📉" if total_change < -2 else "➡️"
        
        response = {
            "symbol": asset_data['symbol'],
            "asset_type": asset_data['asset_type'],
            "current_price": round(current_price, 2),
            "prediction_days": days,
            "predictions": predicted_data,
            "summary": {
                "trend": trend,
                "trend_emoji": trend_emoji,
                "total_change_percent": round(total_change, 2),
                "confidence_level": min(max(metrics['r2_score'] * 100, 0), 100)  # R² como confiança
            },
            "model_metrics": {
                "rmse": round(metrics['rmse'], 2),
                "mae": round(metrics['mae'], 2),
                "r2_score": round(metrics['r2_score'], 3)
            },
            "disclaimer": "Previsões são baseadas em dados históricos e não garantem resultados futuros. Apenas para fins educacionais."
        }
        
        logger.info(f"Previsão gerada para {symbol}: tendência {trend}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro inesperado na previsão para {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno do servidor"
        )

@router.get("/prediction/analysis")
async def get_technical_analysis(
    symbol: str = Query(..., description="Símbolo do ativo"),
    days: int = Query(14, ge=7, le=60, description="Período para análise técnica")
):
    """
    Retorna análise técnica detalhada do ativo
    
    Args:
        symbol: Símbolo do ativo
        days: Período para análise
    
    Returns:
        JSON com indicadores técnicos
    """
    try:
        logger.info(f"Gerando análise técnica para: {symbol}")
        
        # Buscar dados históricos
        asset_data = data_fetcher.get_asset_data(symbol, days=days)
        
        if not asset_data or 'prices' not in asset_data:
            raise HTTPException(
                status_code=404,
                detail=f"Dados insuficientes para análise de '{symbol}'"
            )
        
        # Converter para DataFrame
        df = pd.DataFrame(asset_data['prices'], columns=['timestamp', 'price'])
        df = df.sort_values('timestamp')
        
        # Calcular indicadores técnicos
        df['sma_7'] = df['price'].rolling(window=7).mean()  # Média móvel simples 7 dias
        df['sma_14'] = df['price'].rolling(window=14).mean()  # Média móvel simples 14 dias
        df['volatility'] = df['price'].rolling(window=7).std()  # Volatilidade
        df['price_change'] = df['price'].pct_change()
        
        # RSI simplificado (Relative Strength Index)
        def calculate_rsi(prices, window=14):
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        
        df['rsi'] = calculate_rsi(df['price'])
        
        # Valores atuais
        current_price = df['price'].iloc[-1]
        current_sma_7 = df['sma_7'].iloc[-1]
        current_sma_14 = df['sma_14'].iloc[-1]
        current_rsi = df['rsi'].iloc[-1]
        current_volatility = df['volatility'].iloc[-1]
        
        # Sinais de trading
        signals = []
        
        if current_price > current_sma_7:
            signals.append("🟢 Preço acima da média móvel de 7 dias")
        else:
            signals.append("🔴 Preço abaixo da média móvel de 7 dias")
        
        if current_sma_7 > current_sma_14:
            signals.append("🟢 Tendência de curto prazo positiva")
        else:
            signals.append("🔴 Tendência de curto prazo negativa")
        
        if current_rsi > 70:
            signals.append("⚠️ RSI indica possível sobrecompra")
        elif current_rsi < 30:
            signals.append("⚠️ RSI indica possível sobrevenda")
        else:
            signals.append("🟡 RSI em zona neutra")
        
        # Níveis de suporte e resistência (simplificado)
        recent_prices = df['price'].tail(14)
        support_level = recent_prices.min()
        resistance_level = recent_prices.max()
        
        response = {
            "symbol": asset_data['symbol'],
            "asset_type": asset_data['asset_type'],
            "analysis_period": days,
            "current_price": round(current_price, 2),
            "technical_indicators": {
                "sma_7": round(current_sma_7, 2),
                "sma_14": round(current_sma_14, 2),
                "rsi": round(current_rsi, 2),
                "volatility": round(current_volatility, 2),
                "support_level": round(support_level, 2),
                "resistance_level": round(resistance_level, 2)
            },
            "signals": signals,
            "recommendation": {
                "overall": "Neutro",  # Você pode criar lógica mais complexa aqui
                "confidence": 60,
                "reasoning": "Baseado em indicadores técnicos básicos"
            },
            "risk_assessment": {
                "volatility_level": "Alta" if current_volatility > df['volatility'].mean() * 1.5 else "Média" if current_volatility > df['volatility'].mean() else "Baixa",
                "trend_strength": "Forte" if abs(current_price - current_sma_14) / current_sma_14 > 0.05 else "Fraca"
            }
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na análise técnica para {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno do servidor"
        )