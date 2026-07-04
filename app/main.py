from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from app.routers import auth, trading, ai, pages, wallet, profile
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="AI Trading Bot")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(auth.router)
app.include_router(trading.router)
app.include_router(ai.router)
app.include_router(pages.router)
app.include_router(wallet.router)
app.include_router(profile.router)

from app.services.trading_bot import bot_service
import asyncio

@app.on_event("startup")
async def startup_event():
    # Start the bot in background
    asyncio.create_task(bot_service.start())

@app.on_event("shutdown")
def shutdown_event():
    bot_service.stop()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
