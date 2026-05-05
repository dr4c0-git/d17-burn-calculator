"""
Helius indexer for D17 burn / refund activity.

Strategy
--------
SPL token transfers happen through Associated Token Accounts (ATAs), not
the parent wallet. Helius's enhanced-tx-by-address endpoint queries the
wallet directly and misses many of those transfers. So we instead :

1. Resolve the ATA for (wallet, XBT_mint) via `getTokenAccountsByOwner`.
2. Enumerate every signature touching the ATA via `getSignaturesForAddress`
   (1000-per-page, paginated backward).
3. Hydrate each signature batch via the parsed-tx endpoint
   (`/v0/transactions/?commitment=...&api-key=...`) to get tokenTransfers.

This captures the full burn / refund history the wallet endpoint misses.

Docs:
- https://docs.helius.dev/api-reference/rpc-getsignaturesforaddress
- https://docs.helius.dev/api-reference/parsed-transactions
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional

import httpx

from state import BurnState, BurnTx

log = logging.getLogger("helius")

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
BURN_ADDRESS = os.getenv("BURN_ADDRESS", "4Upb3WBoMSAaMC3eytHvSnL4hYLvDEL8zpQr4Q9U6JsB")
REFUND_ADDRESS = os.getenv(
    "REFUND_ADDRESS", "DWUFCjBxqDuXpUGF8KnVzhAuz2uhRyfrky4aFc2JvvgH"
)
XBT_MINT = os.getenv("XBT_MINT", "")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))

HELIUS_RPC = "https://mainnet.helius-rpc.com"
HELIUS_API = "https://api.helius.xyz"

SIGS_PAGE_SIZE = 1000  # max for getSignaturesForAddress
PARSE_BATCH_SIZE = 100  # max for the parsed-transactions endpoint
MAX_PAGES = 50  # safety: covers up to 50,000 signatures per address


async def start_indexer(state: BurnState) -> asyncio.Task:
    if not HELIUS_API_KEY:
        log.warning("HELIUS_API_KEY not set — indexer will not start.")
    return asyncio.create_task(_indexer_loop(state), name="helius-indexer")


async def stop_indexer(task: asyncio.Task) -> None:
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass


async def _indexer_loop(state: BurnState) -> None:
    if not HELIUS_API_KEY:
        return
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Resolve ATAs once (they're deterministic per (wallet, mint)).
        burn_ata = await _resolve_ata(client, BURN_ADDRESS, XBT_MINT) if XBT_MINT else None
        refund_ata = (
            await _resolve_ata(client, REFUND_ADDRESS, XBT_MINT) if XBT_MINT else None
        )
        log.info("Resolved ATAs: burn=%s, refund=%s", burn_ata, refund_ata)

        while True:
            try:
                await _poll_once(client, state, burn_ata, refund_ata)
                state.mark_indexed()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.exception("indexer cycle failed: %s", e)
            await asyncio.sleep(POLL_INTERVAL)


async def _poll_once(
    client: httpx.AsyncClient,
    state: BurnState,
    burn_ata: Optional[str],
    refund_ata: Optional[str],
) -> None:
    """Initial cycle does a full backfill, subsequent cycles only walk forward."""
    if not state.backfill_done:
        if burn_ata:
            log.info("Backfill: burn ATA %s", burn_ata)
            txs = await _full_history(client, burn_ata)
            log.info("Backfill: %d txs from burn ATA", len(txs))
            for tx in txs:
                burn = _parse_burn_tx(tx)
                if burn is not None:
                    state.add_burn(burn)

        if refund_ata:
            log.info("Backfill: refund ATA %s", refund_ata)
            txs = await _full_history(client, refund_ata)
            log.info("Backfill: %d txs from refund ATA", len(txs))
            for tx in txs:
                recipient = _parse_refund_recipient(tx)
                if recipient is not None:
                    state.apply_refund(tx.get("signature", ""), recipient)

        state.backfill_done = True
        return

    # Steady-state: just fetch the latest page on each ATA. Dedup-by-signature
    # in BurnState makes this idempotent.
    if burn_ata:
        recent = await _recent_page(client, burn_ata)
        for tx in recent:
            burn = _parse_burn_tx(tx)
            if burn is not None:
                state.add_burn(burn)

    if refund_ata:
        recent = await _recent_page(client, refund_ata)
        for tx in recent:
            recipient = _parse_refund_recipient(tx)
            if recipient is not None:
                state.apply_refund(tx.get("signature", ""), recipient)


# ---------- HTTP helpers ----------


async def _rpc(client: httpx.AsyncClient, method: str, params: list[Any]) -> Any:
    """Call a Helius RPC method and return the `result` field."""
    url = f"{HELIUS_RPC}/?api-key={HELIUS_API_KEY}"
    r = await client.post(url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    r.raise_for_status()
    body = r.json()
    if "error" in body:
        raise RuntimeError(f"RPC {method} error: {body['error']}")
    return body.get("result")


async def _resolve_ata(client: httpx.AsyncClient, wallet: str, mint: str) -> Optional[str]:
    """Find the (single) token account owned by `wallet` for `mint`."""
    res = await _rpc(
        client,
        "getTokenAccountsByOwner",
        [wallet, {"mint": mint}, {"encoding": "jsonParsed"}],
    )
    accounts = (res or {}).get("value") or []
    if not accounts:
        return None
    return accounts[0].get("pubkey")


async def _signatures_page(
    client: httpx.AsyncClient, account: str, before: Optional[str], limit: int
) -> list[dict[str, Any]]:
    opts: dict[str, Any] = {"limit": limit}
    if before:
        opts["before"] = before
    res = await _rpc(client, "getSignaturesForAddress", [account, opts])
    return res or []


async def _hydrate_transactions(
    client: httpx.AsyncClient, signatures: list[str]
) -> list[dict[str, Any]]:
    """Bulk-fetch parsed transactions for a list of signatures."""
    if not signatures:
        return []
    out: list[dict[str, Any]] = []
    url = f"{HELIUS_API}/v0/transactions/?api-key={HELIUS_API_KEY}"
    for i in range(0, len(signatures), PARSE_BATCH_SIZE):
        batch = signatures[i : i + PARSE_BATCH_SIZE]
        r = await client.post(url, json={"transactions": batch})
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            out.extend(data)
    return out


async def _full_history(client: httpx.AsyncClient, account: str) -> list[dict[str, Any]]:
    """Paginate every signature on `account` and hydrate them all."""
    sigs: list[str] = []
    before: Optional[str] = None
    for _ in range(MAX_PAGES):
        page = await _signatures_page(client, account, before, SIGS_PAGE_SIZE)
        if not page:
            break
        sigs.extend(s["signature"] for s in page if s.get("signature"))
        if len(page) < SIGS_PAGE_SIZE:
            break
        before = page[-1].get("signature")
        if not before:
            break
    return await _hydrate_transactions(client, sigs)


async def _recent_page(client: httpx.AsyncClient, account: str) -> list[dict[str, Any]]:
    """Just the most-recent page, hydrated. Used in steady-state polling."""
    page = await _signatures_page(client, account, None, 100)
    sigs = [s["signature"] for s in page if s.get("signature")]
    return await _hydrate_transactions(client, sigs)


# ---------- Parsing ----------


def _parse_burn_tx(tx: dict[str, Any]) -> Optional[BurnTx]:
    """Pull a burn out of a parsed Helius tx, if any."""
    transfers = tx.get("tokenTransfers", []) or []
    matching = [
        t for t in transfers
        if t.get("toUserAccount") == BURN_ADDRESS
        and (not XBT_MINT or t.get("mint") == XBT_MINT)
    ]
    if not matching:
        return None
    sender = matching[0].get("fromUserAccount") or ""
    amount = sum(float(t.get("tokenAmount", 0) or 0) for t in matching)
    if amount <= 0 or not sender:
        return None
    return BurnTx(
        signature=tx.get("signature", ""),
        sender=sender,
        amount=amount,
        block_time=int(tx.get("timestamp", 0) or 0),
    )


def _parse_refund_recipient(tx: dict[str, Any]) -> Optional[str]:
    transfers = tx.get("tokenTransfers", []) or []
    for t in transfers:
        if (
            t.get("fromUserAccount") == REFUND_ADDRESS
            and (not XBT_MINT or t.get("mint") == XBT_MINT)
        ):
            recipient = t.get("toUserAccount")
            if recipient:
                return recipient
    return None
