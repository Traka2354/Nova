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


@dataclass
class TradePlan:
    volume: float
    sl_price: float
    tp_price: float
    sl_money: float      # stvarni rizik nakon zaokruzivanja lota
    tp_money: float      # ciljani profit


def money_targets(balance: float, params: RiskParams, confidence: float) -> Targets:
    """Bira TP/SL novcani cilj unutar opsega, srazmerno sigurnosti signala."""
    c = max(0.0, min(1.0, confidence))
    tp_pct = params.tp_min_pct + (params.tp_max_pct - params.tp_min_pct) * c
    sl_pct = params.sl_min_pct + (params.sl_max_pct - params.sl_min_pct) * c
    return Targets(sl_money=balance * sl_pct, tp_money=balance * tp_pct)


def money_per_price_per_lot(symbol_info) -> float:
    """Novac (account currency) po pomeraju cene od 1.0, po JEDNOM lotu."""
    tick_value = float(getattr(symbol_info, "trade_tick_value", 0) or 0)
    tick_size = float(getattr(symbol_info, "trade_tick_size", 0) or 0)
    if tick_value > 0 and tick_size > 0:
        return tick_value / tick_size
    # fallback: standardni ugovor za zlato je 100 unci po lotu
    return float(getattr(symbol_info, "trade_contract_size", 100) or 100)


def normalize_volume(symbol_info, volume: float, max_lot: float) -> float:
    """Zaokruzi lot na korak brokera i ogranici na min/max (broker + nas cap)."""
    vmin = float(getattr(symbol_info, "volume_min", 0.01) or 0.01)
    vmax = float(getattr(symbol_info, "volume_max", 100.0) or 100.0)
    vstep = float(getattr(symbol_info, "volume_step", 0.01) or 0.01)
    vmax = min(vmax, max_lot) if max_lot > 0 else vmax
    if volume < vmin:
        return vmin
    if volume > vmax:
        return vmax
    steps = round((volume - vmin) / vstep)
    return round(vmin + steps * vstep, 8)


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float | None:
    """Average True Range - mera volatilnosti za smislenu razdaljinu SL-a."""
    n = min(len(highs), len(lows), len(closes))
    if n < period + 1:
        return None
    trs: list[float] = []
    for i in range(n - period, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    return sum(trs) / len(trs)


def plan_trade(
    symbol_info,
    side: str,
    entry: float,
    balance: float,
    params: RiskParams,
    confidence: float,
    sl_distance: float,
) -> TradePlan:
    """Auto-skaliranje: lot se racuna tako da SL gubi tacno SL% balansa.

    SL razdaljina (`sl_distance`, u cenovnim jedinicama, npr. iz ATR-a) odredjuje
    GDE je stop; lot odredjuje KOLIKO se rizikuje. TP razdaljina se izvuce iz
    TP novcanog cilja i tog lota, tako da i TP donese TP% balansa.
    """
    targets = money_targets(balance, params, confidence)
    per_lot = money_per_price_per_lot(symbol_info)
    digits = int(getattr(symbol_info, "digits", 2) or 2)

    if params.auto_lot and per_lot > 0 and sl_distance > 0:
        raw = targets.sl_money / (per_lot * sl_distance)
        volume = normalize_volume(symbol_info, raw, params.max_lot)
    else:
        volume = normalize_volume(symbol_info, params.lot_size, params.max_lot)

    money_per_price = per_lot * volume
    sl_money = money_per_price * sl_distance if money_per_price > 0 else targets.sl_money
    tp_distance = targets.tp_money / money_per_price if money_per_price > 0 else sl_distance * 2

    if side == "buy":
        sl_price = round(entry - sl_distance, digits)
        tp_price = round(entry + tp_distance, digits)
    else:
        sl_price = round(entry + sl_distance, digits)
        tp_price = round(entry - tp_distance, digits)

    return TradePlan(
        volume=volume,
        sl_price=sl_price,
        tp_price=tp_price,
        sl_money=sl_money,
        tp_money=targets.tp_money,
    )


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
