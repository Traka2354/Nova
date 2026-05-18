# SonicCopyX — MT5 → MT4 Trade Copier

## Kako radi

```
MT5 Terminal (Master)
  └── SonicCopyX_Sender_MT5.mq5
        ↓ piše svakih 200ms
  %AppData%\MetaQuotes\Terminal\Common\Files\SonicCopyX_signal.csv
        ↑ čita svakih 1s
  └── SonicCopyX_Receiver_MT4.mq4
MT4 Terminal (Slave)
```

Oba terminala na istom VPS-u dijele isti "Common" folder, bez ikakvog kašnjenja.

---

## Instalacija korak po korak

### Korak 1 — MT5 Sender EA

1. Otvori MT5 terminal
2. Idi na **File → Open Data Folder**
3. Otvori mapu `MQL5\Experts\`
4. Kopiraj `SonicCopyX_Sender_MT5.mq5` u tu mapu
5. U MT5: desni klik na **Expert Advisors** u Navigator → **Refresh**
6. Prevuci EA na **bilo koji chart** (npr. EURUSD M1) na master accountu
7. Parametri:
   - `SignalFile` = `SonicCopyX_signal.csv` (ne mijenjaj)
   - `LotMultiplier` = `1.0` (1.0 = isti lot; 0.5 = pola lota na slaveu)
   - `CopyAllSymbols` = `true` ili `false`
8. Klikni **OK** i provjeri da je smiley face ikona na chartu (EA aktivan)

### Korak 2 — MT4 Receiver EA

1. Otvori MT4 terminal
2. Idi na **File → Open Data Folder**
3. Otvori mapu `MQL4\Experts\`
4. Kopiraj `SonicCopyX_Receiver_MT4.mq4` u tu mapu
5. U MT4: desni klik na **Expert Advisors** → **Refresh**
6. Prevuci EA na **bilo koji chart** na slave accountu
7. Parametri:
   - `SignalFile` = `SonicCopyX_signal.csv` (mora biti isti kao u Senderu)
   - `Slippage` = `30` (može biti veći za volatile parove)
   - `MagicNumber` = `88888` (nemoj mijenjati ako imaš više EA-ova)
   - `CloseIfSenderOffline` = `true` — preporučeno za sigurnost
8. Klikni **OK**

### Korak 3 — Provjera da radi

1. Otvori trejd na MT5 master accountu
2. Idi na MT4 i provjeri da se trejd otvorio u roku od 1-2 sekunde
3. U MT4 → **Experts** tab (donji panel) vidiš log poruke

---

## Česti problemi

| Problem | Rješenje |
|---------|----------|
| EA ne radi, smiley face je tužan | Uključi **Auto Trading** dugme u MT5/MT4 toolbaru |
| Trejd se ne kopira | Provjeri da oba EA imaju isti `SignalFile` naziv |
| "OrderSend error 130" | SL/TP je preblizu cijeni — smanji ili stavi na 0 |
| "OrderSend error 134" | Nema dovoljno sredstava na slave accountu |
| MT4 ne vidi fajl | Provjeri da je `FILE_COMMON` opcija aktivna — oba EA je koriste automatski |

---

## Sigurnost

- Receiver automatski zatvara sve pozicije ako MT5 Sender stane (HeartbeatTimeout)
- Magic number osigurava da Receiver ne dira trejdove otvorene ručno
- Lot multiplier omogućava risk management (npr. 0.1 = 10% lota mastera)

---

## Lokacija dijeljenog fajla na Windows VPS

```
C:\Users\<KorisničkoIme>\AppData\Roaming\MetaQuotes\Terminal\Common\Files\SonicCopyX_signal.csv
```

Možeš otvoriti ovaj fajl u Notepadu da vidiš live pozicije.
