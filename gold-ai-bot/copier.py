"""Copy trading: kopiranje pozicija sa MASTER naloga na MOJ (slave) nalog.

VAZNO (ogranicenje MT5 Python paketa): jedan proces moze biti ulogovan na SAMO
JEDAN nalog u datom trenutku. Zato kopir u svakom ciklusu:
  1) uloguje se na MASTER, procita njegove otvorene pozicije,
  2) vrati se na SLAVE (moj nalog) i uskladi ih.
Za maksimalnu pouzdanost u produkciji preporucuje se zaseban MT5 terminal/proces
za MASTER (npr. preko investor/read-only logina). Ovo je radni temelj.

Kopirane pozicije se oznacavaju `magic` brojem i komentarom "copy:<master_ticket>"
da bi se razlikovale od pozicija koje otvara AI i da bi se znalo sta zatvoriti
kada master zatvori svoju poziciju.
"""
from __future__ import annotations

import logging

from config import Account, CopyConfig
from mt5_client import MT5Client, Position

log = logging.getLogger("copy")

_PREFIX = "copy:"


def _copied_index(slave_positions: list[Position], magic: int) -> dict[str, Position]:
    """Mapira master_ticket -> kopirana pozicija na slave nalogu."""
    out: dict[str, Position] = {}
    for p in slave_positions:
        if p.magic == magic and p.comment.startswith(_PREFIX):
            master_ticket = p.comment[len(_PREFIX):]
            out[master_ticket] = p
    return out


def sync(
    client: MT5Client,
    slave: Account,
    cfg: CopyConfig,
    symbol: str | None = None,
) -> None:
    """Jedan ciklus sinhronizacije master -> slave."""
    if not cfg.enabled or not cfg.master.is_set:
        return

    # 1) procitaj master pozicije
    client.connect(cfg.master.login, cfg.master.password, cfg.master.server, cfg.master.path)
    master_positions = client.positions(symbol)
    master_by_ticket = {str(p.ticket): p for p in master_positions}

    # 2) vrati se na svoj (slave) nalog i uskladi
    client.connect(slave.login, slave.password, slave.server, slave.path)
    copied = _copied_index(client.positions(symbol), cfg.magic)

    # otvori nove (master ima, ja nemam)
    for ticket, mpos in master_by_ticket.items():
        if ticket in copied:
            continue
        volume = round(mpos.volume * cfg.lot_multiplier, 2)
        if volume <= 0:
            continue
        try:
            client.open_market(
                symbol=mpos.symbol,
                side=mpos.side,
                volume=volume,
                magic=cfg.magic,
                comment=f"{_PREFIX}{ticket}",
            )
            log.info("Kopirana master pozicija #%s (%s %s)", ticket, mpos.side, mpos.symbol)
        except Exception as e:  # noqa: BLE001
            log.error("Kopiranje #%s nije uspelo: %s", ticket, e)

    # zatvori one koje je master zatvorio (ja imam kopiju, master vise nema)
    for ticket, spos in copied.items():
        if ticket not in master_by_ticket:
            try:
                client.close_position(spos)
                log.info("Zatvorena kopija #%s jer je master zatvorio #%s", spos.ticket, ticket)
            except Exception as e:  # noqa: BLE001
                log.error("Zatvaranje kopije #%s nije uspelo: %s", spos.ticket, e)
