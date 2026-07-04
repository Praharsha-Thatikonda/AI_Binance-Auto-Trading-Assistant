from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from app.routers.auth import user_sessions
import ccxt

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="templates")

def get_current_user():
    return user_sessions.get('current_user')

from app.services.news_service import news_service
from app.routers.auth import get_db
from app.database import SessionLocalMarket
from sqlalchemy.orm import Session
from fastapi import Depends

def get_market_db():
    db = SessionLocalMarket()
    try:
        yield db
    finally:
        db.close()

@router.get("/market")
async def market_page(request: Request, db: Session = Depends(get_market_db)):
    user = get_current_user()
    if not user:
        return templates.TemplateResponse("index.html", {"request": request, "error": "Please login first"})
    
    news = news_service.fetch_latest_news(db)
    
    return templates.TemplateResponse("market.html", {"request": request, "news": news})

from app.database import SessionLocalUsers, SessionLocalWallet, User, WalletBalance, WalletTransaction
from datetime import datetime

def get_wallet_db():
    db = SessionLocalWallet()
    try:
        yield db
    finally:
        db.close()

@router.get("/wallet")
async def wallet_page(request: Request):
    try:
        user_session = get_current_user()
        if not user_session:
            return templates.TemplateResponse("index.html", {"request": request, "error": "Please login first"})
        
        user_id = user_session.get('db_id')
        if not user_id:
             return templates.TemplateResponse("index.html", {"request": request, "error": "Session invalid"})
        
        # 1. Fetch User & Keys
        db_users = SessionLocalUsers()
        user = db_users.query(User).filter(User.id == user_id).first()
        db_users.close()
        
        if not user:
            return templates.TemplateResponse("index.html", {"request": request, "error": "User not found"})
        
        # 2. Fetch Local Wallet
        db_wallet = SessionLocalWallet()
        local_balances = db_wallet.query(WalletBalance).filter(WalletBalance.user_id == user_id).all()
        
        # 3. Fetch Exchange (Optional)
        exchange_assets = {}
        if user.api_key:
            try:
                exchange = ccxt.binance({
                    'apiKey': user.api_key,
                    'secret': user.api_secret,
                    'options': {'adjustForTimeDifference': True}
                })
                # Timeout or simple fetch
                balance = exchange.fetch_balance()
                exchange_assets = {k: v for k, v in balance['total'].items() if v > 0}
            except Exception as e:
                print(f"Exchange Fetch Error: {e}")
                
        # 4. Merge & Format (Return as Dict for Old Template)
        # Old template expects: assets = {'BTC': 0.1, 'USDT': 100.0}
        assets_map = {b.currency: b.amount for b in local_balances}
        all_currencies = set(assets_map.keys()) | set(exchange_assets.keys())
        
        final_assets = {}
        total_usdt = 0.0
        prices = {"USDT": 1.0, "BTC": 65000.0, "ETH": 3500.0, "SOL": 140.0} # Mock prices
        
        for currency in all_currencies:
            amount = assets_map.get(currency, 0.0) + exchange_assets.get(currency, 0.0)
            final_assets[currency] = round(amount, 6)
            
            # Calculate Total
            price = prices.get(currency, 0.0)
            total_usdt += amount * price
            
        # 5. Recent Transactions
        # Old template expects: trade.side, trade.symbol, trade.datetime, trade.amount
        recent_trades = []
        txs = db_wallet.query(WalletTransaction).filter(WalletTransaction.user_id == user_id).order_by(WalletTransaction.id.desc()).limit(10).all()
        db_wallet.close()
        
        for tx in txs:
            recent_trades.append({
                "side": "buy" if tx.type == "DEPOSIT" else "sell", # Map DEPOSIT->buy (green), WITHDRAW->sell (red)
                "symbol": tx.currency,
                "amount": tx.amount,
                "datetime": tx.timestamp, # Old template used 'datetime'
                "type": tx.type
            })

        return templates.TemplateResponse("wallet.html", {
            "request": request, 
            "assets": final_assets, # Dictionary
            "total_balance": round(total_usdt, 2), # Old variable name
            "recent_trades": recent_trades
        })
    except Exception as e:
        print(f"Wallet Page Error: {e}")
        import traceback
        traceback.print_exc()
        return templates.TemplateResponse("index.html", {"request": request, "error": f"System Error: {str(e)}"})

from app.database import SessionLocalUsers, User

@router.get("/profile")
async def profile_page(request: Request):
    user_session = get_current_user()
    if not user_session:
        return templates.TemplateResponse("index.html", {"request": request, "error": "Please login first"})
    
    db = SessionLocalUsers()
    try:
        user = db.query(User).filter(User.id == user_session['db_id']).first()
        return templates.TemplateResponse("profile.html", {"request": request, "user": user})
    finally:
        db.close()

@router.get("/ai-models")
async def ai_models_page(request: Request):
    user = get_current_user()
    if not user:
        return templates.TemplateResponse("index.html", {"request": request, "error": "Please login first"})
    
    return templates.TemplateResponse("ai_models.html", {"request": request})
