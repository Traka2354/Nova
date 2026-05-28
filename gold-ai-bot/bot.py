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
import filters
import risk
import trade_manager
from guards import RiskGuard
from mt5_client import MT5Client
from research import ai_analyst, news


def _setup_logging() -> None:
    """Log na konzolu i u rotirajuci fajl (za VPS nadzor)."""
    state_dir = os.getenv("STATE_DIR", "logs")
    os.makedirs(state_dir, exist_ok=True)
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    rotating = logging.handlers.RotatingFileHandler(
        os.path.join(state_dir, "bot.log"), maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    rotating.setFormatter(fmt)
    root.addHandler(console)
    root.addHandler(rotating)


_setup_logging()
log = logging.getLogger("bot")


def maybe_trade(
    client: MT5Client,
    cfg: config.Config,
    highs: list[float],
    lows: list[float],
    closes: list[float],
    atr_value: float | None,
) -> None:
    open_positions = [p for p in client.positions(cfg.symbol)]
    if len(open_positions) >= cfg.risk.max_open_positions:
        log.info("Dostignut max broj pozicija (%s). Cekam.", cfg.risk.max_open_positions)
        return

    if not filters.within_hours(_dt.datetime.utcnow(), cfg.filters):
        log.info("Van sati trgovanja (UTC). Bez novih ulazaka.")
        return

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

    if not filters.spread_ok(tick.ask, tick.bid, cfg.filters.max_spread):
        log.info("Spread prevelik (%.2f). Preskacem ulaz.", tick.ask - tick.bid)
        return

    entry = tick.ask if signal.direction == "buy" else tick.bid
    sl_distance = atr_value * cfg.risk.atr_sl_mult if atr_value else entry * cfg.risk.sl_fallback_pct
    plan = risk.plan_trade(sym, signal.direction, entry, balance, cfg.risk, signal.confidence, sl_distance)

    client.open_market(
        symbol=cfg.symbol,
        side=signal.direction,
        volume=plan.volume,
        sl=plan.sl_price,
        tp=plan.tp_price,
        magic=cfg.risk.bot_magic,
        comment="ai-signal",
    )
    log.info(
        "Izvrsen %s @ %.2f | lot %.2f | SL %.2f (-%.2f) | TP %.2f (+%.2f)",
        signal.direction.upper(), entry, plan.volume,
        plan.sl_price, plan.sl_money, plan.tp_price, plan.tp_money,
    )


def _flatten(client: MT5Client, cfg: config.Config) -> None:
    """Zatvori sve pozicije na simbolu - zastita naloga pri tvrdom stopu."""
    positions = client.positions(cfg.symbol)
    for p in positions:
        try:
            client.close_position(p)
        except Exception as e:  # noqa: BLE001
            log.error("Ne mogu da zatvorim #%s: %s", p.ticket, e)
    if positions:
        log.warning("Zatvoreno %s pozicija (tvrdi stop / zastita naloga).", len(positions))


def main() -> None:
    cfg = config.load()
    log.info("Pokrecem Gold AI Bot | mode=%s | simbol=%s", cfg.mode, cfg.symbol)
    if not cfg.account.is_set:
        raise SystemExit(
            f"Nalog za '{cfg.mode}' rezim nije podesen. Popuni .env (vidi .env.example)."
        )

    client = MT5Client()
    client.connect(cfg.account.login, cfg.account.password, cfg.account.server, cfg.account.path)
    guard = RiskGuard()

    try:
        while True:
            try:
                # osiguraj da smo na svom nalogu pre procene
                client.connect(cfg.account.login, cfg.account.password, cfg.account.server, cfg.account.path)
                state = guard.assess(client, cfg)

                if state.halt:
                    # tvrdi stop (probijen ukupni DD): cuvaj nalog
                    if cfg.guards.drawdown_flatten:
                        _flatten(client, cfg)
                    # ne sinhronizuj copier dok smo zaustavljeni (da se ne reotvara)
                else:
                    copier.sync(client, cfg.account, cfg.copy, cfg.symbol)
                    # copier ostavlja konekciju na masteru -> vrati se na moj nalog
                    client.connect(cfg.account.login, cfg.account.password, cfg.account.server, cfg.account.path)

                highs, lows, closes = client.recent_rates(cfg.symbol, "M15", 100)
                atr_value = risk.atr(highs, lows, closes, cfg.risk.atr_period)

                # uvek upravljaj otvorenim pozicijama (trailing/break-even)
                trade_manager.manage(client, cfg, atr_value)

                # nove ulaske dozvoli samo ako zastite to dozvoljavaju
                if state.can_open:
                    maybe_trade(client, cfg, highs, lows, closes, atr_value)
            except Exception as e:  # noqa: BLE001 - petlja mora da prezivi gresku
                log.exception("Greska u ciklusu: %s", e)
            time.sleep(cfg.poll_interval_sec)
    except KeyboardInterrupt:
        log.info("Zaustavljam bota...")
    finally:
        client.shutdown()


if __name__ == "__main__":
    main()
