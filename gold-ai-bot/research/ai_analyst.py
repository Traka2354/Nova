"""AI analiticar - "razmislja kao trejder".

Dva koraka:
  1) gather_market_intel(): koristi Claude `web_search` alat da prikupi aktuelne
     drivere za zlato (USD/DXY, prinosi, Fed, geopolitika, inflacija) i sazme ih.
  2) analyze(): spaja taj brief + cenovni/tehnicki kontekst i vraca STRUKTURISANU
     odluku (smer, sigurnost, razlog) preko structured outputs-a.

Koristi se Claude Opus 4.7 sa adaptivnim razmisljanjem. System promptovi su
stabilni i kesirani (prompt caching), a promenljivi podaci idu u user poruku.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
from typing import Literal

from pydantic import BaseModel, Field

log = logging.getLogger("ai")


class AnalysisResult(BaseModel):
    direction: Literal["buy", "sell", "hold"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    key_factors: list[str] = Field(default_factory=list)


INTEL_SYSTEM = (
    "Ti si makro analiticar specijalizovan za trziste zlata (XAUUSD). "
    "Tvoj zadatak je da prikupis i sazmes NAJNOVIJE faktore koji pomeraju cenu "
    "zlata: kretanje americkog dolara (DXY), realni prinosi na americke obveznice, "
    "ocekivanja od FED-a i kamatne stope, inflacija (CPI/PCE), geopoliticke tenzije, "
    "i znacajni ekonomski dogadjaji u kalendaru. Koristi web pretragu za sveze izvore. "
    "Vrati kratak, cinjenicni brief (5-8 recenica) bez investicionog saveta."
)

DECIDE_SYSTEM = (
    "Ti si disciplinovan day-trader za zlato (XAUUSD) cija je PRVA briga zastita "
    "kapitala - cilj je zaraditi, a ne izgubiti. Na osnovu makro brifa i tehnickog "
    "konteksta donosis odluku: 'buy', 'sell' ili 'hold'.\n"
    "Pravila:\n"
    "- Default je 'hold'. Trguj samo kad postoji jasna prednost (edge).\n"
    "- Ulazi SAMO ako se vise nezavisnih faktora poklapa (makro smer + tehnicki "
    "trend + momentum). Ako su signali pomesani, kontradiktorni ili slabi -> 'hold'.\n"
    "- Ne trguj PROTIV jasnog trenda i ne 'hvataj noz' u jakom kretanju.\n"
    "- Izbegavaj ulaz neposredno pre/posle velikih vesti (visok rizik whipsaw-a).\n"
    "- Trazi povoljan risk/reward (najmanje ~2:1 u korist profita).\n"
    "- Sigurnost (confidence) postavi realno i konzervativno: visoke vrednosti "
    "(>0.8) samo uz snazno poklapanje faktora; kod sumnje smanji sigurnost.\n"
    "Uvek navedi jasan razlog i kljucne faktore. Ti NISI finansijski savetnik; "
    "ovo je automatizovana procena za demo/test."
)


def _client(api_key: str):
    import anthropic  # lokalni import da projekat radi i bez paketa

    return anthropic.Anthropic(api_key=api_key)


def gather_market_intel(client, symbol: str, model: str, max_loops: int = 6) -> str:
    """Korak 1: web istrazivanje drivera za zlato."""
    today = _dt.date.today().isoformat()
    messages = [
        {
            "role": "user",
            "content": (
                f"Datum: {today}. Istrazi i sazmi aktuelne drivere za {symbol} (zlato) "
                "danas. Fokus: DXY/USD, realni prinosi, FED, inflacija, geopolitika, "
                "i bilo koji vazan dogadjaj iz ekonomskog kalendara za danas/sutra."
            ),
        }
    ]
    tools = [{"type": "web_search_20260209", "name": "web_search"}]
    system = [{"type": "text", "text": INTEL_SYSTEM, "cache_control": {"type": "ephemeral"}}]

    resp = None
    for _ in range(max_loops):
        resp = client.messages.create(
            model=model,
            max_tokens=4000,
            system=system,
            tools=tools,
            messages=messages,
        )
        # server-side alat moze da pauzira (pause_turn) - nastavi razgovor
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        break

    if resp is None:
        return ""
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def analyze(client, model: str, brief: str, technical: dict, extra_headlines: list[str]) -> AnalysisResult:
    """Korak 2: strukturisana odluka na osnovu brifa + tehnickog konteksta."""
    payload = {
        "macro_brief": brief or "(nema brifa)",
        "technical": technical,
        "headlines": extra_headlines[:10],
    }
    system = [{"type": "text", "text": DECIDE_SYSTEM, "cache_control": {"type": "ephemeral"}}]
    user = (
        "Na osnovu sledecih podataka donesi odluku za trgovanje zlatom.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )

    resp = client.messages.parse(
        model=model,
        max_tokens=6000,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=AnalysisResult,
    )
    result = resp.parsed_output
    if result is None:  # npr. odbijanje ili nepotpun izlaz
        return AnalysisResult(
            direction="hold",
            confidence=0.0,
            reasoning="AI nije vratio validan strukturisan odgovor; zadrzavam poziciju.",
        )
    return result


def get_signal(
    api_key: str,
    model: str,
    symbol: str,
    technical: dict,
    web_research: bool = True,
    extra_headlines: list[str] | None = None,
) -> AnalysisResult:
    """Glavni ulaz: vraca AnalysisResult ili 'hold' ako nesto ne radi."""
    if not api_key:
        return AnalysisResult(
            direction="hold", confidence=0.0, reasoning="Nedostaje ANTHROPIC_API_KEY."
        )
    try:
        client = _client(api_key)
        brief = gather_market_intel(client, symbol, model) if web_research else ""
        return analyze(client, model, brief, technical, extra_headlines or [])
    except Exception as e:  # noqa: BLE001 - bot ne sme da padne zbog AI-ja
        log.exception("AI signal nije uspeo: %s", e)
        return AnalysisResult(
            direction="hold", confidence=0.0, reasoning=f"Greska u AI sloju: {e}"
        )
