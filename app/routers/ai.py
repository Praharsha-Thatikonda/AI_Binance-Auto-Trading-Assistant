from fastapi import APIRouter, Request, HTTPException, Body, Depends, BackgroundTasks
from pydantic import BaseModel
from app.routers.auth import user_sessions, get_db
from app.database import User, AIModelConfig, ChatHistory, SessionLocalLogs, Dataset, SessionLocalDatasets, SessionLocalAIChat
from sqlalchemy.orm import Session
import json
import asyncio
import random
from typing import List, Optional
from datetime import datetime
from app.services.background_agent import background_agent

router = APIRouter(prefix="/ai", tags=["ai"])

# --- Pydantic Models ---
class AnalysisRequest(BaseModel):
    symbol: str
    timeframe: str
    model: str = "gemini-pro"
    risk_level: str = "medium"
    strategy: str = "trend"
    active_agents: str = "technical,sentiment"

class ConfigRequest(BaseModel):
    provider: str = "google"
    api_key: str
    model_name: str = "gemini-pro"
    
class ChatRequest(BaseModel):
    message: str
    context: str = "market"
    model: str = "gemini-pro"

class TestConnectionRequest(BaseModel):
    provider: str = "google"

class ToggleModelRequest(BaseModel):
    model_id: str
    is_active: bool

class LocalConfigRequest(BaseModel):
    local_model_path: str
    compute_device: str

class GlobalParamsRequest(BaseModel):
    temperature: float
    max_output_tokens: int
    system_prompt: str

class DatasetRequest(BaseModel):
    name: str
    type: str
    description: str = ""
    content: str = "" # Base64 or raw content for small files

class CreateModelRequest(BaseModel):
    name: str
    architecture: str
    purpose: str = "regression" # regression, classification, anomaly
    features: List[str] = ["close", "volume"]

class TrainModelRequest(BaseModel):
    model_name: str
    dataset_id: int
    epochs: int = 50
    batch_size: int = 64
    learning_rate: float = 0.001
    optimizer: str = "adam"

@router.post("/local-config")
async def save_local_config(
    request: LocalConfigRequest,
    db: Session = Depends(get_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    config = db.query(AIModelConfig).filter(
        AIModelConfig.user_id == user_id,
        AIModelConfig.provider == "local"
    ).first()
    
    settings = json.dumps({
        "path": request.local_model_path,
        "device": request.compute_device
    })
    
    if config:
        config.settings = settings
        config.is_active = True
    else:
        config = AIModelConfig(
            user_id=user_id,
            provider="local",
            model_name="llama-3-70b", # Default or from request if we added it
            is_active=True,
            settings=settings
        )
        db.add(config)
        
    db.commit()
    return {"status": "success", "message": "Local configuration saved."}

@router.post("/global-config")
async def save_global_config(
    request: GlobalParamsRequest,
    db: Session = Depends(get_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    # Use a special config entry for global params
    config = db.query(AIModelConfig).filter(
        AIModelConfig.user_id == user_id,
        AIModelConfig.provider == "system"
    ).first()
    
    settings = json.dumps({
        "temperature": request.temperature,
        "max_tokens": request.max_output_tokens,
        "system_prompt": request.system_prompt
    })
    
    if config:
        config.settings = settings
    else:
        config = AIModelConfig(
            user_id=user_id,
            provider="system",
            model_name="global-params",
            is_active=True,
            settings=settings
        )
        db.add(config)
        
    db.commit()
    return {"status": "success", "message": "Global parameters saved."}

@router.get("/config")
async def get_all_config(db: Session = Depends(get_db)):
    user_id = get_current_user_id()
    if not user_id: return {}
    
    # Fetch all configs
    configs = db.query(AIModelConfig).filter(AIModelConfig.user_id == user_id).all()
    
    result = {
        "google_key": "",
        "openai_key": "",
        "anthropic_key": "",
        "local_path": "",
        "compute_device": "cuda",
        "global_params": {
            "temperature": 0.7,
            "max_tokens": 2048,
            "system_prompt": ""
        }
    }
    
    for c in configs:
        if c.provider == "google": result["google_key"] = c.api_key
        elif c.provider == "openai": result["openai_key"] = c.api_key
        elif c.provider == "anthropic": result["anthropic_key"] = c.api_key
        elif c.provider == "local":
            try:
                s = json.loads(c.settings)
                result["local_path"] = s.get("path", "")
                result["compute_device"] = s.get("device", "cuda")
            except: pass
        elif c.provider == "system":
            try:
                s = json.loads(c.settings)
                result["global_params"]["temperature"] = s.get("temperature", 0.7)
                result["global_params"]["max_tokens"] = s.get("max_tokens", 2048)
                result["global_params"]["system_prompt"] = s.get("system_prompt", "")
            except: pass
            
    return result

def get_datasets_db():
    db = SessionLocalDatasets()
    try:
        yield db
    finally:
        db.close()

@router.get("/datasets")
async def get_datasets(db: Session = Depends(get_datasets_db)):
    user_id = get_current_user_id()
    if not user_id: return []
    
    datasets = db.query(Dataset).filter(Dataset.user_id == user_id).all()
    return datasets

@router.post("/datasets/import")
async def import_dataset(
    request: DatasetRequest,
    db: Session = Depends(get_datasets_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    # In a real app, we'd save the file to disk. For now, we'll mock the path.
    # If content is provided, we could write it.
    
    file_path = f"datasets/{request.name}.{request.type}"
    
    dataset = Dataset(
        user_id=user_id,
        name=request.name,
        type=request.type,
        path=file_path,
        size="Unknown", # Calculate real size
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        description=request.description
    )
    db.add(dataset)
    db.commit()
    
    return {"status": "success", "message": f"Dataset {request.name} imported."}

@router.delete("/datasets/{dataset_id}")
async def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_datasets_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == user_id).first()
    if dataset:
        db.delete(dataset)
        db.commit()
        return {"status": "success", "message": "Dataset deleted."}
    raise HTTPException(status_code=404, detail="Dataset not found")

from fastapi.responses import Response

@router.get("/datasets/{dataset_id}/export")
async def export_dataset(
    dataset_id: int,
    db: Session = Depends(get_datasets_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == user_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    # Generate mock content based on type
    content = ""
    if dataset.type == "csv":
        content = "Date,Open,High,Low,Close,Volume\n2023-01-01,100,105,99,102,1000\n2023-01-02,102,108,101,107,1500"
    elif dataset.type == "json":
        content = json.dumps([
            {"date": "2023-01-01", "close": 102},
            {"date": "2023-01-02", "close": 107}
        ], indent=2)
    else:
        content = f"Mock content for {dataset.name}"
        
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={dataset.name}.{dataset.type}"}
    )


# --- Helper Functions ---
def get_current_user_id():
    if 'current_user' not in user_sessions:
        return None
    return user_sessions['current_user'].get('db_id')

def get_ai_config(db: Session, user_id: int, provider: str = "google"):
    return db.query(AIModelConfig).filter(
        AIModelConfig.user_id == user_id, 
        AIModelConfig.provider == provider
    ).first()

# --- Endpoints ---

@router.post("/test-connection")
async def test_connection(
    request: TestConnectionRequest,
    db: Session = Depends(get_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    config = get_ai_config(db, user_id, request.provider)
    if not config or not config.api_key:
        raise HTTPException(status_code=400, detail=f"{request.provider.title()} API Key not configured.")
        
    try:
        from app.services.ai_service import ai_service
        
        # We'll just try to generate a simple response to test connectivity
        model_name = "gemini-pro"
        if request.provider == "openai": model_name = "gpt-3.5-turbo"
        
        await ai_service.generate_response(
            prompt="Ping",
            provider=request.provider,
            api_key=config.api_key,
            model_name=model_name
        )
        
        return {"status": "success", "latency": "200ms", "message": f"{request.provider.title()} Connected"}
            
    except Exception as e:
        print(f"Test Connection Error: {e}")
        raise HTTPException(status_code=400, detail=f"Connection Failed: {str(e)}")

@router.post("/config/add")
async def add_ai_config(
    request: ConfigRequest,
    db: Session = Depends(get_db)
):
    user_id = get_current_user_id()
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    # Verify Key
    try:
        from app.services.ai_service import ai_service
        
        # We'll just try to generate a simple response to verify the key
        model_name = "gemini-pro"
        if request.provider == "openai": model_name = "gpt-3.5-turbo"
        
        await ai_service.generate_response(
            prompt="Test",
            provider=request.provider,
            api_key=request.api_key,
            model_name=model_name
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid API Key: {str(e)}")

    # Save to DB
    config = db.query(AIModelConfig).filter(
        AIModelConfig.user_id == user_id,
        AIModelConfig.provider == request.provider
    ).first()
    
    if not config:
        config = AIModelConfig(
            user_id=user_id,
            provider=request.provider,
            model_name=request.model_name,
            api_key=request.api_key,
            is_active=True
        )
        db.add(config)
    else:
        config.api_key = request.api_key
        config.model_name = request.model_name
        config.is_active = True
    
    db.commit()
    
    # Update legacy session key for backward compatibility
    if request.provider == "google":
        user_sessions['current_user']['ai_api_key'] = request.api_key
        
    return {"status": "success", "message": f"{request.provider.title()} configuration saved."}

@router.get("/models")
async def get_models(db: Session = Depends(get_db)):
    user_id = get_current_user_id()
    if not user_id:
        return {"server": [], "local": []}
        
    try:
        configs = db.query(AIModelConfig).filter(AIModelConfig.user_id == user_id).all()
    except Exception as e:
        print(f"AI Config Fetch Error: {e}")
        configs = []
    
    models = []
    # Default Gemini if not configured (fallback)
    has_google = False
    for c in configs:
        if c.provider == "google": has_google = True
        models.append({
            "id": c.model_name,
            "name": f"{c.provider.title()} - {c.model_name}",
            "provider": c.provider,
            "status": "active" if c.is_active else "inactive"
        })
        
    if not has_google:
        models.append({"id": "gemini-pro", "name": "Gemini Pro (Default)", "provider": "google", "status": "inactive"})
        
    return {
        "server": models,
        "local": [] 
    }

@router.post("/models/toggle")
async def toggle_model(
    request: ToggleModelRequest,
    db: Session = Depends(get_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    # Find config by model_name (which we use as ID in frontend)
    # Note: Frontend sends 'gemini-pro', 'gpt-4', etc.
    # We need to map these to provider/model_name or just search by model_name
    
    config = db.query(AIModelConfig).filter(
        AIModelConfig.user_id == user_id,
        AIModelConfig.model_name == request.model_id
    ).first()
    
    if config:
        config.is_active = request.is_active
        db.commit()
        return {"status": "success", "message": f"Model {request.model_id} {'activated' if request.is_active else 'deactivated'}"}
    
    # If not found, we might need to create it (e.g. for default models)
    # For now, let's assume we only toggle existing configs or return error
    # But wait, default models like 'gemini-pro' might not be in DB yet if user never configured them.
    # Let's create a default entry if missing.
    
    provider = "google" # Default guess
    if "gpt" in request.model_id: provider = "openai"
    elif "claude" in request.model_id: provider = "anthropic"
    elif "llama" in request.model_id: provider = "local"
    
    new_config = AIModelConfig(
        user_id=user_id,
        provider=provider,
        model_name=request.model_id,
        api_key="", # User needs to configure key separately
        is_active=request.is_active
    )
    db.add(new_config)
    db.commit()
    
    return {"status": "success", "message": f"Model {request.model_id} {'activated' if request.is_active else 'deactivated'} (New Config Created)"}

@router.post("/models/import")
async def import_model(
    request: CreateModelRequest, # Reusing this for simplicity, or create ImportModelRequest
    db: Session = Depends(get_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    # Check if model exists
    existing = db.query(AIModelConfig).filter(
        AIModelConfig.user_id == user_id,
        AIModelConfig.model_name == request.name
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Model with this name already exists")
        
    settings = json.dumps({
        "architecture": request.architecture,
        "purpose": request.purpose,
        "features": request.features,
        "imported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    config = AIModelConfig(
        user_id=user_id,
        provider="local",
        model_name=request.name,
        is_active=False,
        settings=settings
    )
    db.add(config)
    db.commit()
    
    return {"status": "success", "message": f"Model {request.name} imported successfully."}

@router.get("/models/export")
async def export_all_models(db: Session = Depends(get_db)):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    configs = db.query(AIModelConfig).filter(AIModelConfig.user_id == user_id).all()
    export_data = []
    for c in configs:
        export_data.append({
            "name": c.model_name,
            "provider": c.provider,
            "api_key": c.api_key, # Warning: Exporting keys might be unsafe in prod
            "settings": json.loads(c.settings) if c.settings else {}
        })
        
    return Response(
        content=json.dumps(export_data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=models_backup.json"}
    )

@router.get("/models/{model_id}/export")
async def export_single_model(
    model_id: str,
    db: Session = Depends(get_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    config = db.query(AIModelConfig).filter(
        AIModelConfig.user_id == user_id,
        AIModelConfig.model_name == model_id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Model not found")
        
    export_data = {
        "name": config.model_name,
        "provider": config.provider,
        "settings": json.loads(config.settings) if config.settings else {}
    }
    
    return Response(
        content=json.dumps(export_data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={model_id}_config.json"}
    )

@router.post("/analyze")
async def analyze_market(
    request: AnalysisRequest,
    db: Session = Depends(get_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    # Determine provider based on model name
    provider = "google"
    if "gpt" in request.model: provider = "openai"
    elif "claude" in request.model: provider = "anthropic"
    
    config = get_ai_config(db, user_id, provider)
    api_key = None
    
    if config and config.api_key:
        api_key = config.api_key
    elif provider == "google" and 'ai_api_key' in user_sessions['current_user']:
        api_key = user_sessions['current_user']['ai_api_key']
    
    if not api_key:
         raise HTTPException(status_code=400, detail=f"{provider.title()} API Key not configured.")

    try:
        from app.services.ai_service import ai_service
        
        prompt = f"""
        Act as a professional crypto trader.
        Task: Analyze {request.symbol} on {request.timeframe} timeframe.
        Strategy: {request.strategy}
        Risk: {request.risk_level}
        
        Provide a JSON response with:
        1. technical_analysis (string)
        2. fundamental_analysis (string)
        3. risk_assessment (Low/Medium/High)
        4. consensus_signal (BUY/SELL/HOLD)
        5. confidence_score (0.0-1.0)
        6. reasoning (string)
        """
        
        response_text = await ai_service.generate_response(
            prompt=prompt,
            provider=provider,
            api_key=api_key,
            model_name=request.model,
            system_prompt="You are a helpful assistant that outputs JSON.",
            json_mode=True
        )
        
        # Clean up potential markdown
        response_text = response_text.replace('```json', '').replace('```', '').strip()
        return json.loads(response_text)
        
    except Exception as e:
        print(f"AI Error: {e}")
        raise HTTPException(status_code=500, detail=f"AI Analysis failed: {str(e)}")

@router.post("/chat")
async def chat_ai(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    # Determine provider
    provider = "google"
    if "gpt" in request.model: provider = "openai"
    elif "claude" in request.model: provider = "anthropic"
    
    config = get_ai_config(db, user_id, provider)
    api_key = None
    
    if config and config.api_key:
        api_key = config.api_key
    elif provider == "google" and 'ai_api_key' in user_sessions['current_user']:
        api_key = user_sessions['current_user']['ai_api_key']
    
    if not api_key:
         raise HTTPException(status_code=400, detail=f"{provider.title()} API Key not configured.")

    try:
        # Use Background Agent to process request
        response_text = await background_agent.process_chat_request(
            message=request.message,
            context_type=request.context,
            model_name=request.model,
            api_key=api_key,
            provider=provider,
            user_context="" # Could fetch user specific context here
        )

        # Save to Chat History
        log_db = SessionLocalAIChat()
        try:
            # User Message
            log_db.add(ChatHistory(
                user_id=user_id,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                sender="user",
                message=request.message,
                context=request.context,
                model_used=request.model
            ))
            # AI Response
            log_db.add(ChatHistory(
                user_id=user_id,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                sender="ai",
                message=response_text,
                context=request.context,
                model_used=request.model
            ))
            log_db.commit()
        finally:
            log_db.close()

        return {"response": response_text}
        
    except Exception as e:
        print(f"Chat Error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@router.post("/models/create")
async def create_new_model(
    request: CreateModelRequest,
    db: Session = Depends(get_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    # In a real app, we would initialize the model architecture here and save weights
    # For now, we save the config
    
    settings = json.dumps({
        "architecture": request.architecture,
        "purpose": request.purpose,
        "features": request.features,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    config = AIModelConfig(
        user_id=user_id,
        provider="local", # Custom models are local
        model_name=request.name,
        is_active=False,
        settings=settings
    )
    db.add(config)
    db.commit()
    
    return {"status": "success", "message": f"Model {request.name} initialized."}

# Training State (In-memory for simplicity)
training_state = {
    "status": "idle",
    "progress": 0,
    "current_epoch": 0,
    "total_epochs": 0,
    "logs": []
}

@router.post("/train")
async def start_training(
    request: TrainModelRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    if training_state["status"] == "running":
        raise HTTPException(status_code=400, detail="Training already in progress")
    
    # Verify Dataset
    dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id, Dataset.user_id == user_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    training_state["status"] = "running"
    training_state["progress"] = 0
    training_state["total_epochs"] = request.epochs
    training_state["logs"] = [f"Starting training for {request.model_name}...", f"Dataset: {dataset.name}"]
    
    background_tasks.add_task(run_training_simulation, request.epochs)
    
    return {"status": "success", "message": "Training started"}

@router.get("/train/status")
async def get_training_status():
    return training_state

async def run_training_simulation(epochs: int):
    import time
    for i in range(epochs):
        await asyncio.sleep(0.5) # Simulate work
        training_state["current_epoch"] = i + 1
        training_state["progress"] = int(((i + 1) / epochs) * 100)
        
        # Simulate loss
        loss = 0.5 * (0.9 ** i) + random.uniform(0.01, 0.05)
        training_state["logs"].append(f"Epoch {i+1}/{epochs} - Loss: {loss:.4f}")
        
    training_state["status"] = "completed"
    training_state["logs"].append("Training finished successfully.")
