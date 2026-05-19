# ═══════════════════════════════════════════════════════════════
#   SonicCopyX — MT5 → BingX Konfiguracija
#   Popuni ovo prije pokretanja!
# ═══════════════════════════════════════════════════════════════

# ── MT5 Account ─────────────────────────────────────────────────
MT5_LOGIN    = 0          # Tvoj MT5 broj accounta  (npr. 123456789)
MT5_PASSWORD = ""         # MT5 lozinka              (npr. "MyPass123")
MT5_SERVER   = ""         # Broker server            (npr. "ICMarkets-Live01")

# ── BingX API ───────────────────────────────────────────────────
# Dobij na: BingX -> Account -> API Management -> Create API
BINGX_API_KEY    = ""     # Npr. "abc123..."
BINGX_SECRET_KEY = ""     # Npr. "xyz789..."

# ── Konverzija lotova ────────────────────────────────────────────
# Koliko BingX contracts = 1 MT5 lot
# GOLD-USDT: 1 contract = 1 oz zlata
# XAUUSD MT5: 1 lot = 100 oz  →  LOT_TO_QTY = 100
# Ako hoces polovic: postavi na 50
LOT_TO_QTY = {
    "XAUUSD": 100.0,   # 1 MT5 lot = 100 BingX GOLD-USDT contracts
}

# ── Mapiranje simbola MT5 → BingX ───────────────────────────────
SYMBOL_MAP = {
    "XAUUSD": "GOLD-USDT",
}

# ── Postavke ────────────────────────────────────────────────────
POLL_INTERVAL_SEC = 0.5   # Koliko cesto se provjerava MT5 (sekunde)
MIN_QTY_GOLD      = 1.0   # Minimalna kolicina na BingX (1 contract)
