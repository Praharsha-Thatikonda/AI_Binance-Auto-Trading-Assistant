from fastapi import APIRouter, Depends, HTTPException, Body
from app.routers.auth import user_sessions, get_db
from app.database import User, WalletBalance, WalletTransaction, SessionLocalWallet, SessionLocalWeb3
from sqlalchemy.orm import Session
from app.services.web3_service import web3_service
from app.services.ai_service import ai_service
import ccxt
import json
from datetime import datetime, timedelta
import random
from pydantic import BaseModel

router = APIRouter(prefix="/api/wallet", tags=["wallet"])

wallet_cache = {}
CACHE_DURATION = 30


def get_current_user_id():
    if 'current_user' not in user_sessions:
        return None
    return user_sessions['current_user'].get('db_id')

def get_wallet_db():
    db = SessionLocalWallet()
    try:
        yield db
    finally:
        db.close()

def get_web3_db():
    db = SessionLocalWeb3()
    try:
        yield db
    finally:
        db.close()

@router.get("/transactions")
def get_transactions(wallet_db: Session = Depends(get_wallet_db)):
    user_id = get_current_user_id()
    if not user_id: return []
    
    txs = wallet_db.query(WalletTransaction).filter(WalletTransaction.user_id == user_id).order_by(WalletTransaction.id.desc()).limit(100).all()
    
    return [
        {
            "id": tx.id,
            "type": tx.type,
            "asset": tx.currency,
            "amount": tx.amount,
            "status": tx.status,
            "timestamp": tx.timestamp,
            "wallet_type": tx.wallet_type,
            "tx_hash": tx.tx_hash,
            "to_address": tx.to_address
        }
        for tx in txs
    ]


class TransactionRequest(BaseModel):
    type: str # deposit, withdraw, transfer
    currency: str
    amount: float
    to_address: str = None
    wallet_type: str = "spot" # spot, web3
    memo: str = None # Added memo field

@router.get("/assets")
async def get_assets(
    db: Session = Depends(get_db),
    wallet_db: Session = Depends(get_wallet_db)
):
    user_id = get_current_user_id()
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    # 1. Fetch Spot Balances
    local_balances = wallet_db.query(WalletBalance).filter(WalletBalance.user_id == user_id).all()
    assets_map = {b.currency: b.amount for b in local_balances}
    
    # 2. Fetch Web3 Balances (Aggregated for now)
    from app.database import Web3Balance
    web3_balances = wallet_db.query(Web3Balance).filter(Web3Balance.user_id == user_id).all()
    web3_assets_map = {b.currency: b.amount for b in web3_balances}

    # 3. Fetch Exchange Balances (Optional/Hybrid)
    user = db.query(User).filter(User.id == user_id).first()
    exchange_assets = {}
    
    if user.api_key:
        if user_id in wallet_cache and (datetime.now() - wallet_cache[user_id]['timestamp']).total_seconds() < CACHE_DURATION:
            exchange_assets = wallet_cache[user_id]['data'].get('raw_assets', {})
        else:
            try:
                exchange = ccxt.binance({
                    'apiKey': user.api_key,
                    'secret': user.api_secret,
                    'options': {'adjustForTimeDifference': True}
                })
                # Set timeout
                exchange.timeout = 5000
                balance = exchange.fetch_balance()
                for currency, amount in balance['total'].items():
                    if amount > 0:
                        exchange_assets[currency] = amount
                
                wallet_cache[user_id] = {
                    'data': {'raw_assets': exchange_assets},
                    'timestamp': datetime.now()
                }
            except Exception as e:
                print(f"CCXT Error: {e}")
                # Don't fail the whole request, just log and continue
                # Maybe return a warning flag?

    # 4. Merge Balances
    final_assets = []
    all_currencies = set(assets_map.keys()) | set(exchange_assets.keys())
    total_usdt = 0.0
    
    # Fetch Real-Time Prices via CCXT
    prices = {}
    try:
        exchange_public = ccxt.binance()
        exchange_public.timeout = 3000
        # Fetch a few common ones
        tickers = exchange_public.fetch_tickers(['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'USDT/USDT', 'BNB/USDT'])
        prices = {
            "BTC": tickers['BTC/USDT']['last'],
            "ETH": tickers['ETH/USDT']['last'],
            "SOL": tickers['SOL/USDT']['last'],
            "BNB": tickers['BNB/USDT']['last'],
            "USDT": 1.0
        }
    except Exception as e:
        print(f"Price Fetch Error: {e}")
        prices = {"USDT": 1.0, "BTC": 65000.0, "ETH": 3500.0, "SOL": 140.0, "BNB": 600.0}
    
    for currency in all_currencies:
        local_amt = assets_map.get(currency, 0.0)
        exch_amt = exchange_assets.get(currency, 0.0)
        total_amt = local_amt + exch_amt
        
        price = prices.get(currency, 0.0)
        # If price not found, try to guess or 0
        if price == 0 and currency not in prices:
             # Fallback for unknown coins
             price = 0
             
        val_usdt = total_amt * price
        total_usdt += val_usdt
        
        final_assets.append({
            "symbol": currency,
            "amount": round(total_amt, 6),
            "local_amount": round(local_amt, 6),
            "exchange_amount": round(exch_amt, 6),
            "value_usdt": round(val_usdt, 2),
            "current_price": price
        })

    # Web3 Assets List & Total
    web3_final_assets = []
    for currency, amount in web3_assets_map.items():
        price = prices.get(currency, 0.0)
        val_usdt = amount * price
        total_usdt += val_usdt # Add to total
        
        web3_final_assets.append({
            "symbol": currency,
            "amount": round(amount, 6),
            "value_usdt": round(val_usdt, 2),
            "current_price": price
        })
        
    # Calculate Exchange Total
    exchange_total_usdt = 0.0
    for asset in final_assets:
        exchange_total_usdt += asset['exchange_amount'] * asset['current_price']

    return {
        "total_balance_usdt": round(total_usdt, 2),
        "exchange_balance_usdt": round(exchange_total_usdt, 2),
        "assets": final_assets,
        "web3_assets": web3_final_assets
    }

@router.post("/transaction")
async def process_transaction(
    request: TransactionRequest,
    wallet_db: Session = Depends(get_wallet_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
        
    # Determine Wallet Type
    wallet_type = getattr(request, 'wallet_type', 'spot')
    
    if wallet_type == 'web3':
        from app.database import Web3Balance
        balance_model = Web3Balance
    else:
        balance_model = WalletBalance

    balance_entry = wallet_db.query(balance_model).filter(
        balance_model.user_id == user_id,
        balance_model.currency == request.currency
    ).first()
    
    if not balance_entry:
        balance_entry = balance_model(user_id=user_id, currency=request.currency, amount=0.0, updated_at=str(datetime.now()))
        wallet_db.add(balance_entry)
    
    # Process Logic
    if request.type == "withdraw":
        if wallet_type == 'web3':
            # Web3 Withdraw = On-Chain Send
            # This logic should ideally be in web3/send, but if called here:
             raise HTTPException(status_code=400, detail="Use Web3 Send for Web3 withdrawals")
        else:
            # Spot Withdraw
            if balance_entry.amount < request.amount:
                raise HTTPException(status_code=400, detail="Insufficient balance")
            balance_entry.amount -= request.amount
        
    elif request.type == "deposit":
        # Both Spot and Web3 Deposit = Add Funds (Simulation)
        balance_entry.amount += request.amount

    elif request.type == "transfer":
        if balance_entry.amount < request.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
        # Find recipient
        from app.database import SessionLocalUsers
        user_db = SessionLocalUsers()
        try:
            recipient = user_db.query(User).filter(
                (User.username == request.to_address) | (User.email == request.to_address)
            ).first()
            
            if not recipient:
                raise HTTPException(status_code=404, detail="Recipient user not found (username or email)")
            
            if recipient.id == user_id:
                raise HTTPException(status_code=400, detail="Cannot transfer to self")

            balance_entry.amount -= request.amount
            
            # Credit recipient (Same Wallet Type)
            recipient_balance = wallet_db.query(balance_model).filter(
                balance_model.user_id == recipient.id,
                balance_model.currency == request.currency
            ).first()
            
            if not recipient_balance:
                recipient_balance = balance_model(user_id=recipient.id, currency=request.currency, amount=0.0, updated_at=str(datetime.now()))
                wallet_db.add(recipient_balance)
            
            recipient_balance.amount += request.amount
            recipient_balance.updated_at = str(datetime.now())
            
        finally:
            user_db.close()
        
    balance_entry.updated_at = str(datetime.now())
    
    # Record Transaction
    tx = WalletTransaction(
        user_id=user_id,
        type=request.type.upper(),
        currency=request.currency,
        amount=request.amount,
        status="COMPLETED",
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        to_address=request.to_address,
        wallet_type=wallet_type
    )
    wallet_db.add(tx)
    wallet_db.commit()
    
    return {"status": "success", "message": f"{request.type.title()} of {request.amount} {request.currency} completed.", "new_balance": balance_entry.amount}

class ConvertRequest(BaseModel):
    from_currency: str
    to_currency: str
    amount: float

@router.post("/convert")
async def convert_assets(
    request: ConvertRequest,
    wallet_db: Session = Depends(get_wallet_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
        
    # Fetch Real-Time Prices via CCXT
    prices = {}
    try:
        exchange_public = ccxt.binance()
        tickers = exchange_public.fetch_tickers(['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'USDT/USDT'])
        prices = {
            "BTC": tickers['BTC/USDT']['last'],
            "ETH": tickers['ETH/USDT']['last'],
            "SOL": tickers['SOL/USDT']['last'],
            "USDT": 1.0
        }
    except Exception as e:
        print(f"Price Fetch Error: {e}")
        prices = {"USDT": 1.0, "BTC": 65000.0, "ETH": 3500.0, "SOL": 140.0}
    
    if request.from_currency not in prices or request.to_currency not in prices:
        raise HTTPException(status_code=400, detail="Currency not supported for conversion")
        
    # Check Balance
    from_balance = wallet_db.query(WalletBalance).filter(
        WalletBalance.user_id == user_id,
        WalletBalance.currency == request.from_currency
    ).first()
    
    if not from_balance or from_balance.amount < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
        
    # Calculate Conversion
    from_price = prices[request.from_currency]
    to_price = prices[request.to_currency]
    
    # amount * from_price = value_in_usd
    # value_in_usd / to_price = to_amount
    to_amount = (request.amount * from_price) / to_price
    
    # Execute
    from_balance.amount -= request.amount
    from_balance.updated_at = str(datetime.now())
    
    to_balance = wallet_db.query(WalletBalance).filter(
        WalletBalance.user_id == user_id,
        WalletBalance.currency == request.to_currency
    ).first()
    
    if not to_balance:
        to_balance = WalletBalance(user_id=user_id, currency=request.to_currency, amount=0.0, updated_at=str(datetime.now()))
        wallet_db.add(to_balance)
        
    to_balance.amount += to_amount
    to_balance.updated_at = str(datetime.now())
    
    # Record Transaction
    tx = WalletTransaction(
        user_id=user_id,
        type="CONVERT",
        currency=f"{request.from_currency}->{request.to_currency}",
        amount=request.amount,
        status="COMPLETED",
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        to_address=None
    )
    wallet_db.add(tx)
    wallet_db.commit()
    
    return {
        "status": "success", 
        "message": f"Converted {request.amount} {request.from_currency} to {round(to_amount, 6)} {request.to_currency}",
        "converted_amount": to_amount
    }

@router.post("/web3/create")
async def create_web3_wallet(
    web3_db: Session = Depends(get_web3_db),
    wallet_db: Session = Depends(get_wallet_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    try:
        wallet = web3_service.create_wallet(web3_db, user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Auto-faucet for new wallets (Give 10 ETH)
    from app.database import Web3Balance
    bal = wallet_db.query(Web3Balance).filter(Web3Balance.user_id == user_id, Web3Balance.currency == "ETH").first()
    if not bal:
        bal = Web3Balance(user_id=user_id, currency="ETH", amount=10.0, updated_at=str(datetime.now()))
        wallet_db.add(bal)
        wallet_db.commit()
    else:
        # If balance exists, maybe add more? No, just once per user for now to avoid abuse.
        pass
        
    return {"status": "success", "address": wallet.address, "message": "Wallet created successfully. 10 Test ETH credited."}

class DeleteWalletRequest(BaseModel):
    address: str

@router.post("/web3/delete")
async def delete_web3_wallet(
    request: DeleteWalletRequest,
    web3_db: Session = Depends(get_web3_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    try:
        web3_service.delete_wallet(web3_db, user_id, request.address)
        return {"status": "success", "message": "Wallet deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/web3/info")
async def get_web3_info(
    web3_db: Session = Depends(get_web3_db),
    wallet_db: Session = Depends(get_wallet_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    wallets = web3_service.get_wallets(web3_db, user_id)
    
    # Fetch balances for each wallet (Mock logic or DB query)
    # Since Web3Balance currently aggregates by User ID (simplified model), we'll just show the total balance for all wallets for now
    # Or we can split it if we update the model. For now, let's just show the aggregated ETH balance for the user.
    from app.database import Web3Balance
    eth_bal = wallet_db.query(Web3Balance).filter(Web3Balance.user_id == user_id, Web3Balance.currency == "ETH").first()
    balance = eth_bal.amount if eth_bal else 0.0

    return {
        "wallets": [
            {
                "address": w.address,
                "chain": w.chain,
                "private_key": w.private_key,
                "balance": balance # Simplified: All wallets share the user's "Web3 Balance" in this DB model
            }
            for w in wallets
        ]
    }

class Web3SendRequest(BaseModel):
    to_address: str
    amount: float
    currency: str = "ETH"

@router.post("/web3/send")
async def send_web3_transaction(
    request: Web3SendRequest,
    web3_db: Session = Depends(get_web3_db),
    wallet_db: Session = Depends(get_wallet_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    try:
        # Basic validation
        if not request.to_address.startswith("0x") or len(request.to_address) != 42:
             raise HTTPException(status_code=400, detail="Invalid Ethereum address")

        result = web3_service.process_internal_tx(
            web3_db, wallet_db, user_id, request.to_address, request.amount, request.currency
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class ChatRequest(BaseModel):
    message: str
    context: str = "wallet"

@router.post("/chat")
async def wallet_chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    # Fetch user config for AI
    from app.database import AIModelConfig
    config = db.query(AIModelConfig).filter(AIModelConfig.user_id == user_id, AIModelConfig.is_active == True).first()
    
    provider = "google" # Default
    api_key = None
    model_name = "gemini-pro"
    
    if config:
        provider = config.provider
        api_key = config.api_key
        model_name = config.model_name
    
    # If no config, maybe use system default or fail gracefully
    # For this demo, we'll try to use a default key if available in env, or return a static response if not.
    if not api_key:
         # Check user table for direct key (legacy)
         user = db.query(User).filter(User.id == user_id).first()
         if user.ai_api_key:
             api_key = user.ai_api_key
             provider = "google" # Assume google for legacy
    
    if not api_key:
        return {"response": "I'm sorry, but I need an API key to function. Please configure one in the AI Models settings."}
        
    try:
        system_prompt = "You are a helpful crypto wallet assistant. You can help with deposits, withdrawals, and explaining blockchain concepts. Keep answers concise."
        response = await ai_service.generate_response(request.message, provider, api_key, model_name, system_prompt)
        return {"response": response}
    except Exception as e:
        print(f"AI Chat Error: {e}")
        return {"response": "I'm having trouble connecting to my brain right now. Please try again later."}

class TradingModeRequest(BaseModel):
    mode: str # 'manual' or 'auto'

@router.get("/trading_mode")
async def get_trading_mode(db: Session = Depends(get_db)):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    user = db.query(User).filter(User.id == user_id).first()
    settings = json.loads(user.settings) if user.settings else {}
    
    return {"mode": settings.get("trading_mode", "manual")}

@router.post("/trading_mode")
async def set_trading_mode(
    request: TradingModeRequest,
    db: Session = Depends(get_db)
):
    user_id = get_current_user_id()
    if not user_id: raise HTTPException(status_code=401, detail="Not logged in")
    
    user = db.query(User).filter(User.id == user_id).first()
    settings = json.loads(user.settings) if user.settings else {}
    
    settings["trading_mode"] = request.mode
    user.settings = json.dumps(settings)
    db.commit()
    
    return {"status": "success", "mode": request.mode}
