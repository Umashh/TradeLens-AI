from pathlib import Path
import asyncio
import json
from app.services.bot_engine import BotEngine

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.services.data_feed import LiveFuturesFeed
from app.services.signal_engine import SignalEngine
from app.services.analytics import TradeAnalytics


app = FastAPI(title="TradeLens AI Master")

BASE_DIR = Path(__file__).resolve().parent

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)

feed = LiveFuturesFeed()
engine = SignalEngine()
analytics = TradeAnalytics()
bot = BotEngine()


@app.get("/")
async def dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html"
    )


@app.get("/buy")
async def buy_bot(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="buy.html"
    )


@app.get("/api/performance")
async def performance():
    return analytics.summary()


@app.websocket("/ws/market")
async def market_socket(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            snapshot = feed.next_snapshot()

            signals = engine.analyze(
                nq_candles=feed.nq_history,
                es_candles=feed.es_history,
            )

            bot_status = bot.process(snapshot, signals)

            payload = {
                "nq": snapshot["nq"],
                "es": snapshot["es"],
                "signals": signals,
                "performance": analytics.summary(),
                "bot": bot_status,
            }

            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(5)  # Poll every 5s (yfinance rate limit friendly)

    except WebSocketDisconnect:
        print("Client disconnected")
