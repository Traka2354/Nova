"""Filteri ulaska - disciplinovan trejder ne ulazi u losim uslovima."""
from __future__ import annotations

import datetime as _dt

from config import Filters


def spread_ok(ask: float, bid: float, max_spread: float) -> bool:
    """Ne ulazi kad je spread prevelik (los fill, cesto oko vesti)."""
    if max_spread <= 0:
        return True
    return (ask - bid) <= max_spread


def within_hours(now_utc: _dt.datetime, f: Filters) -> bool:
    """Trguj samo u likvidnim satima i (po default-u) ne vikendom."""
    if not f.allow_weekend and now_utc.weekday() >= 5:  # 5=subota, 6=nedelja
        return False
    if f.start_hour == f.end_hour:  # 24h rezim
        return True
    h = now_utc.hour
    if f.start_hour < f.end_hour:
        return f.start_hour <= h < f.end_hour
    # opseg koji prelazi ponoc (npr. 22-06)
    return h >= f.start_hour or h < f.end_hour
