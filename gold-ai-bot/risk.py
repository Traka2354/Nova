"""Risk management: TP/SL kao procenat balansa + jednostavni indikatori.

TP i SL se zadaju kao novcani cilj (procenat od UKUPNOG balansa naloga).
Iz tog cilja, fiksne velicine pozicije i specifikacije simbola racunamo
konkretne cene SL/TP koje ce dati taj profit/gubitak.
"""
from __future__ import annotations

from dataclasses import dataclass

from config import RiskParams


@dataclass
class Targets:
    sl_money: float
    tp_money: float


def money_targets(balance: float, params: RiskParams, confidence: float) -> Targets:
    """Bira TP/SL novcani cilj unutar opsega, srazmerno sigurnosti signala."""
    c = max(0.0, min(1.0, confidence))
    tp_pct = params.tp_min_pct + (params.tp_max_pct - params.tp_min_pct) * c
    sl_pct = params.sl_min_pct + (params.sl_max_pct - params.sl_min_pct) * c
    return Targets(sl_money=balance * sl_pct, tp_money=balance * tp_pct)


def _money_per_price_unit(symbol_info, volume: float) -> float:
    """Koliko novca (account currency) donosi pomeraj cene od 1.0 za dati lot."""
    tick_value = float(getattr(symbol_info, "trade_tick_value", 0) or 0)
    tick_size = float(getattr(symbol_info, "trade_tick_size", 0) or 0)
    if tick_value <= 0 or tick_size <= 0:
        # fallback: standardni ugovor za zlato je 100 unci po lotu
        contract = float(getattr(symbol_info, "trade_contract_size", 100) or 100)
        return contract * volume
    return (tick_value / tick_size) * volume


def sl_tp_prices(
    symbol_info,
    side: str,
    entry: float,
    volume: float,
    targets: Targets,
) -> tuple[float, float]:
    """Vraca (sl_price, tp_price) za zadate novcane ciljeve."""
    per_unit = _money_per_price_unit(symbol_info, volume)
    if per_unit <= 0:
        return 0.0, 0.0
    sl_dist = targets.sl_money / per_unit
    tp_dist = targets.tp_money / per_unit
    digits = int(getattr(symbol_info, "digits", 2) or 2)
    if side == "buy":
        sl = round(entry - sl_dist, digits)
        tp = round(entry + tp_dist, digits)
    else:
        sl = round(entry + sl_dist, digits)
        tp = round(entry - tp_dist, digits)
    return sl, tp


# ---- jednostavni indikatori (kontekst za AI) ----

def sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) < period + 1:
        return None
    gains, losses = 0.0, 0.0
    for i in range(-period, 0):
        diff = values[i] - values[i - 1]
        if diff >= 0:
            gains += diff
        else:
            losses -= diff
    if losses == 0:
        return 100.0
    rs = (gains / period) / (losses / period)
    return 100 - (100 / (1 + rs))


def technical_summary(closes: list[float]) -> dict:
    """Sazima cenovni kontekst u nekoliko brojeva za AI analitičara."""
    return {
        "last_close": closes[-1] if closes else None,
        "sma20": sma(closes, 20),
        "sma50": sma(closes, 50),
        "rsi14": rsi(closes, 14),
        "n_candles": len(closes),
    }
