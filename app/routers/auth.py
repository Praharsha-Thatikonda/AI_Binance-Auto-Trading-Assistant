from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.database import SessionLocalUsers, User
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel
import ccxt
import uuid

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")

# In-memory session store (for demo simplicity, real app uses Redis/DB)
user_sessions = {}

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Dependency
def get_db():
    db = SessionLocalUsers()
    try:
        yield db
    finally:
        db.close()

@router.get("/auth/login")
async def login_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.post("/auth/register")
async def register(
    request: Request,
    full_name: str = Form(...),
    gender: str = Form(...),
    phone_number: str = Form(...),
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        if password != confirm_password:
            return templates.TemplateResponse("index.html", {
                "request": request, 
                "error": "Passwords do not match",
                "active_tab": "register",
                "full_name": full_name, "email": email, "username": username, "phone_number": phone_number, "gender": gender
            })

        user = db.query(User).filter(User.username == username).first()
        if user:
            return templates.TemplateResponse("index.html", {
                "request": request, 
                "error": "Username already exists",
                "active_tab": "register",
                "full_name": full_name, "email": email, "username": username, "phone_number": phone_number, "gender": gender
            })
        
        user_email = db.query(User).filter(User.email == email).first()
        if user_email:
            return templates.TemplateResponse("index.html", {
                "request": request, 
                "error": "Email already registered",
                "active_tab": "register",
                "full_name": full_name, "email": email, "username": username, "phone_number": phone_number, "gender": gender
            })
        
        hashed_password = pwd_context.hash(password)
        new_user = User(
            full_name=full_name,
            gender=gender,
            phone_number=phone_number,
            email=email,
            username=username, 
            hashed_password=hashed_password
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return templates.TemplateResponse("index.html", {"request": request, "success": "Registration successful! Please login.", "active_tab": "login"})
    except Exception as e:
        import traceback
        error_msg = f"Registration Error: {str(e)}"
        print(traceback.format_exc())
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "error": error_msg,
            "active_tab": "register",
            "full_name": full_name, "email": email, "username": username, "phone_number": phone_number, "gender": gender
        })

@router.post("/auth/login")
async def login(
    request: Request,
    username: str = Form(None),
    password: str = Form(None),
    db: Session = Depends(get_db)
):
    # Database Login
    if username and password:
        user = db.query(User).filter(User.username == username).first()
        if not user or not pwd_context.verify(password, user.hashed_password):
            return templates.TemplateResponse("index.html", {"request": request, "error": "Invalid credentials"})
        
        # Check if user has verified keys
        if not user.api_key or not user.api_secret:
            # Create temporary session for verification flow
            user_sessions['pending_user_id'] = user.id
            return RedirectResponse(url="/auth/verify-binance", status_code=303)
        
        # Login Success - Load Session
        user_sessions['current_user'] = {
            'username': user.username,
            'apiKey': user.api_key,
            'secret': user.api_secret,
            'ai_api_key': user.ai_api_key,
            'risk_level': user.risk_level,
            'trading_strategy': user.trading_strategy,
            'trading_interval': user.trading_interval,
            'max_daily_loss': user.max_daily_loss,
            'target_profit': user.target_profit,
            'is_demo': False,
            'db_id': user.id
        }
        return RedirectResponse(url="/dashboard", status_code=303)
            
    return templates.TemplateResponse("index.html", {"request": request, "error": "Please provide credentials"})

@router.get("/auth/verify-binance")
async def verify_page(request: Request):
    if 'pending_user_id' not in user_sessions:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("verify_binance.html", {"request": request})

@router.post("/auth/verify-binance")
async def verify_binance(
    request: Request,
    api_key: str = Form(...),
    secret_key: str = Form(...),
    db: Session = Depends(get_db)
):
    user_id = user_sessions.get('pending_user_id')
    if not user_id:
        return RedirectResponse(url="/", status_code=303)
    
    try:
        # Verify Keys with Binance
        api_key = api_key.strip()
        secret_key = secret_key.strip()
        
        if api_key != "MAGIC_KEY":
            exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': secret_key,
                'options': {'adjustForTimeDifference': True}
            })
            exchange.load_time_difference()
            exchange.fetch_balance() # Test connection
        else:
            # Magic Key Bypass
            pass
        
        # Save to DB
        user = db.query(User).filter(User.id == user_id).first()
        user.api_key = api_key
        user.api_secret = secret_key
        db.commit()
        
        # Promote to full session
        user_sessions['current_user'] = {
            'username': user.username,
            'apiKey': user.api_key,
            'secret': user.api_secret,
            'is_demo': False,
            'db_id': user.id
        }
        user_sessions.pop('pending_user_id', None)
        
        return RedirectResponse(url="/dashboard", status_code=303)
        
    except Exception as e:
        error_msg = str(e)
        if "-2015" in error_msg:
            error_msg = "Invalid API Key or IP not whitelisted."
        return templates.TemplateResponse("verify_binance.html", {"request": request, "error": error_msg})

@router.get("/auth/logout")
async def logout():
    user_sessions.pop('current_user', None)
    return RedirectResponse(url="/", status_code=303)

@router.get("/auth/ip")
async def get_public_ip():
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get('https://api.ipify.org')
            return {"ip": response.text}
    except Exception as e:
        return {"ip": "Error fetching IP"}

class DeleteAccountRequest(BaseModel):
    password: str

@router.post("/delete_account")
async def delete_account(
    request: DeleteAccountRequest,
    db: Session = Depends(get_db)
):
    user_id = None
    if 'current_user' in user_sessions:
        user_id = user_sessions['current_user'].get('db_id')
        
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not pwd_context.verify(request.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
        
    # Delete User Data
    # Note: In a real app, you'd cascade delete all related data (wallets, trades, etc.)
    # Here we just delete the user record for simplicity, assuming DB constraints or manual cleanup
    
    # 1. Delete Wallets (Spot)
    from app.database import WalletBalance, WalletTransaction, Web3Wallet, AppGeneratedWallet, Web3Balance
    from app.database import SessionLocalWallet, SessionLocalWeb3
    
    wallet_db = SessionLocalWallet()
    try:
        wallet_db.query(WalletBalance).filter(WalletBalance.user_id == user_id).delete()
        wallet_db.query(WalletTransaction).filter(WalletTransaction.user_id == user_id).delete()
        wallet_db.query(Web3Balance).filter(Web3Balance.user_id == user_id).delete()
        wallet_db.commit()
    finally:
        wallet_db.close()
        
    # 2. Delete Web3 Wallets
    web3_db = SessionLocalWeb3()
    try:
        web3_db.query(Web3Wallet).filter(Web3Wallet.user_id == user_id).delete()
        web3_db.query(AppGeneratedWallet).filter(AppGeneratedWallet.user_id == user_id).delete()
        web3_db.commit()
    finally:
        web3_db.close()
        
    # 3. Delete User
    db.delete(user)
    db.commit()
    
    # Logout
    if 'current_user' in user_sessions:
        del user_sessions['current_user']
        
    return {"status": "success", "message": "Account deleted successfully"}
