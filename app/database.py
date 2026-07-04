import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database URLs
# Database URLs
DB_URL_USERS = os.getenv("DB_URL_USERS", "sqlite:///./users.db")
DB_URL_MARKET = os.getenv("DB_URL_MARKET", "sqlite:///./market_data.db") # Trading DB
DB_URL_LOGS = os.getenv("DB_URL_LOGS", "sqlite:///./system_logs.db")
DB_URL_WALLET = os.getenv("DB_URL_WALLET", "sqlite:///./wallet.db")
DB_URL_WEB3 = os.getenv("DB_URL_WEB3", "sqlite:///./web3.db")
DB_URL_DATASETS = os.getenv("DB_URL_DATASETS", "sqlite:///./datasets.db")
DB_URL_AI_CHAT = os.getenv("DB_URL_AI_CHAT", "sqlite:///./ai_chat.db")

# Engines
engine_users = create_engine(DB_URL_USERS, connect_args={"check_same_thread": False})
engine_market = create_engine(DB_URL_MARKET, connect_args={"check_same_thread": False})
engine_logs = create_engine(DB_URL_LOGS, connect_args={"check_same_thread": False})
engine_wallet = create_engine(DB_URL_WALLET, connect_args={"check_same_thread": False})
engine_web3 = create_engine(DB_URL_WEB3, connect_args={"check_same_thread": False})
engine_datasets = create_engine(DB_URL_DATASETS, connect_args={"check_same_thread": False})
engine_ai_chat = create_engine(DB_URL_AI_CHAT, connect_args={"check_same_thread": False})

# Session Makers
SessionLocalUsers = sessionmaker(autocommit=False, autoflush=False, bind=engine_users)
SessionLocalMarket = sessionmaker(autocommit=False, autoflush=False, bind=engine_market)
SessionLocalLogs = sessionmaker(autocommit=False, autoflush=False, bind=engine_logs)
SessionLocalWallet = sessionmaker(autocommit=False, autoflush=False, bind=engine_wallet)
SessionLocalWeb3 = sessionmaker(autocommit=False, autoflush=False, bind=engine_web3)
SessionLocalDatasets = sessionmaker(autocommit=False, autoflush=False, bind=engine_datasets)
SessionLocalAIChat = sessionmaker(autocommit=False, autoflush=False, bind=engine_ai_chat)

# Backward compatibility
SessionLocal = SessionLocalUsers

Base = declarative_base()

# --- Users DB Models ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    gender = Column(String)
    phone_number = Column(String)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    api_key = Column(String, nullable=True)
    api_secret = Column(String, nullable=True)
    ai_api_key = Column(String, nullable=True)
    risk_level = Column(String, default="medium")
    trading_strategy = Column(String, default="trend")
    is_active = Column(Boolean, default=True)
    settings = Column(Text, default="{}")
    trading_interval = Column(String, default="1h")
    max_daily_loss = Column(Float, nullable=True)
    target_profit = Column(Float, nullable=True)
    active_agents = Column(String, default="technical,sentiment")

class AIModelConfig(Base):
    __tablename__ = "ai_configs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    provider = Column(String)
    model_name = Column(String)
    api_key = Column(String, nullable=True)
    is_active = Column(Boolean, default=False)
    settings = Column(Text, default="{}")

# --- Market/Trading DB Models ---
class TradeHistory(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    symbol = Column(String)
    side = Column(String)
    amount = Column(Float)
    price = Column(Float)
    timestamp = Column(String)
    status = Column(String)
    strategy_used = Column(String, nullable=True)
    ai_confidence = Column(Float, nullable=True)

class MarketNews(Base):
    __tablename__ = "market_news"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    source = Column(String)
    url = Column(String)
    published_at = Column(String)
    sentiment_score = Column(Float, nullable=True)
    category = Column(String, default="general") # market, geopolitical, business
    summary = Column(Text, nullable=True)

# --- Logs DB Models ---
class BotLog(Base):
    __tablename__ = "bot_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    timestamp = Column(String)
    level = Column(String)
    message = Column(String)
    context = Column(Text, nullable=True)

# --- AI Chat DB Models ---
class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    timestamp = Column(String)
    sender = Column(String) # 'user' or 'ai'
    message = Column(Text)
    context = Column(String) # 'market', 'dashboard', etc.
    model_used = Column(String, nullable=True)

# --- Datasets DB Models ---
class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    name = Column(String)
    type = Column(String) # csv, json, etc.
    path = Column(String) # File path or content reference
    size = Column(String)
    created_at = Column(String)
    description = Column(Text, nullable=True)

# --- Wallet DB Models ---
class WalletBalance(Base):
    __tablename__ = "wallet_balances"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    currency = Column(String, index=True) # USDT, BTC, etc.
    amount = Column(Float, default=0.0)
    updated_at = Column(String)

class Web3Balance(Base):
    __tablename__ = "web3_balances"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    currency = Column(String, index=True) # ETH, APP, etc.
    amount = Column(Float, default=0.0)
    updated_at = Column(String)

class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    type = Column(String) # DEPOSIT, WITHDRAW, TRANSFER, CONVERT
    currency = Column(String)
    amount = Column(Float)
    status = Column(String) # PENDING, COMPLETED, FAILED
    timestamp = Column(String)
    tx_hash = Column(String, nullable=True) # For real blockchain txs
    to_address = Column(String, nullable=True)
    wallet_type = Column(String, default="spot") # spot, web3

# --- Web3 DB Models ---
class Web3Wallet(Base):
    __tablename__ = "web3_wallets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    address = Column(String, unique=True)
    chain = Column(String) # ETH, SOL, BSC
    label = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    connected_at = Column(String)

class AppGeneratedWallet(Base):
    __tablename__ = "app_generated_wallets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    address = Column(String, unique=True)
    private_key = Column(String) # In production, this MUST be encrypted
    mnemonic = Column(String, nullable=True)
    chain = Column(String, default="APP-CHAIN")
    created_at = Column(String)

# Create Tables
Base.metadata.create_all(bind=engine_users)
Base.metadata.create_all(bind=engine_market)
Base.metadata.create_all(bind=engine_logs)
Base.metadata.create_all(bind=engine_wallet)
Base.metadata.create_all(bind=engine_web3)
Base.metadata.create_all(bind=engine_datasets)
Base.metadata.create_all(bind=engine_ai_chat)
