from fastapi import APIRouter, Request, HTTPException, Body
from app.routers.auth import user_sessions
import ccxt
from pydantic import BaseModel

router = APIRouter(tags=["trading"])

class OrderRequest(BaseModel):
    symbol: str
    side: str  # 'buy' or 'sell'
    type: str = 'market' # 'market' or 'limit'
    quantity: float = None # Optional: if None, use percentage of balance
    percentage: float = 10.0 # Default to using 10% of available balance for safety
    price: float = None # Required for limit orders
    stop_loss: float = None
    take_profit: float = None

@router.get("/trading/history")
async def get_order_history():
    if 'current_user' not in user_sessions:
        raise HTTPException(status_code=401, detail="User not logged in")
    
    user = user_sessions['current_user']
    
    try:
        exchange = ccxt.binance({
            'apiKey': user['apiKey'],
            'secret': user['secret'],
            'options': {'adjustForTimeDifference': True}
        })
        # Remove sandbox mode check unless explicitly requested for testnet, 
        # but user wants REAL operations. 
        # We will keep testnet support if the user has a flag for it, 
        # but default to real.
        if user.get('is_testnet'): 
             exchange.set_sandbox_mode(True)
        
        # Fetch recent orders (last 10)
        orders = exchange.fetch_orders(limit=10)
        return orders
    except Exception as e:
        print(f"Error fetching history: {e}")
        # Return empty list or raise error? 
        # Better to return empty list so UI doesn't break, but log the error.
        return []

@router.post("/trading/order")
async def execute_order(order: OrderRequest):
    if 'current_user' not in user_sessions:
        raise HTTPException(status_code=401, detail="User not logged in")
    
    api_key = user_sessions['current_user']['apiKey']
    api_secret = user_sessions['current_user']['secret']
    is_testnet = user_sessions['current_user'].get('is_testnet', False)
    
    try:
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True,
                'recvWindow': 60000
            }
        })
        
        if is_testnet:
            exchange.set_sandbox_mode(True)
            
        exchange.load_time_difference()
        
        # 1. Get Market Price if needed
        current_price = None
        if order.type == 'market':
            ticker = exchange.fetch_ticker(order.symbol)
            current_price = ticker['last']
        
        # 2. Calculate Quantity
        amount = order.quantity
        if amount is None:
            balance = exchange.fetch_balance()
            base, quote = order.symbol.split('/')
            
            if order.side == 'buy':
                quote_balance = balance['free'].get(quote, 0)
                if quote_balance == 0: raise HTTPException(status_code=400, detail=f"Insufficient {quote}")
                spend = quote_balance * (order.percentage / 100)
                price_for_calc = order.price if order.type == 'limit' else current_price
                amount = spend / price_for_calc
            elif order.side == 'sell':
                base_balance = balance['free'].get(base, 0)
                if base_balance == 0: raise HTTPException(status_code=400, detail=f"Insufficient {base}")
                amount = base_balance * (order.percentage / 100)

        # 3. Execute Order
        params = {}
        if order.stop_loss: params['stopLossPrice'] = order.stop_loss
        if order.take_profit: params['takeProfitPrice'] = order.take_profit

        trade_result = exchange.create_order(
            symbol=order.symbol,
            type=order.type,
            side=order.side,
            amount=amount,
            price=order.price if order.type == 'limit' else None,
            params=params
        )
        
        return {
            "status": "success",
            "side": order.side,
            "symbol": order.symbol,
            "amount": amount,
            "price": trade_result.get('price', current_price),
            "order_id": trade_result['id']
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trading/market-data")
async def get_market_data():
    if 'current_user' not in user_sessions:
        raise HTTPException(status_code=401, detail="User not logged in")
    
    user = user_sessions['current_user']
    try:
        # Try with user keys first
        exchange = ccxt.binance({
            'apiKey': user['apiKey'],
            'secret': user['secret'],
            'options': {'adjustForTimeDifference': True}
        })
        if user.get('is_testnet'): exchange.set_sandbox_mode(True)
        
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT']
        tickers = exchange.fetch_tickers(symbols)
    except Exception as e:
        print(f"User keys failed for market data, falling back to public: {e}")
        try:
            # Fallback to public instance
            exchange = ccxt.binance({'options': {'adjustForTimeDifference': True}})
            symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT']
            tickers = exchange.fetch_tickers(symbols)
        except Exception as e2:
            print(f"Public market data fetch failed: {e2}")
            return []
        
    result = []
    for symbol, data in tickers.items():
        result.append({
            "symbol": symbol,
            "price": data['last'],
            "change": data['percentage']
        })
    return result

@router.get("/dashboard")
async def dashboard(request: Request):
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="templates")
    
    if 'current_user' not in user_sessions:
        return templates.TemplateResponse("index.html", {"request": request, "error": "Please login first"})
    
    api_key = user_sessions['current_user']['apiKey']
    api_secret = user_sessions['current_user']['secret']
    is_testnet = user_sessions['current_user'].get('is_testnet', False)
    
    try:
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 60000
            }
        })
        
        if is_testnet:
            exchange.set_sandbox_mode(True)

        exchange.load_time_difference() # Force sync time
        balance = exchange.fetch_balance()
        assets = {k: v for k, v in balance['total'].items() if v > 0}
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request, 
            "assets": assets
        })
    except Exception as e:
        return templates.TemplateResponse("index.html", {"request": request, "error": str(e)})
