import csv
from datetime import datetime
from pathlib import Path


class BotEngine:
    def __init__(self):
        self.mode = "PAPER"
        self.enabled = True
        self.open_trade = None
        self.closed_trades = []
        self.last_action = "Waiting for setup"
        self.current_bias = "neutral"

        self.stop_points  = 30
        self.target_points = 60
        self.point_value  = 20

        self.trade_file = Path("data/trades.csv")
        self.trade_file.parent.mkdir(exist_ok=True)

    def process(self, snapshot, signals):
        nq    = snapshot["nq"]
        price = nq["close"]

        self.manage_open_trade(price)

        if self.enabled and self.open_trade is None:
            master = self.get_master_signal(signals)
            if master:
                self.enter_trade(price, master)

        return self.status()

    def get_master_signal(self, signals):
        for s in signals:
            if s["type"] == "MASTER ICT SETUP":
                return s
        return None

    def enter_trade(self, price, signal):
        bias = signal["bias"]
        self.current_bias = bias

        sl = price - self.stop_points  if bias == "long" else price + self.stop_points
        tp = price + self.target_points if bias == "long" else price - self.target_points

        self.open_trade = {
            "side":       bias,
            "entry":      price,
            "stop_loss":  round(sl, 2),
            "take_profit": round(tp, 2),
            "status":     "OPEN",
            "setup":      signal["type"],
            "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        self.last_action = (
            f"Paper {bias.upper()} entered at {price}. "
            f"SL: {round(sl,2)} TP: {round(tp,2)}"
        )

    def manage_open_trade(self, price):
        if not self.open_trade:
            return
        t    = self.open_trade
        side = t["side"]

        if side == "long":
            if price <= t["stop_loss"]:   self.close_trade(price, "LOSS")
            elif price >= t["take_profit"]: self.close_trade(price, "WIN")
        else:
            if price >= t["stop_loss"]:   self.close_trade(price, "LOSS")
            elif price <= t["take_profit"]: self.close_trade(price, "WIN")

    def close_trade(self, price, result):
        t    = self.open_trade
        side = t["side"]
        pts  = price - t["entry"] if side == "long" else t["entry"] - price
        pnl  = round(pts * self.point_value, 2)

        closed = {**t, "exit": price, "result": result, "pnl": pnl,
                  "exit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        self.closed_trades.append(closed)
        self.open_trade = None
        self.last_action = f"Paper trade closed: {result}. PnL: ${pnl}"
        self._log_trade(closed)

    def _log_trade(self, trade):
        """Append closed trade to trades.csv"""
        try:
            file_exists = self.trade_file.exists()
            with open(self.trade_file, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "date", "symbol", "side", "entry", "exit",
                    "qty", "pnl", "setup", "result", "exit_time"
                ])
                if not file_exists:
                    writer.writeheader()
                writer.writerow({
                    "date":      trade.get("entry_time", "")[:10],
                    "symbol":    "NQ",
                    "side":      trade["side"],
                    "entry":     trade["entry"],
                    "exit":      trade["exit"],
                    "qty":       1,
                    "pnl":       trade["pnl"],
                    "setup":     trade["setup"],
                    "result":    trade["result"],
                    "exit_time": trade.get("exit_time", ""),
                })
        except Exception as e:
            print(f"[bot_engine] log error: {e}")

    def status(self):
        total_pnl   = round(sum(t["pnl"] for t in self.closed_trades), 2)
        total_trades = len(self.closed_trades)
        wins        = len([t for t in self.closed_trades if t["result"] == "WIN"])
        win_rate    = round((wins / total_trades) * 100, 2) if total_trades else 0

        return {
            "mode":          self.mode,
            "enabled":       self.enabled,
            "status":        "Running" if self.enabled else "Paused",
            "current_bias":  self.current_bias,
            "last_action":   self.last_action,
            "open_trade":    self.open_trade,
            "closed_trades": self.closed_trades[-5:],
            "total_pnl":     total_pnl,
            "total_trades":  total_trades,
            "win_rate":      win_rate,
        }
