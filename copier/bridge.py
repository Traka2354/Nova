"""
SonicCopyX Bridge — MT5 -> MT4 trade copier
Pokretanje: python bridge.py
Zahtijeva: pip install MetaTrader5
"""

import time
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    handlers=[
        logging.FileHandler("bridge.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("SonicBridge")

# ── Config (mijenjaj samo ovdje) ───────────────────────────────────────────
MT5_LOGIN    = 0          # Tvoj MT5 account broj (0 = koristi već prijavljen terminal)
MT5_PASSWORD = ""         # Lozinka (ostavi prazno ako je terminal već prijavljen)
MT5_SERVER   = ""         # Broker server (ostavi prazno ako je terminal već prijavljen)

LOT_MULTIPLIER   = 1.0   # 1.0 = isti lot; 0.5 = pola lota na slaveu
COPY_ALL_SYMBOLS = True   # True = svi parovi
ALLOWED_SYMBOLS  = ["XAUUSD", "EURUSD", "GBPUSD"]  # Koristi se kad je COPY_ALL_SYMBOLS=False

POLL_INTERVAL = 0.5       # Sekunde između provjera MT5 pozicija
HEARTBEAT_INTERVAL = 3    # Sekunde između heartbeat upisa

# Signal fajl — isti putanja kao MetaTrader Common folder na Windows VPS
# Automatski se pronalazi; ako ne pronađe, koristi lokalni folder
SIGNAL_FILE_NAME = "SonicCopyX_signal.csv"

# ── Pronađi MetaTrader Common folder ───────────────────────────────────────
def find_signal_path():
    appdata = os.environ.get("APPDATA", "")
    common  = Path(appdata) / "MetaQuotes" / "Terminal" / "Common" / "Files"
    if common.exists():
        return str(common / SIGNAL_FILE_NAME)
    # Fallback: isti folder kao skripta
    return SIGNAL_FILE_NAME

SIGNAL_FILE = find_signal_path()
log.info(f"Signal fajl: {SIGNAL_FILE}")

# ── MT5 konekcija ──────────────────────────────────────────────────────────
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    log.warning("MetaTrader5 Python paket nije instaliran. Pokreni: pip install MetaTrader5")

def connect_mt5():
    if not MT5_AVAILABLE:
        return False
    if not mt5.initialize():
        log.error(f"MT5 initialize() greška: {mt5.last_error()}")
        return False
    if MT5_LOGIN and MT5_PASSWORD and MT5_SERVER:
        ok = mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
        if not ok:
            log.error(f"MT5 login greška: {mt5.last_error()}")
            return False
    info = mt5.account_info()
    if info is None:
        log.error("MT5: ne mogu dohvatiti account info")
        return False
    log.info(f"MT5 spojen — Account #{info.login} | Balance: {info.balance} {info.currency}")
    return True

# ── Čitanje pozicija ───────────────────────────────────────────────────────
def get_positions_mt5():
    """Čita otvorene pozicije via Python MT5 API."""
    positions = mt5.positions_get()
    if positions is None:
        return []
    result = []
    for p in positions:
        sym = p.symbol
        if not COPY_ALL_SYMBOLS and sym not in ALLOWED_SYMBOLS:
            continue
        result.append({
            "ticket":     p.ticket,
            "symbol":     sym,
            "type":       p.type,       # 0=BUY, 1=SELL
            "lots":       round(p.volume * LOT_MULTIPLIER, 2),
            "open_price": p.price_open,
            "sl":         p.sl,
            "tp":         p.tp,
            "magic":      p.magic,
            "open_time":  int(p.time),
        })
    return result

# ── Equity monitor fallback ────────────────────────────────────────────────
class EquityMonitor:
    """
    Kada MT5 API ne može čitati pozicije (broker blokada),
    prati equity promjene da detektira otvaranje/zatvaranje trejdova.
    Ograničenje: ne zna simbol/smjer automatski — zahtijeva konfiguraciju.
    """
    def __init__(self):
        self.prev_equity  = None
        self.prev_balance = None
        self.open_trades  = {}  # ticket -> pseudo pozicija

    def check(self):
        info = mt5.account_info()
        if info is None:
            return []

        equity  = info.equity
        balance = info.balance

        if self.prev_equity is None:
            self.prev_equity  = equity
            self.prev_balance = balance
            return list(self.open_trades.values())

        delta = equity - self.prev_equity
        self.prev_equity  = equity
        self.prev_balance = balance

        if abs(delta) > 0.50:  # Promjena veća od 50 centi
            direction = "PROMJENA EQUITY" + (f" +{delta:.2f}" if delta > 0 else f" {delta:.2f}")
            log.info(f"Equity monitor: {direction} | Equity={equity} Balance={balance}")

        return list(self.open_trades.values())

equity_monitor = EquityMonitor()

# ── Pisanje signal fajla ───────────────────────────────────────────────────
prev_content = ""

def write_signal_file(positions):
    global prev_content

    lines = [f"HEARTBEAT={int(time.time())}"]
    for p in positions:
        lines.append(
            f"{p['ticket']}|{p['symbol']}|{p['type']}|{p['lots']:.2f}|"
            f"{p['open_price']:.5f}|{p['sl']:.5f}|{p['tp']:.5f}|"
            f"{p['magic']}|{p['open_time']}"
        )

    content = "\n".join(lines) + "\n"
    if content == prev_content:
        return  # Nema promjena — ne pisati

    try:
        os.makedirs(os.path.dirname(os.path.abspath(SIGNAL_FILE)), exist_ok=True)
        with open(SIGNAL_FILE, "w", encoding="ascii") as f:
            f.write(content)
        prev_content = content
    except Exception as e:
        log.error(f"Greška pri pisanju fajla: {e}")

# ── Status ispis ───────────────────────────────────────────────────────────
last_log_time   = 0
last_pos_count  = -1

def log_status(positions, mode):
    global last_log_time, last_pos_count
    now = time.time()
    count = len(positions)
    if now - last_log_time > 30 or count != last_pos_count:
        log.info(f"[{mode}] Aktivnih pozicija na masteru: {count}")
        for p in positions:
            ptype = "BUY" if p["type"] == 0 else "SELL"
            log.info(f"  #{p['ticket']} {ptype} {p['lots']} {p['symbol']} @ {p['open_price']:.5f}")
        last_log_time  = now
        last_pos_count = count

# ── Glavni loop ────────────────────────────────────────────────────────────
def run():
    log.info("=" * 55)
    log.info("  SonicCopyX Bridge — pokrenut")
    log.info("  Zaustavi sa: Ctrl+C")
    log.info("=" * 55)

    mt5_connected = connect_mt5()
    use_equity_fallback = not mt5_connected

    if not mt5_connected:
        log.warning("MT5 nije spojen — koristim equity monitor fallback")
        if MT5_AVAILABLE:
            mt5.initialize()  # Pokušaj inicijalizirati bez logina

    reconnect_attempts = 0

    while True:
        try:
            # Čitanje pozicija
            if MT5_AVAILABLE and mt5_connected:
                positions = get_positions_mt5()

                # Ako API vrača prazno ali terminal je prijavljen, provjeri equity
                if len(positions) == 0:
                    info = mt5.account_info()
                    if info and info.margin > 0:
                        log.warning("MT5 API vidi 0 pozicija ali margin > 0 — broker vjerovatno blokira čitanje")
                        use_equity_fallback = True

                if use_equity_fallback:
                    positions = equity_monitor.check()
                    mode = "EQUITY-FALLBACK"
                else:
                    mode = "MT5-API"
            else:
                positions = []
                mode = "OFFLINE"

                # Pokušaj reconnect svake minute
                reconnect_attempts += 1
                if reconnect_attempts % 120 == 0:
                    log.info("Pokušavam reconnect na MT5...")
                    mt5_connected = connect_mt5()

            write_signal_file(positions)
            log_status(positions, mode)
            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            log.info("Bridge zaustavljen od korisnika.")
            break
        except Exception as e:
            log.error(f"Neočekivana greška: {e}", exc_info=True)
            time.sleep(2)

    # Obriši signal fajl kad se bridge zaustavi
    try:
        os.remove(SIGNAL_FILE)
        log.info("Signal fajl obrisan.")
    except Exception:
        pass

    if MT5_AVAILABLE:
        mt5.shutdown()

if __name__ == "__main__":
    run()
