"""Tanak omotac oko MetaTrader5 paketa.

VAZNO: paket `MetaTrader5` radi samo na Windows-u. Na drugim sistemima import
nece uspeti, pa se MT5 ucitava lenjivo (tek pri konekciji) da bi se ostatak
projekta (config, risk, backtest) mogao razvijati i na Mac/Linux.
"""
from __future__ import annotations

import datetime as _dt
import logging
from dataclasses import dataclass

log = logging.getLogger("mt5")

_mt5 = None


def _api():
    global _mt5
    if _mt5 is None:
        try:
            import MetaTrader5 as mt5  # type: ignore
        except ImportError as e:  # pragma: no cover - zavisi od OS-a
            raise RuntimeError(
                "MetaTrader5 paket nije dostupan. Pokreni bota na Windows-u "
                "(VPS ili Parallels) sa instaliranim MT5 terminalom."
            ) from e
        _mt5 = mt5
    return _mt5


@dataclass
class Position:
    ticket: int
    symbol: str
    side: str  # "buy" | "sell"
    volume: float
    price_open: float
    sl: float
    tp: float
    profit: float
    magic: int
    comment: str


class MT5Client:
    def __init__(self) -> None:
        self.mt5 = _api()
        self._logged_in: int | None = None

    # ---- konekcija ----
    def connect(self, login: int, password: str, server: str, path: str | None = None) -> None:
        if self._logged_in == login:
            return
        kwargs = {"path": path} if path else {}
        if not self.mt5.initialize(**kwargs):
            raise RuntimeError(f"MT5 initialize neuspesno: {self.mt5.last_error()}")
        if not self.mt5.login(login=login, password=password, server=server):
            raise RuntimeError(f"MT5 login neuspesan ({login}@{server}): {self.mt5.last_error()}")
        self._logged_in = login
        log.info("Povezan na MT5 nalog %s @ %s", login, server)

    def shutdown(self) -> None:
        if _mt5 is not None:
            self.mt5.shutdown()
        self._logged_in = None

    # ---- citanje ----
    def account_balance(self) -> float:
        info = self.mt5.account_info()
        if info is None:
            raise RuntimeError("account_info() vratio None - nema konekcije?")
        return float(info.balance)

    def account_equity(self) -> float:
        info = self.mt5.account_info()
        return float(info.equity) if info else 0.0

    def symbol_info(self, symbol: str):
        info = self.mt5.symbol_info(symbol)
        if info is None or not info.visible:
            # simbol mora biti "vidljiv" u Market Watch-u da bi se trgovao
            self.mt5.symbol_select(symbol, True)
            info = self.mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"Simbol {symbol} nije pronadjen kod brokera")
        return info

    def tick(self, symbol: str):
        t = self.mt5.symbol_info_tick(symbol)
        if t is None:
            raise RuntimeError(f"Nema cene (tick) za {symbol}")
        return t

    def positions(self, symbol: str | None = None) -> list[Position]:
        raw = self.mt5.positions_get(symbol=symbol) if symbol else self.mt5.positions_get()
        out: list[Position] = []
        for p in raw or []:
            out.append(
                Position(
                    ticket=p.ticket,
                    symbol=p.symbol,
                    side="buy" if p.type == self.mt5.POSITION_TYPE_BUY else "sell",
                    volume=p.volume,
                    price_open=p.price_open,
                    sl=p.sl,
                    tp=p.tp,
                    profit=p.profit,
                    magic=p.magic,
                    comment=p.comment,
                )
            )
        return out

    def closed_deals(self, magic: int, symbol: str | None, since: _dt.datetime):
        """Zatvarajuci dealovi (vreme, profit) za dati magic, hronoloski."""
        deals = self.mt5.history_deals_get(since, _dt.datetime.now())
        out: list[tuple[_dt.datetime, float]] = []
        for d in deals or []:
            if d.entry != self.mt5.DEAL_ENTRY_OUT:
                continue
            if magic and d.magic != magic:
                continue
            if symbol and d.symbol != symbol:
                continue
            out.append((_dt.datetime.fromtimestamp(d.time), float(d.profit)))
        out.sort(key=lambda x: x[0])
        return out

    def recent_closes(self, symbol: str, timeframe: str = "M15", count: int = 100):
        """Lista zatvarajucih cena (najstarija -> najnovija) za indikatore."""
        tf = getattr(self.mt5, f"TIMEFRAME_{timeframe}")
        rates = self.mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None:
            return []
        return [float(r["close"]) for r in rates]

    def recent_rates(self, symbol: str, timeframe: str = "M15", count: int = 100):
        """(highs, lows, closes) najstarija -> najnovija; za ATR i indikatore."""
        tf = getattr(self.mt5, f"TIMEFRAME_{timeframe}")
        rates = self.mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None:
            return [], [], []
        highs = [float(r["high"]) for r in rates]
        lows = [float(r["low"]) for r in rates]
        closes = [float(r["close"]) for r in rates]
        return highs, lows, closes

    # ---- trgovanje ----
    def _filling(self, symbol: str):
        info = self.symbol_info(symbol)
        mode = getattr(info, "filling_mode", 0)
        # bitno: neki brokeri prihvataju samo odredjeni filling rezim
        if mode & 1:
            return self.mt5.ORDER_FILLING_FOK
        if mode & 2:
            return self.mt5.ORDER_FILLING_IOC
        return self.mt5.ORDER_FILLING_RETURN

    def open_market(
        self,
        symbol: str,
        side: str,
        volume: float,
        sl: float = 0.0,
        tp: float = 0.0,
        magic: int = 0,
        comment: str = "gold-ai-bot",
    ):
        t = self.tick(symbol)
        is_buy = side == "buy"
        price = t.ask if is_buy else t.bid
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": self.mt5.ORDER_TYPE_BUY if is_buy else self.mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 20,
            "magic": magic,
            "comment": comment,
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self._filling(symbol),
        }
        result = self.mt5.order_send(request)
        if result is None or result.retcode != self.mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"Otvaranje pozicije neuspesno: {getattr(result, 'comment', result)}")
        log.info("Otvorena %s %s @ %.2f vol=%s", side.upper(), symbol, price, volume)
        return result

    def close_position(self, pos: Position):
        t = self.tick(pos.symbol)
        is_buy = pos.side == "buy"
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": self.mt5.ORDER_TYPE_SELL if is_buy else self.mt5.ORDER_TYPE_BUY,
            "position": pos.ticket,
            "price": t.bid if is_buy else t.ask,
            "deviation": 20,
            "magic": pos.magic,
            "comment": "close",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self._filling(pos.symbol),
        }
        result = self.mt5.order_send(request)
        if result is None or result.retcode != self.mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"Zatvaranje pozicije neuspesno: {getattr(result, 'comment', result)}")
        log.info("Zatvorena pozicija #%s", pos.ticket)
        return result

    def modify_sl_tp(self, pos: Position, sl: float, tp: float):
        request = {
            "action": self.mt5.TRADE_ACTION_SLTP,
            "symbol": pos.symbol,
            "position": pos.ticket,
            "sl": float(sl),
            "tp": float(tp),
            "magic": pos.magic,
        }
        result = self.mt5.order_send(request)
        if result is None or result.retcode != self.mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"Izmena SL/TP neuspesna: {getattr(result, 'comment', result)}")
        return result
