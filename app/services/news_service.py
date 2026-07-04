import requests
from bs4 import BeautifulSoup
import random
from datetime import datetime
from app.database import SessionLocal, MarketNews
from sqlalchemy.orm import Session

class NewsService:
    def __init__(self):
        self.sources = [
            {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/"},
            {"name": "CoinTelegraph", "url": "https://cointelegraph.com/rss"}
        ]
        # Fallback/Mock for demo if scraping fails or is blocked
        self.mock_news = [
            {"title": "Bitcoin Breaks $96k Resistance Amidst Institutional Inflow", "source": "CryptoDaily", "sentiment": 0.8, "category": "market"},
            {"title": "SEC Delays Decision on Ethereum ETF Again", "source": "BlockNews", "sentiment": -0.4, "category": "market"},
            {"title": "Global Geopolitical Tensions Rise, Investors Flock to Safe Havens", "source": "WorldFinance", "sentiment": 0.6, "category": "geopolitical"},
            {"title": "Tech Giants Announce New Blockchain Initiatives", "source": "TechInsider", "sentiment": 0.7, "category": "business"},
            {"title": "Inflation Data Higher Than Expected, Markets React", "source": "EconTimes", "sentiment": -0.6, "category": "market"},
            {"title": "New Trade Deal Impacts Global Supply Chains", "source": "GlobalTrade", "sentiment": 0.3, "category": "geopolitical"},
            {"title": "Major Bank Launches Crypto Custody Service", "source": "FinanceWeek", "sentiment": 0.9, "category": "business"}
        ]
        self.cache = []
        self.last_fetch = None
        self.cache_duration = 300 # 5 minutes

    def fetch_latest_news(self, db: Session):
        # Check cache
        if self.last_fetch and (datetime.now() - self.last_fetch).total_seconds() < self.cache_duration:
            if self.cache:
                return self.cache

        # Try to fetch real RSS feeds (Placeholder)
        news_items = []
        try:
            pass 
        except Exception as e:
            print(f"News Fetch Error: {e}")

        # If no real news fetched, generate "Real-like" intelligence
        if not news_items:
            # Check if we have recent news in DB
            cached_news = db.query(MarketNews).order_by(MarketNews.id.desc()).limit(20).all()
            if cached_news:
                self.cache = cached_news
                self.last_fetch = datetime.now()
                return cached_news
            
            # If DB empty, seed it
            for item in self.mock_news:
                news = MarketNews(
                    title=item["title"],
                    source=item["source"],
                    url="#",
                    published_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
                    sentiment_score=item["sentiment"],
                    category=item["category"],
                    summary=f"AI Agent Summary: {item['title']}..."
                )
                db.add(news)
                news_items.append(news)
            db.commit()
            
        self.cache = news_items
        self.last_fetch = datetime.now()
        return news_items

    def analyze_sentiment(self, text: str) -> float:
        # Placeholder for NLP sentiment analysis
        # In production, this would call an AI model
        words = text.lower().split()
        positive = ['bull', 'up', 'gain', 'profit', 'growth', 'high', 'break', 'etf', 'approve']
        negative = ['bear', 'down', 'loss', 'drop', 'crash', 'ban', 'sec', 'delay', 'inflation']
        
        score = 0
        for w in words:
            if w in positive: score += 0.2
            if w in negative: score -= 0.2
            
        return max(min(score, 1.0), -1.0)

news_service = NewsService()
