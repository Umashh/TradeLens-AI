import sys
sys.path.insert(0, "/Users/umashankar/Downloads/files-3")
from app.services.signal_engine import SignalEngine
from app.services.bot_engine import BotEngine

engine = SignalEngine()
bot    = BotEngine()

def nq(t,o,h,l,c,sess="new_york"):
    return {"symbol":"NQ","time":t,"session":sess,"open":o,"high":h,"low":l,"close":c,"volume":500}
def es(t,o,h,l,c,sess="new_york"):
    return {"symbol":"ES","time":t,"session":sess,"open":o,"high":h,"low":l,"close":c,"volume":500}
def section(title):
    print(f"\n{'─'*60}\n  {title}\n{'─'*60}")

nq_candles, es_candles = [], []

print("\n" + "="*60)
print("  TradeLens AI — Today's Setup Replay")
print("="*60)

section("Phase 1: Asia session — context")
for i in range(16):
    p = 27300 + (i%5)*4
    nq_candles.append(nq(f"02:{i*3:02d}:00",p,p+8,p-8,p+2,"asia"))
    es_candles.append(es(f"02:{i*3:02d}:00",p/3.82,(p+8)/3.82,(p-8)/3.82,(p+2)/3.82,"asia"))
print(f"  {len(nq_candles)} Asia candles")

section("Phase 2: London — sell down to 27,185")
london_prices=[27280,27265,27250,27235,27220,27210,27200,27195,27190,27185,
               27195,27205,27215,27225,27235,27245]
for i,p in enumerate(london_prices):
    nq_candles.append(nq(f"05:{i*4:02d}:00",p+3,p+10,p-3,p,"london"))
    es_candles.append(es(f"05:{i*4:02d}:00",(p+3)/3.82,(p+10)/3.82,(p-3)/3.82,p/3.82,"london"))

# ── Force level computation NOW using pre-NY candles ──────────────────────
engine._compute_levels(nq_candles)
print(f"  PDH={engine._prev_day_high} PDL={engine._prev_day_low}")
print(f"  Asia H={engine._asia_high} L={engine._asia_low}")
print(f"  London H={engine._london_high} L={engine._london_low}")

section("Phase 3: NY open 09:00–10:14 — ranging")
ny_prices=[27240,27248,27252,27245,27238,27242,27250,27255,27248,27240,
           27235,27230,27225,27220,27218,27222,27228,27235,27240,27245,
           27250,27248,27242,27238,27235]
for i,p in enumerate(ny_prices):
    nq_candles.append(nq(f"09:{i:02d}:00",p,p+6,p-6,p+2))
    es_candles.append(es(f"09:{i:02d}:00",p/3.82,(p+6)/3.82,(p-6)/3.82,(p+2)/3.82))
nq_swing = min(c["low"] for c in nq_candles[-20:])
es_swing  = min(c["low"] for c in es_candles[-20:])
print(f"  NQ swing low (last 20): {nq_swing} | ES: {round(es_swing,2)}")

section("Phase 4: 10:15 AM — SWEEP + SMT")
print(f"  NQ wicks to 27,180 (below London L {engine._london_low}) closes at 27,198")
print(f"  ES holds above its swing low — SMT divergence")
nq_smt = nq("10:15:00",27230,27235,27180,27198)
es_smt = es("10:15:00",es_swing+0.5,es_swing+2,es_swing+0.3,es_swing+1.2)
nq_candles.append(nq_smt); es_candles.append(es_smt)

sweep = engine.detect_sweep(nq_candles, es_candles)
smt   = engine.detect_smt(nq_candles, es_candles)
print(f"\n  Sweep: {'✓ '+sweep['type'] if sweep else '✗ MISSED'}")
if sweep: print(f"  {sweep['message']}")
print(f"  SMT  : {'✓ '+smt['type'] if smt else '✗ MISSED'}")
if smt: print(f"  {smt['message']}")

section("Phase 5: 10:16–10:44 — consolidation")
consol=[27200,27205,27210,27215,27220,27225,27230,27235,27240,27245,
        27248,27250,27252,27248,27245,27242,27240,27238,27242,27245,
        27248,27250,27252,27254,27256]
for i,p in enumerate(consol):
    nq_candles.append(nq(f"10:{16+i:02d}:00",p,p+6,p-4,p+2))
    es_candles.append(es(f"10:{16+i:02d}:00",p/3.82,(p+6)/3.82,(p-4)/3.82,(p+2)/3.82))
swing_high_pre_bos = max(c["high"] for c in nq_candles[-10:])
print(f"  Swing high before BOS: {swing_high_pre_bos}")

section("Phase 6: 10:45 AM — BULLISH BOS")
nq_bos = nq("10:45:00",27256,27282,27252,27278)
es_bos = es("10:45:00",7138,7145,7135,7143)
nq_candles.append(nq_bos); es_candles.append(es_bos)
bos = engine.detect_bos(nq_candles)
print(f"  BOS: {'✓ '+bos['type'] if bos else '✗ MISSED'}")
if bos: print(f"  {bos['message']}")

section("Phase 7: 10:46 AM — FVG FORMS")
nq_c3 = nq("10:46:00",27280,27298,27278,27292)
es_c3 = es("10:46:00",7143,7150,7140,7147)
nq_candles.append(nq_c3); es_candles.append(es_c3)
fvg = engine.detect_fvg(nq_candles)
print(f"  FVG: {'✓ '+fvg['type'] if fvg else '✗ MISSED'}")
if fvg: print(f"  Zone: {fvg.get('fvg_low')}–{fvg.get('fvg_high')}")

section("Phase 8: 10:47–10:59 — rally then pullback")
rally=[27295,27310,27325,27338,27350,27342,27330,27318,27305,27292,27282,27275,27270]
for i,p in enumerate(rally):
    nq_candles.append(nq(f"10:{47+i:02d}:00",p,p+6,p-4,p+1))
    es_candles.append(es(f"10:{47+i:02d}:00",p/3.82,(p+6)/3.82,(p-4)/3.82,(p+1)/3.82))
print(f"  Pulled back to 27,270 — approaching FVG (27,262–27,278)")

section("Phase 9: 11:00 AM — PRICE TOUCHES FVG → MASTER SETUP")
nq_entry = nq("11:00:00",27272,27276,27263,27271)
es_entry = es("11:00:00",7140,7142,7137,7139)
nq_candles.append(nq_entry); es_candles.append(es_entry)

signals = engine.analyze(nq_candles, es_candles)
print(f"\n  Signals ({len(signals)}):")
for s in signals:
    m = "★" if s["type"]=="MASTER ICT SETUP" else "•"
    print(f"  {m} {s['type']} | {s.get('bias','').upper()}")
    print(f"    {s.get('message','')}")

section("Phase 10: Bot processes signals")
status = bot.process({"nq":nq_entry,"es":es_entry}, signals)
print(f"  Action: {status['last_action']}")
if status["open_trade"]:
    t = status["open_trade"]
    print(f"  Entry {t['entry']} | SL {t['stop_loss']} | TP {t['take_profit']}")

if bot.open_trade:
    section("Phase 11: Price hits session high 27,440 → WIN")
    tp_snap = {"nq":nq("11:28:00",27400,27445,27395,27441),"es":es_entry}
    status = bot.process(tp_snap, [])
    tr = bot.closed_trades[-1]
    pts = tr["exit"]-tr["entry"]
    print(f"  Result : {tr['result']}")
    print(f"  {tr['entry']} → {tr['exit']} | +{pts:.0f} pts | ${tr['pnl']:,.0f} | {pts/30:.1f}R")

print("\n"+"="*60)
master  = any(s["type"]=="MASTER ICT SETUP" for s in signals)
entered = len(bot.closed_trades) > 0
print(f"  Sweep detected       : {'✓' if any('Sweep' in s['type'] for s in signals) else '✗'}")
print(f"  SMT detected         : {'✓' if any('SMT'   in s['type'] for s in signals) else '✗'}")
print(f"  FVG detected         : {'✓' if any('FVG'   in s['type'] for s in signals) else '✗'}")
print(f"  BOS detected         : {'✓' if any('BOS'   in s['type'] for s in signals) else '✗'}")
print(f"  MASTER ICT SETUP     : {'✓ FIRED' if master else '✗ did not fire'}")
print(f"  Bot entered trade    : {'✓ YES' if entered else '✗ NO'}")
if entered:
    print(f"  Result               : {bot.closed_trades[-1]['result']} ${bot.closed_trades[-1]['pnl']:,.0f}")
print("="*60+"\n")
