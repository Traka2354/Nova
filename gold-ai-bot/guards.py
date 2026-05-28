"""Zastitni circuit breakeri - kapital pre profita (poseban fokus na 12X/funded).

Blokira otvaranje novih pozicija (i po potrebi zatvara sve) kada:
  - je probijen UKUPNI drawdown limit (npr. 6%) - kljucno za 12X nalog gde te
    broker izbacuje na ~10%; zato stajemo sa rezervom i ostajemo zaustavljeni
    do kraja dana (sticky),
  - je dnevni gubitak dostigao limit,
  - je dnevni profit cilj dostignut (poknjizi dan i stani),
  - je bilo previse uzastopnih gubitaka,
  - je skoro bio gubitak (cooldown, anti-revenge trading).

Stanje (pocetni balans, pik, dan zaustavljanja) se pamti u logs/guard_state.json
da bi prezivelo restart VPS-a - inace bi restart resetovao bazu i sakrio pravi
drawdown na funded nalogu.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import os
from dataclasses import dataclass

from config import Config
from mt5_client import MT5Client

log = logging.getLogger("guard")

# STATE_DIR omogucava vise instanci bota (npr. 12X-zastita i copy/AI) bez sukoba
_STATE_FILE = os.path.join(os.getenv("STATE_DIR", "logs"), "guard_state.json")


@dataclass
class GuardState:
    can_open: bool
    halt: bool          # tvrdi stop (probijen DD) - zatvori sve i pauziraj copier
    reason: str


def _load_state() -> dict:
    try:
        with open(_STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
    tmp = _STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, _STATE_FILE)


class RiskGuard:
    def __init__(self) -> None:
        self.state = _load_state()
        self.day: _dt.date | None = None
        self.day_start_balance: float | None = None

    # ---- baza za merenje ukupnog drawdown-a ----
    def _baseline(self, client: MT5Client, cfg: Config) -> float:
        if cfg.guards.account_baseline > 0:
            return cfg.guards.account_baseline
        login = cfg.account.login
        if self.state.get("login") == login and self.state.get("baseline"):
            return float(self.state["baseline"])
        baseline = client.account_balance()
        self.state.update({"login": login, "baseline": baseline, "peak": baseline})
        _save_state(self.state)
        log.info("Postavljen baseline za DD: %.2f (nalog %s)", baseline, login)
        return baseline

    def _reset_day(self, client: MT5Client) -> None:
        today = _dt.date.today()
        if today != self.day or self.day_start_balance is None:
            self.day = today
            self.day_start_balance = client.account_balance()

    def assess(self, client: MT5Client, cfg: Config) -> GuardState:
        self._reset_day(client)
        equity = client.account_equity()
        baseline = self._baseline(client, cfg)
        today_str = _dt.date.today().isoformat()

        # --- UKUPNI drawdown (najvaznije za 12X) ---
        peak = max(float(self.state.get("peak", baseline)), equity)
        if peak != self.state.get("peak"):
            self.state["peak"] = peak
            _save_state(self.state)
        ref = peak if cfg.guards.drawdown_trailing else baseline
        total_dd = (ref - equity) / ref if ref else 0.0

        already_halted = self.state.get("halted_day") == today_str
        if total_dd >= cfg.guards.max_total_drawdown_pct or already_halted:
            if not already_halted:
                self.state["halted_day"] = today_str
                _save_state(self.state)
                log.warning(
                    "TVRDI STOP: ukupni drawdown %.2f%% (limit %.1f%%). "
                    "Zatvaram i pauziram do kraja dana - cuvam nalog.",
                    total_dd * 100, cfg.guards.max_total_drawdown_pct * 100,
                )
            return GuardState(can_open=False, halt=True, reason="max_total_drawdown")

        # --- dnevni gubitak / profit ---
        start = self.day_start_balance or baseline
        day_change = (equity - start) / start if start else 0.0
        if day_change <= -cfg.risk.max_daily_loss_pct:
            return GuardState(False, False, "daily_loss")
        if cfg.guards.daily_profit_pct > 0 and day_change >= cfg.guards.daily_profit_pct:
            log.info("Dnevni profit cilj (%.1f%%) dostignut. Knjizim dan.", day_change * 100)
            return GuardState(False, False, "daily_profit_target")

        # --- uzastopni gubici / cooldown ---
        midnight = _dt.datetime.combine(_dt.date.today(), _dt.time.min)
        try:
            deals = client.closed_deals(cfg.risk.bot_magic, cfg.symbol, midnight)
        except Exception as e:  # noqa: BLE001
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
            return GuardState(False, False, "consecutive_losses")

        if deals and cfg.guards.cooldown_min > 0:
            last_time, last_profit = deals[-1]
            if last_profit < 0:
                mins = (_dt.datetime.now() - last_time).total_seconds() / 60
                if mins < cfg.guards.cooldown_min:
                    return GuardState(False, False, "cooldown")

        return GuardState(True, False, "ok")
