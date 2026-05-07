# TradeLens AI Master

Python FastAPI dashboard for:
- Live/pluggable NQ and ES market data
- SMT divergence between Nasdaq and S&P
- FVG and IFVG detection
- BOS/MSS detection
- ICT window filter: 9:00 AM to 12:00 PM New York time
- Trade execution journal analytics
- Landing dashboard and Buy Bot page

## Run

```bash
cd tradelens_ai_master
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Current Data Mode

This starter uses mock live candles so you can build the UI and signal engine immediately.

Later, replace `app/services/data_feed.py` with:
- Tradovate WebSocket
- CME WebSocket
- Databento live futures
- Massive/Polygon futures feed
- Broker order execution API

Do not enable live trading until you have paper-traded and added broker-side risk controls.
