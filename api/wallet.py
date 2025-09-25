from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, validator
from typing import List, Optional
from datetime import datetime, timezone
from utils.helpers import DataFetcher, logger
from utils.db import DatabaseManager

router = APIRouter()
data_fetcher = DataFetcher()

# Modelos Pydantic
class WalletTransaction(BaseModel):
    symbol: str
    asset_type: str  # 'crypto' ou 'stock' 
    transaction_type: str  # 'buy' ou 'sell'
    quantity: float
    price_per_unit: float
    total_value: float
    date: datetime
    notes: Optional[str] = None
    
    @validator('transaction_type')
    def validate_transaction_type(cls, v):
        if v not in ['buy', 'sell']:
            raise ValueError('transaction_type deve ser "buy" ou "sell"')
        return v
    
    @validator('quantity', 'price_per_unit', 'total_value')
    def validate_positive_numbers(cls, v):
        if v <= 0:
            raise ValueError('Valores devem ser positivos')
        return v

class WalletAsset(BaseModel):
    symbol: str
    asset_type: str
    total_quantity: float
    average_buy_price: float
    total_invested: float
    current_value: float
    profit_loss: float
    profit_loss_percent: float
    first_purchase_date: datetime
    last_update: datetime

class WalletSummary(BaseModel):
    total_value: float
    total_invested: float
    total_profit_loss: float
    total_profit_loss_percent: float
    assets_count: int
    transactions_count: int
    best_performer: Optional[dict] = None
    worst_performer: Optional[dict] = None

# Endpoints do CRUD
@router.post("/transactions")
async def add_transaction(transaction: WalletTransaction):
    """
    Adiciona uma nova transação ao wallet
    """
    try:
        logger.info(f"Adicionando transação: {transaction.symbol} - {transaction.transaction_type}")
        
        # Verificar se o ativo existe
        asset_data = data_fetcher.get_asset_data(transaction.symbol, days=1)
        if not asset_data:
            raise HTTPException(
                status_code=404,
                detail=f"Ativo '{transaction.symbol}' não encontrado"
            )
        
        # Salvar transação no banco
        from utils.helpers import DatabaseManager
        db = DatabaseManager()
        
        transaction_doc = {
            "symbol": transaction.symbol.lower(),
            "asset_type": transaction.asset_type,
            "transaction_type": transaction.transaction_type,
            "quantity": transaction.quantity,
            "price_per_unit": transaction.price_per_unit,
            "total_value": transaction.total_value,
            "date": transaction.date,
            "notes": transaction.notes,
            "created_at": datetime.now(timezone.utc)
        }
        
        result = db.db.wallet_transactions.insert_one(transaction_doc)
        
        # Atualizar holdings após adicionar transação
        await update_wallet_holdings(transaction.symbol)
        
        return {
            "success": True,
            "transaction_id": str(result.inserted_id),
            "message": f"Transação de {transaction.transaction_type} adicionada com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao adicionar transação: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno do servidor"
        )

@router.get("/transactions")
async def get_transactions(
    symbol: Optional[str] = Query(None, description="Filtrar por símbolo"),
    transaction_type: Optional[str] = Query(None, description="Filtrar por tipo (buy/sell)"),
    limit: int = Query(50, description="Limite de resultados")
):
    """
    Lista transações do wallet com filtros opcionais
    """
    try:
        from utils.helpers import DatabaseManager
        db = DatabaseManager()
        
        # Construir filtros
        filters = {}
        if symbol:
            filters["symbol"] = symbol.lower()
        if transaction_type:
            filters["transaction_type"] = transaction_type
        
        # Buscar transações
        transactions = list(
            db.db.wallet_transactions
            .find(filters)
            .sort("date", -1)
            .limit(limit)
        )
        
        # Formatar resposta
        formatted_transactions = []
        for tx in transactions:
            formatted_transactions.append({
                "id": str(tx["_id"]),
                "symbol": tx["symbol"].upper(),
                "asset_type": tx["asset_type"],
                "transaction_type": tx["transaction_type"],
                "quantity": tx["quantity"],
                "price_per_unit": tx["price_per_unit"],
                "total_value": tx["total_value"],
                "date": tx["date"].isoformat(),
                "notes": tx.get("notes"),
                "created_at": tx["created_at"].isoformat()
            })
        
        return {
            "transactions": formatted_transactions,
            "total": len(formatted_transactions),
            "filters_applied": filters
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar transações: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno do servidor"
        )

@router.delete("/transactions/{transaction_id}")
async def delete_transaction(transaction_id: str):
    """
    Remove uma transação do wallet
    """
    try:
        from utils.helpers import DatabaseManager
        from bson import ObjectId
        
        db = DatabaseManager()
        
        # Buscar transação antes de deletar para update dos holdings
        transaction = db.db.wallet_transactions.find_one({"_id": ObjectId(transaction_id)})
        if not transaction:
            raise HTTPException(
                status_code=404,
                detail="Transação não encontrada"
            )
        
        # Deletar transação
        result = db.db.wallet_transactions.delete_one({"_id": ObjectId(transaction_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail="Transação não encontrada"
            )
        
        # Atualizar holdings após deletar transação
        await update_wallet_holdings(transaction["symbol"])
        
        return {
            "success": True,
            "message": "Transação removida com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao deletar transação: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno do servidor"
        )

@router.get("/holdings")
async def get_wallet_holdings():
    """
    Retorna todos os ativos no wallet com valores atualizados
    """
    try:
        from utils.helpers import DatabaseManager
        db = DatabaseManager()
        
        # Buscar holdings atuais
        holdings = list(db.db.wallet_holdings.find({}))
        
        assets = []
        total_value = 0
        total_invested = 0
        
        for holding in holdings:
            if holding["total_quantity"] <= 0:
                continue  # Pular ativos zerados
            
            # Buscar preço atual
            current_data = data_fetcher.get_asset_data(holding["symbol"], days=1)
            if current_data:
                current_price = current_data["current_price"]
                current_value = holding["total_quantity"] * current_price
                profit_loss = current_value - holding["total_invested"]
                profit_loss_percent = (profit_loss / holding["total_invested"]) * 100 if holding["total_invested"] > 0 else 0
                
                # Atualizar valores no banco
                db.db.wallet_holdings.update_one(
                    {"_id": holding["_id"]},
                    {
                        "$set": {
                            "current_price": current_price,
                            "current_value": current_value,
                            "profit_loss": profit_loss,
                            "profit_loss_percent": profit_loss_percent,
                            "last_update": datetime.now(timezone.utc)
                        }
                    }
                )
                
                total_value += current_value
                total_invested += holding["total_invested"]
                
                assets.append({
                    "symbol": holding["symbol"].upper(),
                    "asset_type": holding["asset_type"],
                    "total_quantity": holding["total_quantity"],
                    "average_buy_price": holding["average_buy_price"],
                    "current_price": current_price,
                    "total_invested": holding["total_invested"],
                    "current_value": current_value,
                    "profit_loss": profit_loss,
                    "profit_loss_percent": profit_loss_percent,
                    "price_change_24h": current_data.get("price_change_24h", 0),
                    "first_purchase_date": holding["first_purchase_date"].isoformat(),
                    "last_update": datetime.now(timezone.utc).isoformat()
                })
        
        # Calcular métricas do portfolio
        total_profit_loss = total_value - total_invested
        total_profit_loss_percent = (total_profit_loss / total_invested) * 100 if total_invested > 0 else 0
        
        # Encontrar melhor e pior performance
        best_performer = max(assets, key=lambda x: x["profit_loss_percent"]) if assets else None
        worst_performer = min(assets, key=lambda x: x["profit_loss_percent"]) if assets else None
        
        return {
            "assets": sorted(assets, key=lambda x: x["current_value"], reverse=True),
            "summary": {
                "total_value": round(total_value, 2),
                "total_invested": round(total_invested, 2),
                "total_profit_loss": round(total_profit_loss, 2),
                "total_profit_loss_percent": round(total_profit_loss_percent, 2),
                "assets_count": len(assets),
                "best_performer": best_performer,
                "worst_performer": worst_performer
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar holdings: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno do servidor"
        )

@router.get("/wallet/summary")
async def get_wallet_summary():
    """
    Retorna resumo executivo do wallet
    """
    try:
        holdings_data = await get_wallet_holdings()
        return holdings_data["summary"]
        
    except Exception as e:
        logger.error(f"Erro ao gerar resumo do wallet: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno do servidor"
        )

# Função auxiliar para atualizar holdings
# Função auxiliar para recalcular holdings
async def update_wallet_holdings(symbol: str):
    """
    Atualiza holdings de um ativo baseado nas transações
    """
    try:
        db = DatabaseManager()
        
        # Buscar transações do ativo
        transactions = list(db.wallet_transactions.find({"symbol": symbol.lower()}).sort("date", 1))
        
        if not transactions:
            db.delete_holding(symbol)
            return

        total_quantity = 0
        total_invested = 0
        weighted_price_sum = 0
        first_purchase_date = transactions[0]["date"]

        for tx in transactions:
            if tx["transaction_type"] == "buy":
                total_quantity += tx["quantity"]
                total_invested += tx["total_value"]
                weighted_price_sum += tx["quantity"] * tx["price_per_unit"]
            elif tx["transaction_type"] == "sell":
                if total_quantity >= tx["quantity"]:
                    avg_cost = weighted_price_sum / total_quantity if total_quantity > 0 else 0
                    cost_of_sold = avg_cost * tx["quantity"]
                    total_quantity -= tx["quantity"]
                    total_invested -= cost_of_sold
                    weighted_price_sum -= avg_cost * tx["quantity"]
                else:
                    logger.warning(f"Venda de {tx['quantity']} excede holdings de {total_quantity} para {symbol}")

        average_buy_price = weighted_price_sum / total_quantity if total_quantity > 0 else 0

        holding_doc = {
            "symbol": symbol.lower(),
            "asset_type": transactions[0]["asset_type"],
            "total_quantity": total_quantity,
            "average_buy_price": average_buy_price,
            "total_invested": total_invested,
            "first_purchase_date": first_purchase_date,
            "updated_at": datetime.now(timezone.utc)
        }

        db.update_holding(symbol, holding_doc)
        logger.info(f"Holdings atualizados para {symbol}: {total_quantity} unidades")
        
    except Exception as e:
        logger.error(f"Erro ao atualizar holdings para {symbol}: {e}")
        raise
