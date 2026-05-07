from datetime import datetime, time
from zoneinfo import ZoneInfo


class SessionEngine:
    def __init__(self, timezone="America/New_York"):
        self.tz = ZoneInfo(timezone)

        self.sessions = {
            "asia": (time(18, 0), time(0, 0)),
            "london": (time(2, 0), time(5, 0)),
            "new_york": (time(9, 0), time(12, 0)),
        }

    def get_session_name(self, dt=None):
        if dt is None:
            dt = datetime.now(self.tz)

        current_time = dt.time()

        for name, (start, end) in self.sessions.items():
            if start < end:
                if start <= current_time <= end:
                    return name
            else:
                if current_time >= start or current_time <= end:
                    return name

        return "outside_session"

    def session_levels(self, candles, session_name):
        if not candles:
            return None

        session_candles = [
            c for c in candles
            if c.get("session") == session_name
        ]

        if not session_candles:
            return None

        return {
            "session": session_name,
            "high": max(c["high"] for c in session_candles),
            "low": min(c["low"] for c in session_candles),
        }

    def detect_sweep(self, candles, session_name):
        if len(candles) < 2:
            return None

        levels = self.session_levels(candles[:-1], session_name)

        if not levels:
            return None

        current = candles[-1]

        if current["high"] > levels["high"] and current["close"] < levels["high"]:
            return {
                "type": "Buy-side Liquidity Sweep",
                "session": session_name,
                "level": levels["high"],
                "bias": "short",
                "message": f"Swept {session_name} high and closed back below."
            }

        if current["low"] < levels["low"] and current["close"] > levels["low"]:
            return {
                "type": "Sell-side Liquidity Sweep",
                "session": session_name,
                "level": levels["low"],
                "bias": "long",
                "message": f"Swept {session_name} low and closed back above."
            }

        return None