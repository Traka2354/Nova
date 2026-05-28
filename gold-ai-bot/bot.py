"""Glavna petlja: research -> AI odluka -> izvrsenje + copy trading.

Pokretanje (na Windows-u sa instaliranim MT5):
    python bot.py
"""
from __future__ import annotations

import datetime as _dt
import logging
import logging.handlers
import os
import time

import config
import copier
import risk
from mt5_client import MT5Client
from research import ai_analyst, news


def _setup_logging() -> None:
    """Log na konzolu i u rotirajuci fajl logs/bot.log (za VPS nadzor)."""
    os.makedirs("logs", exist_ok=True)
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    rotating = logging.handlers.RotatingFileHandler(
        "logs/bot.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    rotating.setFormatter(fmt)
    root.addHandler(console)
    root.addHandler(rotating)


_setup_logging()
log = logging.getLogger("bot")


class DailyGuard:
    """Prati dnevni gubitak i blokira trgovanje ako se predje limit."""

    def __init__(self) -> None:
        self.day = _dt.date.today()
        self.start_balance: float | None = None

    def check(self, client: MT5Client, max_daily_loss_pct: float) -> bool:
        today = _dt.date.today()
        if today != self.day or self.start_balance is None:
            self.day = today
            self.start_balance = client.account_balance()
        equity = client.account_equity()
        loss = (self.start_balance - equity) / self.start_balance if self.start_balance else 0.0
        if loss >= max_daily_loss_pct:
            log.warning("Dnevni limit gubitka dostignut (%.1f%%). Trgovanje pauzirano.", loss * 100)
            return False
        return True


def maybe_trade(client: MT5Client, cfg: config.Config) -> None:
    open_positions = [p for p in client.positions(cfg.symbol)]
    if len(open_positions) >= cfg.risk.max_open_positions:
        log.info("Dostignut max broj pozicija (%s). Cekam.", cfg.risk.max_open_positions)
        return

    highs, lows, closes = client.recent_rates(cfg.symbol, "M15", 100)
    technical = risk.technical_summary(closes)
    headlines = news.fetch_headlines() if cfg.ai.web_research else []

    if not cfg.ai.enabled:
        log.info("AI je iskljucen (AI_ENABLED=false). Nema novih trejdova.")
        return

    signal = ai_analyst.get_signal(
        api_key=cfg.ai.api_key,
        model=cfg.ai.model,
        symbol=cfg.symbol,
        technical=technical,
        web_research=cfg.ai.web_research,
        extra_headlines=headlines,
    )
    log.info("AI signal: %s (%.0f%%) - %s", signal.direction, signal.confidence * 100, signal.reasoning)

    if signal.direction == "hold":
        return
    if signal.confidence < cfg.risk.min_confidence:
        log.info("Sigurnost ispod praga (%.2f < %.2f). Preskacem.", signal.confidence, cfg.risk.min_confidence)
        return

    balance = client.account_balance()
    sym = client.symbol_info(cfg.symbol)
    tick = client.tick(cfg.symbol)
    entry = tick.ask if signal.direction == "buy" else tick.bid

    a = risk.atr(highs, lows, closes, cfg.risk.atr_period)
    sl_distance = a * cfg.risk.atr_sl_mult if a else entry * cfg.risk.sl_fallback_pct
    plan = risk.plan_trade(sym, signal.direction, entry, balance, cfg.risk, signal.confidence, sl_distance)

    client.open_market(
        symbol=cfg.symbol,
        side=signal.direction,
        volume=plan.volume,
        sl=plan.sl_price,
        tp=plan.tp_price,
        comment="ai-signal",
    )
    log.info(
        "Izvrsen %s @ %.2f | lot %.2f | SL %.2f (-%.2f) | TP %.2f (+%.2f)",
        signal.direction.upper(), entry, plan.volume,
        plan.sl_price, plan.sl_money, plan.tp_price, plan.tp_money,
    )


def main() -> None:
    cfg = config.load()
    log.info("Pokrecem Gold AI Bot | mode=%s | simbol=%s", cfg.mode, cfg.symbol)
    if not cfg.account.is_set:
        raise SystemExit(
            f"Nalog za '{cfg.mode}' rezim nije podesen. Popuni .env (vidi .env.example)."
        )

    client = MT5Client()
    client.connect(cfg.account.login, cfg.account.password, cfg.account.server, cfg.account.path)
    guard = DailyGuard()

    try:
        while True:
            try:
                # copy trading: uskladi master -> moj nalog
                copier.sync(client, cfg.account, cfg.copy, cfg.symbol)
                # vrati se na moj nalog (copier ostavlja konekciju na slave-u)
                client.connect(cfg.account.login, cfg.account.password, cfg.account.server, cfg.account.path)

                if guard.check(client, cfg.risk.max_daily_loss_pct):
                    maybe_trade(client, cfg)
            except Exception as e:  # noqa: BLE001 - petlja mora da prezivi gresku
                log.exception("Greska u ciklusu: %s", e)
            time.sleep(cfg.poll_interval_sec)
    except KeyboardInterrupt:
        log.info("Zaustavljam bota...")
    finally:
        client.shutdown()


if __name__ == "__main__":
    main()
