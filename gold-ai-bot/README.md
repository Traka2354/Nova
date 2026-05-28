# Gold AI Bot (XAUUSD) + MetaTrader 5

AI trading bot za zlato koji "razmislja kao trejder": prikuplja informacije sa
weba, donosi odluku (buy/sell/hold) sa obrazlozenjem, automatski otvara/zatvara
pozicije sa TP/SL kao procentom balansa, i moze da kopira signale sa drugog
MT5 naloga na tvoj nalog.

> **Vazna napomena za MacBook:** Python paket `MetaTrader5` radi **samo na
> Windows-u**. Kod, logiku i backtest mozes razvijati i na Macu, ali za **zivu
> konekciju i trgovanje** pokreni bota na **Windows VPS-u** ili u **Parallels/
> Windows VM-u** na Macu (MT5 terminal mora biti instaliran i ulogovan).

## Sta radi

- **AI mozak** (`research/ai_analyst.py`) — Claude (Opus 4.7) sa `web_search`
  alatom: prikuplja drivere za zlato (DXY/USD, prinosi, FED, inflacija,
  geopolitika) i vraca strukturisanu odluku + sigurnost + razlog.
- **Izvrsenje** (`mt5_client.py`, `bot.py`) — otvara/zatvara pozicije na MT5.
- **Risk** (`risk.py`) — TP 1–3% i SL 0.5–1% **od ukupnog balansa** uz
  **auto-skaliranje lota**: SL se postavlja na ATR (volatilnost) razdaljinu, a
  veličina pozicije se računa tako da taj SL gubi tačno SL% balansa (TP onda
  donosi TP% balansa). Plus dnevni limit gubitka i max broj pozicija.
- **Copy trading** (`copier.py`) — kopira pozicije sa MASTER naloga (tudji
  signali, npr. preko investor/read-only logina) na tvoj nalog.
- **Backtest** (`backtest.py`) — test deterministickog dela strategije na
  istoriji.

## Podesavanje

1. Instaliraj zavisnosti (na Windows-u za zivo trgovanje):
   ```
   pip install -r requirements.txt
   ```
2. Kopiraj `.env.example` u `.env` i popuni:
   - `ACCOUNT_MODE=demo` ili `live` (oba naloga imaju svoja polja),
   - MT5 login/lozinka/server,
   - `ANTHROPIC_API_KEY` (za AI mozak),
   - opciono `COPY_*` polja za copy trading.
3. U MT5 terminalu ukljuci **Algo Trading** i dodaj simbol `XAUUSD` u Market Watch.

## Pokretanje

```
python bot.py        # zivi bot (demo ili live, prema ACCOUNT_MODE)
python backtest.py   # backtest deterministicke strategije
```

## Bezbednost

- Prvo testiraj na **demo** nalogu. AI ne garantuje profit — trziste je
  nepredvidivo. Risk kontrole (SL, dnevni limit) su tu da ogranice stetu.
- `.env` se ne commituje (vec je u `.gitignore`). Ne stavljaj lozinke u kod.
- Copy trading sa tudjeg naloga radi samo ako imas pristup (investor/read-only
  login) ili ako trejder javno objavljuje signale. Privatne/zakljucane naloge
  bez pristupa nije moguce kopirati.

## Struktura

```
gold-ai-bot/
├── config.py            # ucitavanje .env, demo/live prekidac, risk, copy
├── mt5_client.py        # konekcija + otvaranje/zatvaranje pozicija (MT5)
├── risk.py              # TP/SL iz % balansa + indikatori (SMA/RSI)
├── research/
│   ├── news.py          # opcione vesti (RSS)
│   └── ai_analyst.py    # Claude API: web research + strukturisana odluka
├── copier.py            # copy trading master -> slave
├── bot.py               # glavna petlja
├── backtest.py          # backtest skelet
├── requirements.txt
└── .env.example
```
