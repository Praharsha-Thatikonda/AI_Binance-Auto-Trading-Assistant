from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from app.routers.auth import user_sessions, get_db, pwd_context
from app.database import User
from sqlalchemy.orm import Session
import json

router = APIRouter(prefix="/api/profile", tags=["profile"])

# --- Pydantic Models ---
class UpdateProfileRequest(BaseModel):
    full_name: str
    phone_number: str
    gender: str
    bio: str = ""

class UpdateSecurityRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class UpdatePreferencesRequest(BaseModel):
    dark_mode: bool
    notifications: bool
    email_reports: bool
    trade_sounds: bool
    two_factor_auth: bool

class UpdateApiRequest(BaseModel):
    exchange: str
    api_key: str
    api_secret: str

# --- Helper ---
def get_current_user_id():
    if 'current_user' not in user_sessions:
        return None
    return user_sessions['current_user'].get('db_id')

# --- Endpoints ---

@router.post("/update")
async def update_profile(
    request: UpdateProfileRequest,
    db: Session = Depends(get_db)
):
    user_id = get_current_user_id()
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    user = db.query(User).filter(User.id == user_id).first()
    user.full_name = request.full_name
    user.phone_number = request.phone_number
    user.gender = request.gender
    
    # Store bio in settings
    settings = json.loads(user.settings) if user.settings else {}
    settings['bio'] = request.bio
    user.settings = json.dumps(settings)
    
    db.commit()
    
    return {"status": "success", "message": "Profile updated successfully"}

@router.post("/security")
async def update_security(
    request: UpdateSecurityRequest,
    db: Session = Depends(get_db)
):
    user_id = get_current_user_id()
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not pwd_context.verify(request.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    if request.new_password != request.confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")
        
    user.hashed_password = pwd_context.hash(request.new_password)
    db.commit()
    
    return {"status": "success", "message": "Password updated successfully"}

@router.post("/preferences")
async def update_preferences(
    request: UpdatePreferencesRequest,
    db: Session = Depends(get_db)
):
    user_id = get_current_user_id()
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    user = db.query(User).filter(User.id == user_id).first()
    
    # Store in settings JSON
    settings = json.loads(user.settings) if user.settings else {}
    settings['dark_mode'] = request.dark_mode
    settings['notifications'] = request.notifications
    settings['email_reports'] = request.email_reports
    settings['trade_sounds'] = request.trade_sounds
    settings['two_factor_auth'] = request.two_factor_auth
    user.settings = json.dumps(settings)
    
    db.commit()
    return {"status": "success", "message": "Preferences saved"}

@router.get("/api-keys")
async def get_api_keys(db: Session = Depends(get_db)):
    user_id = get_current_user_id()
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    user = db.query(User).filter(User.id == user_id).first()
    
    return {
        "binance": {
            "connected": bool(user.api_key),
            "key_preview": f"{user.api_key[:4]}..." if user.api_key else None
        },
        "kucoin": {
            "connected": False, # Placeholder
            "key_preview": None
        }
    }
