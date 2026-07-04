import asyncio
import logging
from sqlalchemy.orm import Session
from app.database import SessionLocal, SessionLocalUsers, SessionLocalMarket, SessionLocalLogs, User, TradeHistory, BotLog, AIModelConfig
from app.services.news_service import news_service
import ccxt
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoTradingBot:
    def __init__(self):
        self.is_running = False
        self.loop = None

    async def start(self):
        if self.is_running: return
        self.is_running = True
        logger.info("Auto-Trading Bot Started")
        
        while self.is_running:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.error(f"Bot Cycle Error: {e}")
            
            # Wait for 1 minute before next cycle (or configurable)
            await asyncio.sleep(60)

    def stop(self):
        self.is_running = False
        logger.info("Auto-Trading Bot Stopped")

    async def run_cycle(self):
        db_users = SessionLocalUsers()
        db_market = SessionLocalMarket()
        try:
            # Get active users
            users = db_users.query(User).filter(User.is_active == True).all()
            
            for user in users:
                if not user.api_key: continue
                
                # We pass both sessions to process_user
                await self.process_user(user, db_market)
                
        finally:
            db_users.close()
            db_market.close()

    async def process_user(self, user: User, db_market: Session):
        # 1. Gather Intelligence
        news = news_service.fetch_latest_news(db_market)
        news_summary = "\n".join([f"- {n.title} (Sentiment: {n.sentiment_score})" for n in news[:3]])
        
        # 2. Analyze Market (BTC/USDT default)
        symbol = "BTC/USDT"
        try:
            exchange = ccxt.binance({
                'apiKey': user.api_key,
                'secret': user.api_secret,
                'options': {'adjustForTimeDifference': True}
            })
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # 3. AI Decision
            decision = await self.get_ai_decision(user, symbol, current_price, news_summary)
            
            # 4. Execute
            if decision['signal'] in ['BUY', 'SELL'] and decision['confidence'] > 0.8:
                self.log_action(user.id, "TRADE_SIGNAL", f"AI Signal: {decision['signal']} for {symbol} @ {current_price} | {decision['reason']}")
                # Execute trade logic here
            else:
                self.log_action(user.id, "INFO", f"Holding {symbol}. Signal: {decision['signal']} ({decision['confidence']}) | {decision['reason']}")
                
        except Exception as e:
            self.log_action(user.id, "ERROR", f"Error processing user: {str(e)}")

    async def get_ai_decision(self, user: User, symbol: str, price: float, news_context: str):
        from app.services.ai_service import ai_service
        
        # Default fallback
        decision = {"signal": "HOLD", "confidence": 0.0, "reason": "AI Error or Not Configured"}
        
        db_users = SessionLocalUsers()
        try:
            # Fetch User's AI Config
            config = db_users.query(AIModelConfig).filter(
                AIModelConfig.user_id == user.id,
                AIModelConfig.is_active == True
            ).first()
            
            provider = config.provider if config else "google"
            api_key = config.api_key if config else user.ai_api_key
            model_name = config.model_name if config else "gemini-pro"
            
            if not api_key:
                return {"signal": "HOLD", "confidence": 0.0, "reason": "No AI API Key Configured"}

            prompt = f"""
            Act as a crypto trading bot.
            Market: {symbol} at ${price}
            News Context: {news_context}
            User Strategy: {user.trading_strategy}
            Risk Level: {user.risk_level}
            
            Decide: BUY, SELL, or HOLD.
            Output JSON: {{ "signal": "...", "confidence": 0.0-1.0, "reason": "..." }}
            """

            try:
                response_text = await ai_service.generate_response(
                    prompt=prompt,
                    provider=provider,
                    api_key=api_key,
                    model_name=model_name,
                    system_prompt="You are a trading bot that outputs JSON.",
                    json_mode=True
                )
                
                # Clean up potential markdown if ai_service didn't catch it all (though it should)
                response_text = response_text.replace('```json', '').replace('```', '').strip()
                decision = json.loads(response_text)
                
            except Exception as e:
                logger.error(f"AI Decision Error: {e}")
                decision["reason"] = f"Error: {str(e)}"

        except Exception as e:
            logger.error(f"AI Decision Error: {e}")
            decision["reason"] = f"Error: {str(e)}"
        finally:
            db_users.close()
            
        return decision

    def log_action(self, user_id: int, level: str, message: str):
        db_logs = SessionLocalLogs()
        try:
            log = BotLog(
                user_id=user_id,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                level=level,
                message=message
            )
            db_logs.add(log)
            db_logs.commit()
        finally:
            db_logs.close()

bot_service = AutoTradingBot()
