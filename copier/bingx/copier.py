"""
SonicCopyX — MT5 → BingX Trade Copier
Pokretanje: python copier.py
"""

import time
import sys
import logging

import config
import mt5_reader
from bingx_api import BingXClient

# ── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    handlers=[
        logging.FileHandler("copier.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("Copier")


def qty_from_lots(mt5_symbol: str, lots: float) -> float:
    """Pretvori MT5 lotove u BingX contracts."""
    ratio = config.LOT_TO_QTY.get(mt5_symbol, 1.0)
    return round(abs(lots) * ratio, 4)


def sync_symbol(bingx: BingXClient, mt5_symbol: str, bingx_symbol: str):
    """
    Sinkronizira jednu poziciju: MT5 symbol → BingX symbol.

    Logika:
      MT5 net > 0  →  BingX treba biti LONG iste veličine
      MT5 net < 0  →  BingX treba biti SHORT iste veličine
      MT5 net = 0  →  BingX treba biti zatvoren
    """
    mt5_net  = mt5_reader.get_net_lots(mt5_symbol)          # u lotovima
    bingx_qty = bingx.get_position_qty(bingx_symbol)         # u contracts (+LONG, -SHORT)

    target_qty  = qty_from_lots(mt5_symbol, mt5_net)         # koliko contracts trebamo
    target_side = "LONG" if mt5_net > 0 else ("SHORT" if mt5_net < 0 else "FLAT")

    bingx_side  = "LONG" if bingx_qty > 0 else ("SHORT" if bingx_qty < 0 else "FLAT")

    log.debug(
        f"{mt5_symbol}: MT5={mt5_net:+.2f}lots → target={target_side} {target_qty}  |  "
        f"BingX={bingx_side} {abs(bingx_qty):.4f}"
    )

    # ── Nema pozicije ni na jednoj strani ────────────────────────
    if target_side == "FLAT" and bingx_side == "FLAT":
        return

    # ── MT5 zatvorio poziciju → zatvori na BingX ─────────────────
    if target_side == "FLAT" and bingx_side != "FLAT":
        log.info(f"MT5 zatvorio {mt5_symbol} → zatvaramo BingX {bingx_symbol}")
        bingx.close_position(bingx_symbol)
        return

    # ── Smjer se promijenio → zatvori staru i otvori novu ────────
    if bingx_side != "FLAT" and bingx_side != target_side:
        log.info(f"Smjer promijenjen ({bingx_side}→{target_side}) — zatvaramo staru poziciju")
        bingx.close_position(bingx_symbol)
        time.sleep(0.3)
        bingx_qty = 0.0
        bingx_side = "FLAT"

    # ── Otvori novu poziciju ──────────────────────────────────────
    if bingx_side == "FLAT" and target_side != "FLAT":
        if target_qty < config.MIN_QTY_GOLD:
            log.warning(f"Količina {target_qty} ispod minimuma {config.MIN_QTY_GOLD} — preskačemo")
            return
        order_side = "BUY" if target_side == "LONG" else "SELL"
        log.info(f"Otvaram BingX {order_side} {target_qty} {bingx_symbol} (MT5: {mt5_net:+.2f} lots)")
        bingx.market_order(bingx_symbol, order_side, target_qty)
        return

    # ── Podesi veličinu ako se promijenila (dodaj ili smanji) ─────
    diff = round(target_qty - abs(bingx_qty), 4)
    if abs(diff) < config.MIN_QTY_GOLD:
        return   # Razlika premala — ne diraj

    if diff > 0:
        # Dodaj više
        order_side = "BUY" if target_side == "LONG" else "SELL"
        log.info(f"Povećavam BingX poziciju: {order_side} +{diff} {bingx_symbol}")
        bingx.market_order(bingx_symbol, order_side, diff)
    else:
        # Smanji (djelimično zatvori)
        order_side = "SELL" if target_side == "LONG" else "BUY"
        log.info(f"Smanjujem BingX poziciju: {order_side} {abs(diff)} {bingx_symbol}")
        bingx.market_order(bingx_symbol, order_side, abs(diff))


def run():
    log.info("=" * 60)
    log.info("  SonicCopyX — MT5 → BingX Copier")
    log.info("  Zaustavi sa: Ctrl+C")
    log.info("=" * 60)

    # ── Spoji se na MT5 ───────────────────────────────────────────
    log.info("Spajam na MT5...")
    if not mt5_reader.connect(config.MT5_LOGIN, config.MT5_PASSWORD, config.MT5_SERVER):
        log.error("Ne mogu se spojiti na MT5. Provjeri config.py.")
        sys.exit(1)

    # ── Spoji se na BingX ─────────────────────────────────────────
    log.info("Spajam na BingX...")
    bingx = BingXClient(config.BINGX_API_KEY, config.BINGX_SECRET_KEY)
    if not bingx.test_connection():
        log.error("Ne mogu se spojiti na BingX. Provjeri API ključeve u config.py.")
        mt5_reader.disconnect()
        sys.exit(1)

    log.info("Obje platforme spojene. Počinjem kopirati...\n")

    reconnect_counter = 0

    while True:
        try:
            # Provjeri MT5 konekciju svakih ~60s
            reconnect_counter += 1
            if reconnect_counter % int(60 / config.POLL_INTERVAL_SEC) == 0:
                if not mt5_reader.is_connected():
                    log.warning("MT5 izgubio konekciju — pokušavam reconnect...")
                    mt5_reader.connect(config.MT5_LOGIN, config.MT5_PASSWORD, config.MT5_SERVER)

            # Sinhroniziraj svaki simbol
            for mt5_sym, bingx_sym in config.SYMBOL_MAP.items():
                sync_symbol(bingx, mt5_sym, bingx_sym)

            time.sleep(config.POLL_INTERVAL_SEC)

        except KeyboardInterrupt:
            log.info("\nCopier zaustavljen.")
            break
        except Exception as e:
            log.error(f"Greška u glavnom loopu: {e}", exc_info=True)
            time.sleep(2)

    mt5_reader.disconnect()
    log.info("Sve konekcije zatvorene.")


if __name__ == "__main__":
    run()
