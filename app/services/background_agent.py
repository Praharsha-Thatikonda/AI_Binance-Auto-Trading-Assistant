import ccxt.async_support as ccxt
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackgroundAgent:
    def __init__(self):
        self.exchange = ccxt.binance({'enableRateLimit': True})
        self.market_cache = {}
        self.cache_expiry = 60 # seconds

    async def get_market_context(self, symbol: str = "BTC/USDT") -> str:
        """Fetches real-time market data for a symbol."""
        try:
            # Check cache
            if symbol in self.market_cache:
                data, timestamp = self.market_cache[symbol]
                if (datetime.now().timestamp() - timestamp) < self.cache_expiry:
                    return self._format_market_data(data)

            # Fetch fresh data
            ticker = await self.exchange.fetch_ticker(symbol)
            # orderbook = await self.exchange.fetch_order_book(symbol, limit=5) # Optional: Add depth
            
            self.market_cache[symbol] = (ticker, datetime.now().timestamp())
            return self._format_market_data(ticker)
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
            return f"Market data for {symbol} unavailable."

    def _format_market_data(self, ticker: Dict) -> str:
        return f"""
        Symbol: {ticker['symbol']}
        Price: ${ticker['last']}
        24h Change: {ticker['percentage']}%
        24h High: ${ticker['high']}
        24h Low: ${ticker['low']}
        Volume: {ticker['quoteVolume']} USDT
        """

    async def get_user_context(self, user_id: int, db_session) -> str:
        """Fetches user-specific context (wallet, open orders)."""
        # This would require importing User/Wallet models and querying DB
        # For now, we'll return a placeholder or implement if models are available
        return "User context: [Wallet Balance: Hidden for security]"

    async def process_chat_request(self, message: str, context_type: str, model_name: str, api_key: str, provider: str, user_context: str = "") -> str:
        """
        Orchestrates the chat response:
        1. Identifies intent (e.g., asking for price).
        2. Fetches relevant background data.
        3. Calls the AI model with enriched context.
        """
        from app.services.ai_service import ai_service
        
        # 1. Identify Intent & Fetch Data
        background_info = ""
        if "price" in message.lower() or "market" in message.lower() or "btc" in message.lower():
            # Extract symbol if possible, default to BTC/USDT
            symbol = "BTC/USDT" 
            if "eth" in message.lower(): symbol = "ETH/USDT"
            elif "sol" in message.lower(): symbol = "SOL/USDT"
            
            market_data = await self.get_market_context(symbol)
            background_info += f"\n[Real-time Market Data]:\n{market_data}\n"

        # 2. Construct System Prompt
        system_prompt = f"""
        You are an advanced AI Trading Assistant.
        Your goal is to provide accurate, data-driven insights for crypto trading.
        
        Context: {context_type}
        {user_context}
        {background_info}
        
        Instructions:
        - Use the provided [Real-time Market Data] to answer questions about prices.
        - If the user asks about a specific coin not in the data, mention you are checking general market trends.
        - Be concise and professional.
        """

        # 3. Call AI Provider via AIService
        try:
            response = await ai_service.generate_response(
                prompt=message,
                provider=provider,
                api_key=api_key,
                model_name=model_name,
                system_prompt=system_prompt
            )
            return response

        except Exception as e:
            logger.error(f"AI Processing Error: {e}")
            return f"I encountered an error processing your request: {str(e)}"

    async def close(self):
        await self.exchange.close()

# Singleton instance
background_agent = BackgroundAgent()
