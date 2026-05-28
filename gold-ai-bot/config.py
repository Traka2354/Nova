"""Ucitavanje konfiguracije iz .env fajla."""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _f(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw not in (None, "") else default


def _i(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw not in (None, "") else default


def _b(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    return raw.strip().lower() in ("1", "true", "yes", "da", "on")


@dataclass
class Account:
    login: int
    password: str
    server: str
    path: str | None = None

    @property
    def is_set(self) -> bool:
        return bool(self.login and self.password and self.server)


@dataclass
class RiskParams:
    tp_min_pct: float
    tp_max_pct: float
    sl_min_pct: float
    sl_max_pct: float
    lot_size: float
    max_open_positions: int
    max_daily_loss_pct: float
    min_confidence: float


@dataclass
class AIConfig:
    enabled: bool
    api_key: str
    model: str
    web_research: bool


@dataclass
class CopyConfig:
    enabled: bool
    master: Account
    lot_multiplier: float
    magic: int


@dataclass
class Config:
    mode: str
    account: Account
    symbol: str
    risk: RiskParams
    ai: AIConfig
    copy: CopyConfig
    poll_interval_sec: int


def _account(prefix: str) -> Account:
    return Account(
        login=_i(f"{prefix}_MT5_LOGIN", 0),
        password=os.getenv(f"{prefix}_MT5_PASSWORD", "") or "",
        server=os.getenv(f"{prefix}_MT5_SERVER", "") or "",
        path=os.getenv(f"{prefix}_MT5_PATH") or None,
    )


def load() -> Config:
    mode = (os.getenv("ACCOUNT_MODE", "demo") or "demo").strip().lower()
    account = _account("DEMO") if mode == "demo" else _account("LIVE")

    master = Account(
        login=_i("COPY_MASTER_LOGIN", 0),
        password=os.getenv("COPY_MASTER_PASSWORD", "") or "",
        server=os.getenv("COPY_MASTER_SERVER", "") or "",
        path=os.getenv("COPY_MASTER_PATH") or None,
    )

    return Config(
        mode=mode,
        account=account,
        symbol=os.getenv("SYMBOL", "XAUUSD") or "XAUUSD",
        risk=RiskParams(
            tp_min_pct=_f("TP_MIN_PCT", 0.01),
            tp_max_pct=_f("TP_MAX_PCT", 0.03),
            sl_min_pct=_f("SL_MIN_PCT", 0.005),
            sl_max_pct=_f("SL_MAX_PCT", 0.01),
            lot_size=_f("LOT_SIZE", 0.01),
            max_open_positions=_i("MAX_OPEN_POSITIONS", 1),
            max_daily_loss_pct=_f("MAX_DAILY_LOSS_PCT", 0.05),
            min_confidence=_f("MIN_CONFIDENCE", 0.6),
        ),
        ai=AIConfig(
            enabled=_b("AI_ENABLED", True),
            api_key=os.getenv("ANTHROPIC_API_KEY", "") or "",
            model=os.getenv("AI_MODEL", "claude-opus-4-7") or "claude-opus-4-7",
            web_research=_b("AI_WEB_RESEARCH", True),
        ),
        copy=CopyConfig(
            enabled=_b("COPY_ENABLED", False),
            master=master,
            lot_multiplier=_f("COPY_LOT_MULTIPLIER", 1.0),
            magic=_i("COPY_MAGIC", 778899),
        ),
        poll_interval_sec=_i("POLL_INTERVAL_SEC", 60),
    )
