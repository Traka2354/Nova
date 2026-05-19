"""BingX Perpetual Futures API wrapper."""

import hmac
import hashlib
import time
import requests
import logging
from typing import Optional

log = logging.getLogger("BingX")

BASE_URL = "https://open-api.bingx.com"


class BingXClient:
    def __init__(self, api_key: str, secret_key: str):
        self.api_key    = api_key
        self.secret_key = secret_key
        self.session    = requests.Session()
        self.session.headers.update({"X-BX-APIKEY": api_key})

    # ── Potpis ────────────────────────────────────────────────────
    def _sign(self, params: dict) -> str:
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return hmac.new(
            self.secret_key.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _params(self, extra: dict) -> dict:
        p = {**extra, "timestamp": int(time.time() * 1000)}
        p["signature"] = self._sign(p)
        return p

    # ── Pozicije ──────────────────────────────────────────────────
    def get_positions(self, symbol: str) -> Optional[dict]:
        """Vraća otvorenu poziciju za symbol ili None ako nema."""
        try:
            p = self._params({"symbol": symbol})
            r = self.session.get(f"{BASE_URL}/openApi/swap/v2/user/positions", params=p, timeout=5)
            r.raise_for_status()
            data = r.json()
            if data.get("code") != 0:
                log.error(f"BingX positions greška: {data}")
                return None
            positions = data.get("data", [])
            for pos in positions:
                if pos.get("symbol") == symbol and float(pos.get("positionAmt", 0)) != 0:
                    return pos
            return None
        except Exception as e:
            log.error(f"get_positions greška: {e}")
            return None

    def get_position_qty(self, symbol: str) -> float:
        """Vraća neto količinu: pozitivno=LONG, negativno=SHORT, 0=nema."""
        pos = self.get_positions(symbol)
        if pos is None:
            return 0.0
        amt = float(pos.get("positionAmt", 0))
        return amt

    # ── Narudžbe ──────────────────────────────────────────────────
    def market_order(self, symbol: str, side: str, quantity: float) -> bool:
        """
        side: "BUY" ili "SELL"
        quantity: broj contracts (pozitivno)
        """
        try:
            p = self._params({
                "symbol":   symbol,
                "side":     side,
                "type":     "MARKET",
                "quantity": str(quantity),
            })
            r = self.session.post(f"{BASE_URL}/openApi/swap/v2/trade/order", params=p, timeout=5)
            r.raise_for_status()
            data = r.json()
            if data.get("code") != 0:
                log.error(f"market_order greška [{side} {quantity} {symbol}]: {data}")
                return False
            order_id = data.get("data", {}).get("order", {}).get("orderId", "?")
            log.info(f"BingX order otvoren: {side} {quantity} {symbol} | ID: {order_id}")
            return True
        except Exception as e:
            log.error(f"market_order exception: {e}")
            return False

    def close_position(self, symbol: str) -> bool:
        """Zatvori cijelu poziciju na symbol."""
        try:
            p = self._params({"symbol": symbol})
            r = self.session.post(f"{BASE_URL}/openApi/swap/v2/trade/closePosition", params=p, timeout=5)
            r.raise_for_status()
            data = r.json()
            if data.get("code") != 0:
                log.error(f"close_position greška [{symbol}]: {data}")
                return False
            log.info(f"BingX pozicija zatvorena: {symbol}")
            return True
        except Exception as e:
            log.error(f"close_position exception: {e}")
            return False

    def test_connection(self) -> bool:
        """Provjeri da API ključevi rade."""
        try:
            p = self._params({})
            r = self.session.get(f"{BASE_URL}/openApi/swap/v2/user/balance", params=p, timeout=5)
            data = r.json()
            if data.get("code") != 0:
                log.error(f"BingX auth greška: {data.get('msg')}")
                return False
            balance = data.get("data", {}).get("balance", {})
            usdt = balance.get("equity", "?")
            log.info(f"BingX spojen — USDT equity: {usdt}")
            return True
        except Exception as e:
            log.error(f"BingX test_connection greška: {e}")
            return False
