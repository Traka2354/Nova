"""Zastitni circuit breakeri - kapital pre profita.

Blokira otvaranje novih pozicija kada:
  - je dnevni gubitak dostigao limit (MAX_DAILY_LOSS_PCT),
  - je dnevni profit cilj dostignut (poknjizi dan i stani),
  - je bilo previse uzastopnih gubitaka (pauza do kraja dana),
  - je skoro bio gubitak (cooldown, anti-revenge trading).

Trailing/break-even na vec otvorenim pozicijama radi nezavisno - guard samo
sprecava NOVE ulaske.
"""
from __future__ import annotations

import datetime as _dt
import logging

from config import Config
from mt5_client import MT5Client

log = logging.getLogger("guard")


class RiskGuard:
    def __init__(self) -> None:
        self.day: _dt.date | None = None
        self.start_balance: float | None = None

    def _reset_if_new_day(self, client: MT5Client) -> None:
        today = _dt.date.today()
        if today != self.day or self.start_balance is None:
            self.day = today
            self.start_balance = client.account_balance()
            log.info("Novi dan. Pocetni balans: %.2f", self.start_balance)

    def can_open(self, client: MT5Client, cfg: Config) -> bool:
        self._reset_if_new_day(client)
        start = self.start_balance or client.account_balance()
        equity = client.account_equity()

        change = (equity - start) / start if start else 0.0
        if change <= -cfg.risk.max_daily_loss_pct:
            log.warning("Dnevni limit gubitka (%.1f%%) dostignut. Pauza.", change * 100)
            return False
        if cfg.guards.daily_profit_pct > 0 and change >= cfg.guards.daily_profit_pct:
            log.info("Dnevni profit cilj (%.1f%%) dostignut. Knjizim dan i stajem.", change * 100)
            return False

        # realizovani zatvoreni trejdovi danas (za uzastopne gubitke / cooldown)
        midnight = _dt.datetime.combine(_dt.date.today(), _dt.time.min)
        try:
            deals = client.closed_deals(cfg.risk.bot_magic, cfg.symbol, midnight)
        except Exception as e:  # noqa: BLE001 - istorija je opciona za odluku
            log.warning("Ne mogu da procitam istoriju trejdova: %s", e)
            deals = []

        consec = 0
        for _, profit in reversed(deals):
            if profit < 0:
                consec += 1
            else:
                break
        if cfg.guards.max_consec_losses > 0 and consec >= cfg.guards.max_consec_losses:
            log.warning("%s uzastopnih gubitaka. Pauza do kraja dana.", consec)
            return False

        if deals and cfg.guards.cooldown_min > 0:
            last_time, last_profit = deals[-1]
            if last_profit < 0:
                mins = (_dt.datetime.now() - last_time).total_seconds() / 60
                if mins < cfg.guards.cooldown_min:
                    log.info("Cooldown posle gubitka: jos %.0f min.", cfg.guards.cooldown_min - mins)
                    return False

        return True
