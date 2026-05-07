import yfinance as yf
from datetime import datetime
from app.services.session_engine import SessionEngine


class LiveFuturesFeed:
    def __init__(self):
        self.nq_ticker = yf.Ticker("NQ=F")
        self.es_ticker = yf.Ticker("ES=F")
        self.nq_history = []
        self.es_history = []
        self.session_engine = SessionEngine()
        self._last_nq = None
        self._last_es = None
        # Pre-seed history with last 30 minutes of 1m bars on startup
        self._seed_history()

    def _seed_history(self):
        """Load recent 1m bars on startup so signals fire immediately."""
        try:
            nq_hist = self.nq_ticker.history(period="1d", interval="1m")
            es_hist = self.es_ticker.history(period="1d", interval="1m")
            session = self.session_engine.get_session_name()

            for i, (nq_row, es_row) in enumerate(zip(
                nq_hist.itertuples(), es_hist.itertuples()
            )):
                ts = nq_row.Index
                t = ts.strftime("%H:%M:%S") if hasattr(ts, "strftime") else str(ts)
                nq_c = {
                    "symbol": "NQ", "time": t, "session": session,
                    "open":   round(float(nq_row.Open),   2),
                    "high":   round(float(nq_row.High),   2),
                    "low":    round(float(nq_row.Low),    2),
                    "close":  round(float(nq_row.Close),  2),
                    "volume": int(nq_row.Volume),
                }
                es_c = {
                    "symbol": "ES", "time": t, "session": session,
                    "open":   round(float(es_row.Open),   2),
                    "high":   round(float(es_row.High),   2),
                    "low":    round(float(es_row.Low),    2),
                    "close":  round(float(es_row.Close),  2),
                    "volume": int(es_row.Volume),
                }
                self.nq_history.append(nq_c)
                self.es_history.append(es_c)

            self.nq_history = self.nq_history[-500:]
            self.es_history = self.es_history[-500:]
            print(f"[data_feed] Seeded {len(self.nq_history)} historical candles")

            if self.nq_history:
                self._last_nq = self.nq_history[-1]
            if self.es_history:
                self._last_es = self.es_history[-1]

        except Exception as e:
            print(f"[data_feed] Seed error: {e}")

    def _fetch(self, ticker):
        try:
            hist = ticker.history(period="1d", interval="1m")
            if hist.empty:
                return None
            row = hist.iloc[-1]
            return {
                "open":   round(float(row["Open"]),  2),
                "high":   round(float(row["High"]),  2),
                "low":    round(float(row["Low"]),   2),
                "close":  round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            }
        except Exception as e:
            print(f"[data_feed] fetch error: {e}")
            return None

    def _candle(self, symbol, ohlcv):
        return {
            "symbol":  symbol,
            "time":    datetime.now().strftime("%H:%M:%S"),
            "session": self.session_engine.get_session_name(),
            "open":    ohlcv["open"],
            "high":    ohlcv["high"],
            "low":     ohlcv["low"],
            "close":   ohlcv["close"],
            "volume":  ohlcv["volume"],
        }

    def next_snapshot(self):
        nq = self._fetch(self.nq_ticker)
        es = self._fetch(self.es_ticker)

        if nq: self._last_nq = nq
        else:  nq = self._last_nq or {"open":27500,"high":27500,"low":27500,"close":27500,"volume":0}

        if es: self._last_es = es
        else:  es = self._last_es or {"open":6750,"high":6750,"low":6750,"close":6750,"volume":0}

        nq_candle = self._candle("NQ", nq)
        es_candle = self._candle("ES", es)

        self.nq_history.append(nq_candle)
        self.es_history.append(es_candle)
        self.nq_history = self.nq_history[-500:]
        self.es_history = self.es_history[-500:]

        return {"nq": nq_candle, "es": es_candle}


class MockFuturesFeed:
    def __init__(self):
        import random
        self._r = random
        self.nq_price = 27589.00
        self.es_price = 6750.00
        self.nq_history = []
        self.es_history = []
        self.session_engine = SessionEngine()

    def _make_candle(self, symbol, last):
        move = self._r.uniform(-8,8) if symbol=="NQ" else self._r.uniform(-2,2)
        o = last; c = max(1, o + move)
        h = max(o,c) + abs(self._r.uniform(0,4))
        l = min(o,c) - abs(self._r.uniform(0,4))
        return {"symbol":symbol,"time":datetime.now().strftime("%H:%M:%S"),
                "session":self.session_engine.get_session_name(),
                "open":round(o,2),"high":round(h,2),"low":round(l,2),
                "close":round(c,2),"volume":self._r.randint(100,900)}, c

    def next_snapshot(self):
        nq, self.nq_price = self._make_candle("NQ", self.nq_price)
        es, self.es_price = self._make_candle("ES", self.es_price)
        self.nq_history.append(nq); self.es_history.append(es)
        self.nq_history = self.nq_history[-500:]
        self.es_history = self.es_history[-500:]
        return {"nq": nq, "es": es}
