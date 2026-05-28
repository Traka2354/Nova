"""Upravljanje otvorenim pozicijama: break-even + trailing stop.

Cilj: kad trejd ode u plus, nikad ga ne pusti da se vrati u gubitak.
  1) Break-even: cim profit dostigne be_atr_mult*ATR, SL se pomera na ulaznu cenu.
  2) Trailing: kad profit predje trail_start_mult*ATR, SL prati cenu na razdaljini
     trail_atr_mult*ATR (samo u korist pozicije - nikad nazad).

Upravlja SAMO pozicijama koje je otvorio AI (po `bot_magic`), ne kopiranim.
"""
from __future__ import annotations

import logging

from config import Config
from mt5_client import MT5Client

log = logging.getLogger("manage")


def manage(client: MT5Client, cfg: Config, atr_value: float | None) -> None:
    t = cfg.trailing
    if not t.enabled:
        return
    positions = [p for p in client.positions(cfg.symbol) if p.magic == cfg.risk.bot_magic]
    if not positions:
        return

    sym = client.symbol_info(cfg.symbol)
    digits = int(getattr(sym, "digits", 2) or 2)
    eps = (10 ** -digits) / 2
    tick = client.tick(cfg.symbol)

    for p in positions:
        ref = atr_value if atr_value else p.price_open * t.fallback_pct
        be_trigger = ref * t.be_atr_mult
        trail_start = ref * t.trail_start_mult
        trail_gap = ref * t.trail_atr_mult

        if p.side == "buy":
            price = tick.bid  # vrednost po kojoj bi se zatvorila buy pozicija
            profit_dist = price - p.price_open
            if profit_dist < be_trigger:
                continue
            candidate = p.price_open  # break-even pod
            if profit_dist >= trail_start:
                candidate = max(candidate, price - trail_gap)
            candidate = round(candidate, digits)
            if candidate > (p.sl or 0) + eps:  # pomeraj samo navise
                _apply(client, p, candidate)
        else:
            price = tick.ask
            profit_dist = p.price_open - price
            if profit_dist < be_trigger:
                continue
            candidate = p.price_open
            if profit_dist >= trail_start:
                candidate = min(candidate, price + trail_gap)
            candidate = round(candidate, digits)
            if p.sl == 0 or candidate < p.sl - eps:  # pomeraj samo nanize
                _apply(client, p, candidate)


def _apply(client: MT5Client, pos, new_sl: float) -> None:
    try:
        client.modify_sl_tp(pos, new_sl, pos.tp)
        log.info("SL pomeren na %.2f za poziciju #%s (%s)", new_sl, pos.ticket, pos.side)
    except Exception as e:  # noqa: BLE001 - broker moze odbiti (min razdaljina)
        log.warning("Ne mogu da pomerim SL za #%s: %s", pos.ticket, e)
