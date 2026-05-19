"""
SonicCopyX — Test konekcija
Pokretanje: python test.py
"""

import sys
import os

# Dodaj parent folder da nadje config
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 55)
print("  SonicCopyX — Dijagnostika konekcija")
print("=" * 55)
print()

errors = []

# ── 1. Provjeri config.py ─────────────────────────────────────
print("[1/4] Provjera config.py...")
try:
    import config

    missing = []
    if not config.MT5_LOGIN:       missing.append("MT5_LOGIN")
    if not config.MT5_PASSWORD:    missing.append("MT5_PASSWORD")
    if not config.MT5_SERVER:      missing.append("MT5_SERVER")
    if not config.BINGX_API_KEY:   missing.append("BINGX_API_KEY")
    if not config.BINGX_SECRET_KEY: missing.append("BINGX_SECRET_KEY")

    if missing:
        print(f"  [!] config.py nije popunjen: {', '.join(missing)}")
        print(f"      Otvori config.py u Notepadu i unesi podatke.")
        errors.append("config")
    else:
        print(f"  [OK] config.py popunjen.")
        print(f"       MT5 login: {config.MT5_LOGIN}")
        print(f"       MT5 server: {config.MT5_SERVER}")
        print(f"       BingX API key: {config.BINGX_API_KEY[:8]}...")

except Exception as e:
    print(f"  [!] Ne mogu ucitati config.py: {e}")
    errors.append("config")

print()

# ── 2. Provjeri Python pakete ─────────────────────────────────
print("[2/4] Provjera Python paketa...")
try:
    import requests
    print(f"  [OK] requests {requests.__version__}")
except ImportError:
    print("  [!] requests nije instaliran → pip install requests")
    errors.append("requests")

try:
    import MetaTrader5 as mt5
    print(f"  [OK] MetaTrader5 {mt5.__version__}")
    MT5_PKG = True
except ImportError:
    print("  [!] MetaTrader5 nije instaliran → pip install MetaTrader5")
    print("      (Radi samo na Windows sa instaliranim MT5 terminalom)")
    errors.append("MetaTrader5")
    MT5_PKG = False

print()

# ── 3. Provjeri BingX API ─────────────────────────────────────
print("[3/4] Test BingX konekcije...")
if "config" not in errors and "requests" not in errors:
    try:
        from bingx_api import BingXClient
        bingx = BingXClient(config.BINGX_API_KEY, config.BINGX_SECRET_KEY)

        import hmac, hashlib, time, requests as req

        ts = int(time.time() * 1000)
        params = {"timestamp": ts}
        query = f"timestamp={ts}"
        sig = hmac.new(config.BINGX_SECRET_KEY.encode(), query.encode(), hashlib.sha256).hexdigest()
        params["signature"] = sig

        r = req.get(
            "https://open-api.bingx.com/openApi/swap/v2/user/balance",
            params=params,
            headers={"X-BX-APIKEY": config.BINGX_API_KEY},
            timeout=8
        )
        data = r.json()

        if data.get("code") == 0:
            bal = data.get("data", {}).get("balance", {})
            equity = bal.get("equity", "?")
            available = bal.get("availableMargin", "?")
            print(f"  [OK] BingX spojen!")
            print(f"       Equity:    {equity} USDT")
            print(f"       Available: {available} USDT")

            # Provjeri GOLD-USDT poziciju
            ts2 = int(time.time() * 1000)
            p2 = {"symbol": "GOLD-USDT", "timestamp": ts2}
            q2 = f"symbol=GOLD-USDT&timestamp={ts2}"
            s2 = hmac.new(config.BINGX_SECRET_KEY.encode(), q2.encode(), hashlib.sha256).hexdigest()
            p2["signature"] = s2
            r2 = req.get(
                "https://open-api.bingx.com/openApi/swap/v2/user/positions",
                params=p2,
                headers={"X-BX-APIKEY": config.BINGX_API_KEY},
                timeout=8
            )
            d2 = r2.json()
            if d2.get("code") == 0:
                positions = [p for p in d2.get("data", []) if float(p.get("positionAmt", 0)) != 0]
                if positions:
                    for pos in positions:
                        amt  = pos.get("positionAmt", 0)
                        side = "LONG" if float(amt) > 0 else "SHORT"
                        pnl  = pos.get("unrealizedProfit", "?")
                        print(f"       Aktivna GOLD-USDT pozicija: {side} {abs(float(amt))} contracts | PnL: {pnl}")
                else:
                    print(f"       GOLD-USDT: nema otvorenih pozicija")
        else:
            print(f"  [!] BingX greska: {data.get('msg', data)}")
            print(f"      Provjeri API ključeve i dozvole (Perpetual Trading mora biti ukljucen).")
            errors.append("bingx")

    except Exception as e:
        print(f"  [!] BingX test greska: {e}")
        errors.append("bingx")
else:
    print("  [--] Preskoceno (config ili requests nedostaju)")

print()

# ── 4. Provjeri MT5 ───────────────────────────────────────────
print("[4/4] Test MT5 konekcije...")
if MT5_PKG and "config" not in errors:
    try:
        if mt5.initialize():
            if config.MT5_LOGIN and config.MT5_PASSWORD and config.MT5_SERVER:
                ok = mt5.login(config.MT5_LOGIN,
                               password=config.MT5_PASSWORD,
                               server=config.MT5_SERVER)
                if ok:
                    info = mt5.account_info()
                    print(f"  [OK] MT5 spojen!")
                    print(f"       Account: #{info.login}")
                    print(f"       Broker:  {info.company}")
                    print(f"       Balance: {info.balance:.2f} {info.currency}")
                    print(f"       Equity:  {info.equity:.2f} {info.currency}")

                    positions = mt5.positions_get()
                    if positions:
                        print(f"       Otvorene pozicije: {len(positions)}")
                        for p in positions:
                            ptype = "BUY" if p.type == 0 else "SELL"
                            print(f"         #{p.ticket} {ptype} {p.volume} {p.symbol}")
                    else:
                        print(f"       Otvorene pozicije: 0 (broker mozda blokira citanje)")
                else:
                    print(f"  [!] MT5 login greska: {mt5.last_error()}")
                    print(f"      Provjeri login/password/server u config.py")
                    errors.append("mt5_login")
            else:
                info = mt5.account_info()
                if info:
                    print(f"  [OK] MT5 spojen (vec prijavljen terminal)")
                    print(f"       Account: #{info.login} | Balance: {info.balance:.2f}")
                else:
                    print(f"  [!] MT5 terminal nije prijavljen. Prijavi se u MT5 i pokusaj ponovo.")
                    errors.append("mt5_login")
            mt5.shutdown()
        else:
            print(f"  [!] MT5 initialize() greska: {mt5.last_error()}")
            print(f"      Provjeri da je MT5 terminal otvoren i prijavljen.")
            errors.append("mt5_init")
    except Exception as e:
        print(f"  [!] MT5 test greska: {e}")
        errors.append("mt5")
elif not MT5_PKG:
    print("  [--] Preskoceno (MetaTrader5 paket nije instaliran)")
else:
    print("  [--] Preskoceno (config nedostaje)")

# ── Rezultat ──────────────────────────────────────────────────
print()
print("=" * 55)
if not errors:
    print("  SVE OK — pokreni copier.py / START.bat")
else:
    print(f"  PROBLEMI: {len(errors)} stvar(i) treba popraviti (vidi gore)")
print("=" * 55)
print()
input("Pritisni Enter za izlaz...")
