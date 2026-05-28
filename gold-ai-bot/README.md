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
  donosi TP% balansa).
- **Zaštita kapitala — „misli kao trejder"**:
  - **Trailing stop + break-even** (`trade_manager.py`) — čim trejd ode u plus,
    SL ide na ulaz pa prati cenu; dobitak se ne vraća u gubitak.
  - **Filteri ulaska** (`filters.py`) — preskače ulaz kad je spred prevelik i
    trguje samo u likvidnim satima (UTC), ne vikendom.
  - **Circuit breakeri** (`guards.py`) — dnevni limit gubitka, dnevni profit
    target (poknjiži dan), pauza posle X uzastopnih gubitaka, i cooldown posle
    gubitka (anti-revenge trading).
  - **Tvrda zaštita ukupnog drawdown-a (za 12X / funded nalog)** — pošto te
    broker izbacuje na ~10%, bot staje sa rezervom (default −6%), zatvori sve
    pozicije i ostane zaustavljen do kraja dana. Baza se pamti u
    `logs/guard_state.json` (preživljava restart VPS-a). Za 12X postavi
    `ACCOUNT_BASELINE` na pojačani iznos.
  - **AI stav** — analitičar je podešen konzervativno: default „hold", ulaz samo
    uz poklapanje više faktora i povoljan risk/reward.
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

## VPS deployment (Windows) — preporuceno za 24/5 rad

Bot mora da radi non-stop, a laptop se uspava/zatvara — zato ide na **Windows
VPS**. (MT5 Python paket radi samo na Windows-u.)

**Koji VPS:** Windows Server 2019/2022, ~2 vCPU / 4 GB RAM je dovoljno. Po
mogucstvu **blizu broker servera** (cesto London ili New York) radi nize
latencije. Bilo koji "Windows VPS" ili "Forex VPS" provajder je u redu.

**Koraci:**
1. Poveži se na VPS preko **RDP** (Remote Desktop).
2. Instaliraj **Python 3.11+** (obavezno obeleži *Add Python to PATH*).
3. Instaliraj **MT5 terminal** od svog brokera, uloguj se na nalog, pa:
   *Tools → Options → Expert Advisors* → dozvoli, i uključi dugme **AutoTrading**.
   Dodaj `XAUUSD` u Market Watch.
4. Kopiraj `gold-ai-bot` folder na VPS (npr. preko git-a ili RDP copy/paste).
5. Pokreni **`setup.bat`** (napravi `.venv`, instalira pakete, kreira `.env`).
6. Popuni **`.env`** (MT5 podaci, `ANTHROPIC_API_KEY`).
7. Pokreni **`run.bat`** — bot radi i sam se restartuje ako padne.

**Da nastavi da radi i kad zatvoriš RDP:** samo zatvori RDP prozor (ne
"Log off") — sesija ostaje aktivna. Logovi su u `logs/bot.log`.

**Da prezivi i restart VPS-a** (jedna opcija):
- *Task Scheduler* → novi task → *Run whether user is logged on or not* →
  *At log on* → akcija: pokreni `run.bat`. Podesi i MT5 da se sam pokrece.
- Ili instaliraj kao Windows servis preko **NSSM** (`nssm install GoldAIBot`).

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
├── trade_manager.py     # trailing stop + break-even na otvorenim pozicijama
├── filters.py           # filteri ulaska (spread, sati, vikend)
├── guards.py            # circuit breakeri (dnevni limit/target, cooldown)
├── copier.py            # copy trading master -> slave
├── bot.py               # glavna petlja
├── backtest.py          # backtest skelet
├── setup.bat            # jednokratni setup na Windows VPS-u
├── run.bat              # pokretanje sa auto-restartom
├── requirements.txt
└── .env.example
```
