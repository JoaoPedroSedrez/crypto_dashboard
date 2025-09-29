from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
from utils.helpers import logger, DatabaseManager
from bson import ObjectId

router = APIRouter()
db = DatabaseManager()

# Nome da coleção no MongoDB
INCOME_COLLECTION = "incomes"

# =============================================================================
# 1. MODELOS PYDANTIC (Para validação de dados)
# =============================================================================

class IncomeCreate(BaseModel):
    """Modelo para criar um novo registro de provento."""
    asset_code: str = Field(..., description="Código do ativo (ex: BTLG11, PETR4)")
    asset_type: str = Field(..., description="Tipo de ativo ('stock' ou 'fii')")
    income_type: str = Field(..., description="Tipo de provento ('dividends', 'jcp' ou 'yield')")
    quantity: float = Field(..., gt=0, description="Quantidade de ações/cotas que geraram o provento")
    value_per_unit: float = Field(..., gt=0, description="Valor do provento por ação/cota")
    payment_date: datetime = Field(..., description="Data do pagamento do provento")

    @field_validator('asset_type')
    @classmethod
    def validate_asset_type(cls, v):
        if v.lower() not in ['stock', 'fii']:
            raise ValueError('asset_type deve ser "stock" ou "fii"')
        return v.lower()
    
    @field_validator('income_type')
    @classmethod
    def validate_income_type(cls, v):
        if v.lower() not in ['dividends', 'jcp', 'yield']:
            raise ValueError('income_type deve ser "dividends", "jcp" ou "yield"')
        return v.lower()
        
    model_config = {
        "json_encoders": {
            datetime: lambda dt: dt.isoformat(),
        }
    }

class IncomeUpdate(IncomeCreate):
    """Modelo para atualizar um registro de provento, inclui o ID."""
    id: str = Field(..., description="ID do registro de provento a ser atualizado")

class IncomeItem(BaseModel):
    """Modelo de retorno para um item de provento."""
    id: str
    asset_code: str
    asset_type: str
    income_type: str
    quantity: float
    value_per_unit: float
    total_value: float
    payment_date: datetime
    
    model_config = {
        "from_attributes": True
    }

class SummaryResponse(BaseModel):
    """Modelo de resumo de proventos."""
    total_income: float
    income_stocks: float
    income_fiis: float
    income_last_month: float
    total_records: int
    last_update: datetime

class IncomeListResponse(BaseModel):
    """Modelo de resposta principal para a listagem."""
    summary: SummaryResponse
    incomes: List[IncomeItem]

# =============================================================================
# 2. FUNÇÕES AUXILIARES
# =============================================================================

def calculate_income_summary(incomes: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calcula o resumo dos proventos a partir da lista de documentos."""
    total_income = 0.0
    income_stocks = 0.0
    income_fiis = 0.0
    
    # Determina o período do mês passado (sem timezone para comparação)
    today = datetime.now()
    first_day_of_this_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Calcula o primeiro dia do mês passado
    first_day_of_last_month = first_day_of_this_month - timedelta(days=1)
    first_day_of_last_month = first_day_of_last_month.replace(day=1)
    
    income_last_month = 0.0
    
    for income in incomes:
        total_value = income.get('total_value', 0.0)
        total_income += total_value
        
        # Agrega por tipo de ativo
        if income.get('asset_type') == 'stock':
            income_stocks += total_value
        elif income.get('asset_type') == 'fii':
            income_fiis += total_value
            
        # Agrega por mês passado
        payment_date = income.get('payment_date')
        if isinstance(payment_date, datetime):
            # Remove timezone info para comparação se necessário
            compare_date = payment_date.replace(tzinfo=None) if payment_date.tzinfo else payment_date
            
            if compare_date >= first_day_of_last_month and compare_date < first_day_of_this_month:
                income_last_month += total_value

    return {
        "total_income": round(total_income, 2),
        "income_stocks": round(income_stocks, 2),
        "income_fiis": round(income_fiis, 2),
        "income_last_month": round(income_last_month, 2)
    }

# =============================================================================
# 3. ROTAS DA API
# =============================================================================

@router.post("/", status_code=201)
async def create_income_entry(income_data: IncomeCreate = Body(...)):
    """Adiciona um novo registro de provento (Dividendo, JCP ou Rendimento de FII)."""
    try:
        income_dict = income_data.model_dump()
        
        # Normaliza o código do ativo
        income_dict['asset_code'] = income_dict['asset_code'].upper()
        
        # Calcula o valor total
        income_dict['total_value'] = income_dict['quantity'] * income_dict['value_per_unit']
        
        # Adiciona timestamps
        income_dict['created_at'] = datetime.now(timezone.utc)
        income_dict['updated_at'] = datetime.now(timezone.utc)

        # Insere no MongoDB usando a coleção correta
        collection = db.db[INCOME_COLLECTION]
        result = collection.insert_one(income_dict)

        if result.inserted_id:
            logger.info(f"✅ Provento criado para {income_dict['asset_code']}. ID: {result.inserted_id}")
            return {"message": "Provento adicionado com sucesso!", "id": str(result.inserted_id)}
        
        raise HTTPException(status_code=500, detail="Erro ao inserir provento no banco de dados.")

    except ValueError as ve:
        logger.error(f"❌ Erro de validação: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"❌ Erro ao criar provento: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

@router.put("/", response_model=Dict[str, str])
async def update_income_entry(income_data: IncomeUpdate = Body(...)):
    """Atualiza um registro de provento existente."""
    try:
        income_id = income_data.id
        
        if not ObjectId.is_valid(income_id):
            raise HTTPException(status_code=400, detail="ID de provento inválido.")

        income_dict = income_data.model_dump(exclude={"id"})
        
        # Recalcula e normaliza campos
        income_dict['asset_code'] = income_dict['asset_code'].upper()
        income_dict['total_value'] = income_dict['quantity'] * income_dict['value_per_unit']
        income_dict['updated_at'] = datetime.now(timezone.utc)

        # Atualiza no MongoDB
        collection = db.db[INCOME_COLLECTION]
        result = collection.update_one(
            {"_id": ObjectId(income_id)},
            {"$set": income_dict}
        )
        
        if result.modified_count > 0 or result.matched_count > 0:
            logger.info(f"✅ Provento ID {income_id} atualizado com sucesso.")
            return {"message": "Provento atualizado com sucesso!"}
        
        raise HTTPException(status_code=404, detail=f"Provento com ID {income_id} não encontrado.")

    except HTTPException:
        raise
    except ValueError as ve:
        logger.error(f"❌ Erro de validação: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar provento ID {income_data.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

@router.delete("/{income_id}", response_model=Dict[str, str])
async def delete_income_entry(income_id: str):
    """Remove um registro de provento."""
    try:
        if not ObjectId.is_valid(income_id):
            raise HTTPException(status_code=400, detail="ID de provento inválido.")
        
        # Remove do MongoDB
        collection = db.db[INCOME_COLLECTION]
        result = collection.delete_one({"_id": ObjectId(income_id)})
        
        if result.deleted_count > 0:
            logger.info(f"✅ Provento ID {income_id} removido com sucesso.")
            return {"message": "Provento removido com sucesso!"}
        
        raise HTTPException(status_code=404, detail=f"Provento com ID {income_id} não encontrado.")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao deletar provento ID {income_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/", response_model=IncomeListResponse)
async def get_all_incomes_and_summary():
    """Retorna todos os registros de proventos e um resumo financeiro."""
    try:
        # Busca todos os proventos do MongoDB, ordenados pela data de pagamento
        collection = db.db[INCOME_COLLECTION]
        cursor = collection.find({}).sort("payment_date", -1)
        income_documents = list(cursor)
        
        # Se a lista estiver vazia, retorna um resumo zerado
        if not income_documents:
            logger.info("📊 Nenhum provento encontrado no banco de dados.")
            empty_summary = SummaryResponse(
                total_income=0.0,
                income_stocks=0.0,
                income_fiis=0.0,
                income_last_month=0.0,
                total_records=0,
                last_update=datetime.now(timezone.utc)
            )
            return IncomeListResponse(summary=empty_summary, incomes=[])

        # Calcula o resumo
        summary_data = calculate_income_summary(income_documents)
        
        # Mapeia os documentos para o modelo IncomeItem
        incomes_list = []
        for doc in income_documents:
            try:
                # Converte ObjectId para string
                doc['id'] = str(doc.pop('_id'))
                
                # Garante que payment_date seja datetime
                if 'payment_date' in doc:
                    if not isinstance(doc['payment_date'], datetime):
                        doc['payment_date'] = datetime.fromisoformat(str(doc['payment_date']))
                    # Remove timezone info se necessário para consistência
                    elif doc['payment_date'].tzinfo:
                        doc['payment_date'] = doc['payment_date'].replace(tzinfo=None)
                
                incomes_list.append(IncomeItem(**doc))
            except Exception as item_error:
                logger.error(f"❌ Erro ao processar item {doc.get('id', 'unknown')}: {item_error}")
                continue
        
        summary = SummaryResponse(
            total_income=summary_data['total_income'],
            income_stocks=summary_data['income_stocks'],
            income_fiis=summary_data['income_fiis'],
            income_last_month=summary_data['income_last_month'],
            total_records=len(incomes_list),
            last_update=datetime.now(timezone.utc)
        )
        
        logger.info(f"📊 Proventos carregados com sucesso! Total: {len(incomes_list)} registros")
        
        return IncomeListResponse(summary=summary, incomes=incomes_list)

    except Exception as e:
        logger.error(f"❌ Erro ao buscar proventos: {e}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        # Retorna resumo vazio em caso de erro
        empty_summary = SummaryResponse(
            total_income=0.0,
            income_stocks=0.0,
            income_fiis=0.0,
            income_last_month=0.0,
            total_records=0,
            last_update=datetime.now(timezone.utc)
        )
        return IncomeListResponse(summary=empty_summary, incomes=[])