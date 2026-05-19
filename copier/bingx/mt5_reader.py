"""Čita MT5 pozicije via Python MetaTrader5 paket."""

import logging
from typing import Optional

log = logging.getLogger("MT5")

try:
    import MetaTrader5 as mt5
    _MT5_PKG = True
except ImportError:
    _MT5_PKG = False
    log.warning("MetaTrader5 paket nije instaliran. Pokreni: pip install MetaTrader5")


def connect(login: int, password: str, server: str) -> bool:
    if not _MT5_PKG:
        return False
    if not mt5.initialize():
        log.error(f"MT5 initialize() greška: {mt5.last_error()}")
        return False
    if login and password and server:
        if not mt5.login(login, password=password, server=server):
            log.error(f"MT5 login greška: {mt5.last_error()}")
            return False
    info = mt5.account_info()
    if info is None:
        log.error("MT5: ne mogu dohvatiti account info")
        return False
    log.info(f"MT5 spojen — #{info.login} | {info.currency} | Balance: {info.balance:.2f}")
    return True


def disconnect():
    if _MT5_PKG:
        mt5.shutdown()


def get_net_lots(mt5_symbol: str) -> float:
    """
    Vraća neto lot veličinu za symbol.
    Pozitivno = net LONG, Negativno = net SHORT, 0 = nema pozicije.
    """
    if not _MT5_PKG:
        return 0.0
    positions = mt5.positions_get(symbol=mt5_symbol)
    if positions is None or len(positions) == 0:
        return 0.0
    net = 0.0
    for p in positions:
        if p.type == 0:    # POSITION_TYPE_BUY
            net += p.volume
        else:              # POSITION_TYPE_SELL
            net -= p.volume
    return round(net, 2)


def is_connected() -> bool:
    if not _MT5_PKG:
        return False
    return mt5.terminal_info() is not None
