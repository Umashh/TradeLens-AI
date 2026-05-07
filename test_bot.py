"""
TradeLens AI — Signal Test
Run from files-3 directory:
  /Users/umashankar/Downloads/files-3/.venv/bin/python test_bot.py
"""
import sys
sys.path.insert(0, "/Users/umashankar/Downloads/files-3")

from app.services.data_feed import LiveFuturesFeed
from app.services.signal_engine import SignalEngine

print("\n" + "="*60)
print("  TradeLens AI — Signal Engine Test")
print("="*60)

print("\nLoading real NQ + ES data...")
feed = LiveFuturesFeed()
print(f"  NQ candles loaded : {len(feed.nq_history)}")
print(f"  NQ current price  : {feed.nq_history[-1]['close']}")
print(f"  ES current price  : {feed.es_history[-1]['close']}")

engine = SignalEngine()
signals = engine.analyze(feed.nq_history, feed.es_history)

print(f"\n  ICT window active : {engine.in_ict_window()}")
print(f"\nSignals detected ({len(signals)} total):")

if not signals:
    print("  None right now — market may be consolidating")
else:
    for s in signals:
        marker = "★" if s["type"] == "MASTER ICT SETUP" else "•"
        print(f"  {marker} {s['type']}")
        print(f"    bias    : {s.get('bias', 'N/A')}")
        print(f"    message : {s.get('message', '')}")
        print()

# Show individual component status
print("Component check (last candle):")
smt = engine.detect_smt(feed.nq_history, feed.es_history)
fvg = engine.detect_fvg(feed.nq_history)
bos = engine.detect_bos(feed.nq_history)
print(f"  SMT   : {'✓ ' + smt['type'] if smt else '✗ not detected'}")
print(f"  FVG   : {'✓ ' + fvg['type'] if fvg else '✗ not detected'}")
print(f"  BOS   : {'✓ ' + bos['type'] if bos else '✗ not detected'}")

sweeps = []
for sess in ["asia", "london", "new_york"]:
    sw = engine.detect_sweep(feed.nq_history, sess)
    if sw:
        sweeps.append(sw)
print(f"  Sweep : {'✓ ' + sweeps[0]['type'] if sweeps else '✗ not detected'}")

print("\n" + "="*60 + "\n")
