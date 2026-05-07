from datetime import datetime, time
import zoneinfo
from app.services.session_engine import SessionEngine

NY_TZ = zoneinfo.ZoneInfo("America/New_York")


class SignalEngine:
    def __init__(self):
        self.window_start   = time(9, 0)
        self.window_end     = time(12, 0)
        self.session_engine = SessionEngine()

        # Signal memory
        self._smt_signal   = None;  self._smt_ttl   = 0
        self._bos_signal   = None;  self._bos_ttl   = 0
        self._sweep_signal = None;  self._sweep_ttl = 0
        self._fvg_signal   = None;  self._fvg_ttl   = 0
        self.TTL = 50

        # Liquidity levels — computed once from history
        self._levels_computed = False
        self._prev_day_high   = None
        self._prev_day_low    = None
        self._asia_high       = None
        self._asia_low        = None
        self._london_high     = None
        self._london_low      = None
        self._4h_levels       = []   # list of (high, low) per 4H block

    # ── TTL management ──────────────────────────────────────────────────────
    def _tick_ttl(self):
        for attr in ["_smt_ttl", "_bos_ttl", "_sweep_ttl", "_fvg_ttl"]:
            val = getattr(self, attr)
            if val > 0:
                setattr(self, attr, val - 1)
                if getattr(self, attr) == 0:
                    setattr(self, attr.replace("_ttl", "_signal"), None)

    def in_ict_window(self):
        return self.window_start <= datetime.now(NY_TZ).time() <= self.window_end

    # ── Liquidity level computation ──────────────────────────────────────────
    def _compute_levels(self, candles):
        """
        Derive all liquidity levels from the full candle history:
        - Previous day high/low (Asia + London candles before NY open)
        - Asia session high/low
        - London session high/low
        - All 4H block highs/lows (group 1m candles into 240-bar blocks)
        Called once per session, then cached.
        """
        if self._levels_computed or len(candles) < 10:
            return

        asia_c   = [c for c in candles if c.get("session") == "asia"]
        london_c = [c for c in candles if c.get("session") == "london"]
        pre_ny   = asia_c + london_c

        if asia_c:
            self._asia_high = max(c["high"] for c in asia_c)
            self._asia_low  = min(c["low"]  for c in asia_c)

        if london_c:
            self._london_high = max(c["high"] for c in london_c)
            self._london_low  = min(c["low"]  for c in london_c)

        if pre_ny:
            self._prev_day_high = max(c["high"] for c in pre_ny)
            self._prev_day_low  = min(c["low"]  for c in pre_ny)

        # 4H blocks: every 240 1m candles = one 4H candle
        block_size = 240
        self._4h_levels = []
        for i in range(0, len(candles) - block_size, block_size):
            block = candles[i:i + block_size]
            self._4h_levels.append({
                "high": max(c["high"] for c in block),
                "low":  min(c["low"]  for c in block),
                "start": block[0]["time"],
                "end":   block[-1]["time"],
            })

        self._levels_computed = True
        print(f"[signal_engine] Levels computed:")
        print(f"  PDH={self._prev_day_high} PDL={self._prev_day_low}")
        print(f"  Asia H={self._asia_high} L={self._asia_low}")
        print(f"  London H={self._london_high} L={self._london_low}")
        print(f"  4H blocks={len(self._4h_levels)}")

    def _all_liquidity_levels(self):
        """Return all tracked levels as list of (label, high_or_low, direction)."""
        levels = []

        if self._prev_day_high: levels.append(("PDH",  self._prev_day_high, "high"))
        if self._prev_day_low:  levels.append(("PDL",  self._prev_day_low,  "low"))
        if self._asia_high:     levels.append(("Asia H", self._asia_high,   "high"))
        if self._asia_low:      levels.append(("Asia L", self._asia_low,    "low"))
        if self._london_high:   levels.append(("Lon H",  self._london_high, "high"))
        if self._london_low:    levels.append(("Lon L",  self._london_low,  "low"))

        for i, b in enumerate(self._4h_levels):
            levels.append((f"4H[{i}] H", b["high"], "high"))
            levels.append((f"4H[{i}] L", b["low"],  "low"))

        return levels

    # ── Sweep detection ──────────────────────────────────────────────────────
    def detect_sweep(self, nq_candles, es_candles):
        """
        Checks current candle against ALL liquidity levels:
        PDH, PDL, Asia H/L, London H/L, all 4H H/L.
        Sweep confirmed by: wick beyond level + close back inside.
        Most specific / recent level takes priority.
        """
        if len(nq_candles) < 5:
            return self._sweep_signal

        self._compute_levels(nq_candles)
        cur = nq_candles[-1]

        for label, level, direction in self._all_liquidity_levels():
            if direction == "low":
                # Bullish sweep: wick below, close above
                if cur["low"] < level and cur["close"] > level:
                    sig = {
                        "type":    "Sell-side Liquidity Sweep",
                        "message": f"Swept {label} ({level}) — wick below, close above. Bullish.",
                        "bias":    "long",
                        "level":   level,
                        "source":  label,
                    }
                    self._sweep_signal = sig
                    self._sweep_ttl    = self.TTL
                    return sig

            elif direction == "high":
                # Bearish sweep: wick above, close below
                if cur["high"] > level and cur["close"] < level:
                    sig = {
                        "type":    "Buy-side Liquidity Sweep",
                        "message": f"Swept {label} ({level}) — wick above, close below. Bearish.",
                        "bias":    "short",
                        "level":   level,
                        "source":  label,
                    }
                    self._sweep_signal = sig
                    self._sweep_ttl    = self.TTL
                    return sig

        return self._sweep_signal  # return remembered sweep if still in TTL

    # ── SMT detection ────────────────────────────────────────────────────────
    def detect_smt(self, nq_candles, es_candles):
        lookback = 20
        if len(nq_candles) < lookback + 1 or len(es_candles) < lookback + 1:
            return self._smt_signal

        nq_cur  = nq_candles[-1];  es_cur  = es_candles[-1]
        nq_prev = nq_candles[-lookback-1:-1]
        es_prev = es_candles[-lookback-1:-1]

        nq_swing_low  = min(c["low"]  for c in nq_prev)
        nq_swing_high = max(c["high"] for c in nq_prev)
        es_swing_low  = min(c["low"]  for c in es_prev)
        es_swing_high = max(c["high"] for c in es_prev)

        nq_broke_low  = nq_cur["low"]  < nq_swing_low
        es_broke_low  = es_cur["low"]  < es_swing_low
        nq_broke_high = nq_cur["high"] > nq_swing_high
        es_broke_high = es_cur["high"] > es_swing_high

        if nq_broke_low and not es_broke_low:
            self._smt_signal = {"type":"SMT Bullish","bias":"long","level":nq_cur["low"],
                "message":f"NQ swept low {nq_cur['low']} (swing {round(nq_swing_low,2)}) — ES held. Bullish divergence."}
            self._smt_ttl = self.TTL
        elif es_broke_low and not nq_broke_low:
            self._smt_signal = {"type":"SMT Bullish","bias":"long","level":es_cur["low"],
                "message":f"ES swept low — NQ held above {round(nq_swing_low,2)}. Bullish divergence."}
            self._smt_ttl = self.TTL
        elif nq_broke_high and not es_broke_high:
            self._smt_signal = {"type":"SMT Bearish","bias":"short","level":nq_cur["high"],
                "message":f"NQ swept high {nq_cur['high']} — ES held. Bearish divergence."}
            self._smt_ttl = self.TTL
        elif es_broke_high and not nq_broke_high:
            self._smt_signal = {"type":"SMT Bearish","bias":"short","level":es_cur["high"],
                "message":f"ES swept high — NQ held. Bearish divergence."}
            self._smt_ttl = self.TTL

        return self._smt_signal

    # ── FVG detection ────────────────────────────────────────────────────────
    def detect_fvg(self, candles):
        if len(candles) < 4:
            return self._fvg_signal

        cur = candles[-1]

        if self._fvg_signal:
            fz_low  = self._fvg_signal["fvg_low"]
            fz_high = self._fvg_signal["fvg_high"]
            bias    = self._fvg_signal["bias"]
            if bias == "long" and cur["close"] < fz_low - 10:
                self._fvg_signal = None; self._fvg_ttl = 0
            elif bias == "short" and cur["close"] > fz_high + 10:
                self._fvg_signal = None; self._fvg_ttl = 0
            else:
                touching = (cur["low"] <= fz_high and cur["close"] >= fz_low - 5
                            if bias == "long" else
                            cur["high"] >= fz_low and cur["close"] <= fz_high + 5)
                self._fvg_signal["message"] = (
                    f"Price touching {'bullish' if bias=='long' else 'bearish'} FVG {fz_low}–{fz_high}. Entry zone."
                    if touching else
                    f"{'Bullish' if bias=='long' else 'Bearish'} FVG at {fz_low}–{fz_high}. Waiting for pullback.")
                self._fvg_signal["touching"] = touching
                self._fvg_ttl = self.TTL
                return self._fvg_signal

        scan_start = max(0, len(candles) - 22)
        candidates = []
        for i in range(scan_start, len(candles) - 2):
            c1 = candles[i]; c3 = candles[i + 2]
            if c1["high"] < c3["low"]:
                candidates.append({"type":"Bullish FVG","bias":"long",
                    "fvg_low":c1["high"],"fvg_high":c3["low"],"idx":i})
            if c1["low"] > c3["high"]:
                candidates.append({"type":"Bearish FVG","bias":"short",
                    "fvg_low":c3["high"],"fvg_high":c1["low"],"idx":i})

        if not candidates:
            return None

        latest  = max(candidates, key=lambda x: x["idx"])
        fz_low  = latest["fvg_low"]; fz_high = latest["fvg_high"]; bias = latest["bias"]
        touching = (cur["low"] <= fz_high and cur["close"] >= fz_low - 5
                    if bias == "long" else
                    cur["high"] >= fz_low and cur["close"] <= fz_high + 5)
        self._fvg_signal = {**latest,
            "message": (f"Price touching {'bullish' if bias=='long' else 'bearish'} FVG {fz_low}–{fz_high}. Entry zone."
                        if touching else
                        f"{'Bullish' if bias=='long' else 'Bearish'} FVG at {fz_low}–{fz_high}. Waiting for pullback."),
            "touching": touching}
        self._fvg_ttl = self.TTL
        return self._fvg_signal

    # ── BOS detection ────────────────────────────────────────────────────────
    def detect_bos(self, candles):
        lookback = 10
        if len(candles) < lookback + 1:
            return self._bos_signal

        current    = candles[-1]
        prev       = candles[-lookback-1:-1]
        swing_high = max(c["high"] for c in prev)
        swing_low  = min(c["low"]  for c in prev)

        if current["close"] > swing_high:
            self._bos_signal = {"type":"Bullish BOS","bias":"long","level":swing_high,
                "message":f"1m close {current['close']} broke swing high {round(swing_high,2)}"}
            self._bos_ttl = self.TTL
        elif current["close"] < swing_low:
            self._bos_signal = {"type":"Bearish BOS","bias":"short","level":swing_low,
                "message":f"1m close {current['close']} broke swing low {round(swing_low,2)}"}
            self._bos_ttl = self.TTL

        return self._bos_signal

    # ── Master analysis ──────────────────────────────────────────────────────
    def analyze(self, nq_candles, es_candles):
        self._tick_ttl()
        signals         = []
        ict_window      = self.in_ict_window()
        current_session = self.session_engine.get_session_name()

        sweep = self.detect_sweep(nq_candles, es_candles)
        if sweep:
            signals.append({**sweep,
                "active_ict_window": ict_window,
                "current_session":   current_session})

        for sig in [
            self.detect_smt(nq_candles, es_candles),
            self.detect_fvg(nq_candles),
            self.detect_bos(nq_candles),
        ]:
            if sig:
                signals.append({**sig,
                    "active_ict_window": ict_window,
                    "current_session":   current_session})

        confluence = self.build_confluence_signal(signals)
        if confluence:
            signals.insert(0, confluence)

        return signals

    def build_confluence_signal(self, signals):
        has_sweep = any("Sweep" in s["type"] for s in signals)
        has_smt   = any("SMT"   in s["type"] for s in signals)
        has_fvg   = any("FVG"   in s["type"] for s in signals)
        has_bos   = any("BOS"   in s["type"] for s in signals)

        if not (has_sweep and has_smt and has_fvg and has_bos):
            return None

        long_count  = sum(1 for s in signals if s.get("bias") == "long")
        short_count = sum(1 for s in signals if s.get("bias") == "short")

        return {
            "type":              "MASTER ICT SETUP",
            "message":           "Sweep + SMT + FVG + BOS confluence detected.",
            "bias":              "long" if long_count > short_count else "short",
            "active_ict_window": self.in_ict_window(),
            "current_session":   self.session_engine.get_session_name(),
        }
