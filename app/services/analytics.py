import pandas as pd
from pathlib import Path

COLUMNS = ["date", "symbol", "side", "entry", "exit", "qty", "pnl", "setup", "result", "exit_time"]

class TradeAnalytics:
    def __init__(self):
        self.trade_file = Path("data/trades.csv")
        self.trade_file.parent.mkdir(exist_ok=True)

    def load(self):
        if not self.trade_file.exists():
            return pd.DataFrame(columns=COLUMNS)
        try:
            df = pd.read_csv(self.trade_file, names=COLUMNS, header=0, on_bad_lines="skip")
            df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce").fillna(0)
            return df
        except Exception as e:
            print(f"[analytics] CSV read error: {e} — resetting")
            self.trade_file.unlink(missing_ok=True)
            return pd.DataFrame(columns=COLUMNS)

    def summary(self):
        df = self.load()
        total_trades = int(len(df))
        if total_trades == 0:
            return {"total_trades": 0, "win_rate": 0.0, "total_pnl": 0.0,
                    "avg_win": 0.0, "avg_loss": 0.0, "best_setup": "--"}

        wins   = df[df["pnl"] > 0]
        losses = df[df["pnl"] <= 0]

        try:
            best_setup = str(df.groupby("setup")["pnl"].sum().sort_values(ascending=False).index[0])
        except Exception:
            best_setup = "--"

        return {
            "total_trades": total_trades,
            "win_rate":     round(float(len(wins) / total_trades * 100), 2),
            "total_pnl":    round(float(df["pnl"].sum()), 2),
            "avg_win":      round(float(wins["pnl"].mean()), 2) if len(wins) else 0.0,
            "avg_loss":     round(float(losses["pnl"].mean()), 2) if len(losses) else 0.0,
            "best_setup":   best_setup,
        }
