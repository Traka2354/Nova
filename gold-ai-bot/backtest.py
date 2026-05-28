"""Jednostavan backtest skelet.

Ucitava istorijske cene zlata iz MT5 i provlaci ih kroz tehnicki sloj da bi se
testirala logika pre realnog novca. AI analiticar koristi web/aktuelne podatke,
pa se u backtestu testira deterministicki deo (indikatori + risk model).
Prosiri `decide()` svojim pravilima da bi merio rezultate kroz proslost.
"""
from __future__ import annotations

import logging

import config
import risk
from mt5_client import MT5Client

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("backtest")


def decide(closes: list[float]) -> str:
    """Primer deterministicke strategije: presek SMA20/SMA50. Vrati buy/sell/hold."""
    s20 = risk.sma(closes, 20)
    s50 = risk.sma(closes, 50)
    if s20 is None or s50 is None:
        return "hold"
    if s20 > s50:
        return "buy"
    if s20 < s50:
        return "sell"
    return "hold"


def run(symbol: str, timeframe: str = "M15", bars: int = 5000) -> None:
    client = MT5Client()
    cfg = config.load()
    client.connect(cfg.account.login, cfg.account.password, cfg.account.server, cfg.account.path)

    closes = client.recent_closes(symbol, timeframe, bars)
    if len(closes) < 60:
        log.error("Premalo podataka za backtest (%s sveca).", len(closes))
        return

    balance = 10_000.0
    position: tuple[str, float] | None = None  # (side, entry)
    wins = losses = trades = 0

    for i in range(60, len(closes)):
        window = closes[: i + 1]
        price = window[-1]
        signal = decide(window)

        if position is None and signal in ("buy", "sell"):
            position = (signal, price)
            trades += 1
        elif position is not None:
            side, entry = position
            move = (price - entry) if side == "buy" else (entry - price)
            # zatvori na suprotan signal (pojednostavljeno)
            if (side == "buy" and signal == "sell") or (side == "sell" and signal == "buy"):
                pnl = move
                balance += pnl
                wins += 1 if pnl > 0 else 0
                losses += 1 if pnl <= 0 else 0
                position = None

    log.info("Trejdova: %s | Pobeda: %s | Gubitaka: %s", trades, wins, losses)
    log.info("Zavrsni (uproscen) balans pomeraj: %.2f", balance - 10_000.0)
    client.shutdown()


if __name__ == "__main__":
    cfg = config.load()
    run(cfg.symbol)
