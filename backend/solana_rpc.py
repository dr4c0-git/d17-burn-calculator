"""
Solana indexer for D17 burn / refund activity, provider-agnostic.

Uses standard Solana JSON-RPC methods only (`getTokenAccountsByOwner`,
`getSignaturesForAddress`, `getTransaction`) so any provider works :
Alchemy, QuickNode, Helius, public mainnet, etc.

Strategy
--------
SPL token transfers happen through Associated Token Accounts (ATAs), not
the parent wallet :

1. Resolve the ATA for (wallet, XBT_mint) once at startup, with retry
   if the provider rate-limits us.
2. Backfill : enumerate every signature on the ATA via
   `getSignaturesForAddress`, hydrate each one with `getTransaction`,
   and parse pre/postTokenBalances to extract the burn / refund.
3. Steady-state : same flow but only the most-recent page each cycle.

We rebuild the same `tokenTransfers` shape that the previous Helius
implementation emitted so `state.py` doesn't change.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional

import httpx

from state import BurnState, BurnTx

log = logging.getLogger("solana-rpc")

ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY", "")
SOLANA_RPC_URL = os.getenv(
    "SOLANA_RPC_URL",
    f"https://solana-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}" if ALCHEMY_API_KEY else "",
)
BURN_ADDRESS = os.getenv("BURN_ADDRESS", "4Upb3WBoMSAaMC3eytHvSnL4hYLvDEL8zpQr4Q9U6JsB")
REFUND_ADDRESS = os.getenv(
    "REFUND_ADDRESS", "DWUFCjBxqDuXpUGF8KnVzhAuz2uhRyfrky4aFc2JvvgH"
)
XBT_MINT = os.getenv("XBT_MINT", "")
# 300s × 2 ATAs is well within free-tier limits across providers.
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))
INIT_RETRY_INTERVAL = int(os.getenv("INIT_RETRY_INTERVAL", "300"))

SIGS_PAGE_SIZE = 1000
MAX_PAGES = 50  # safety cap : up to 50,000 signatures


async def start_indexer(state: BurnState) -> asyncio.Task:
    return asyncio.create_task(_indexer_loop(state), name="solana-rpc-indexer")


async def stop_indexer(task: asyncio.Task) -> None:
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass


async def _indexer_loop(state: BurnState) -> None:
    """Resolve ATAs (with retry on failure) then poll forever."""
    if not SOLANA_RPC_URL:
        log.warning("SOLANA_RPC_URL not set — indexer will not run.")
        return

    log.info("Indexer starting. POLL_INTERVAL=%ds", POLL_INTERVAL)

    async with httpx.AsyncClient(timeout=60.0) as client:
        burn_ata: Optional[str] = None
        refund_ata: Optional[str] = None

        # Step 1 : keep trying to resolve ATAs.
        while burn_ata is None or refund_ata is None:
            try:
                if not XBT_MINT:
                    log.warning("XBT_MINT not configured — indexer will not run.")
                    return
                if burn_ata is None:
                    burn_ata = await _resolve_ata(client, BURN_ADDRESS, XBT_MINT)
                if refund_ata is None:
                    refund_ata = await _resolve_ata(client, REFUND_ADDRESS, XBT_MINT)

                if burn_ata is None or refund_ata is None:
                    log.warning(
                        "Could not resolve ATAs (burn=%s refund=%s). Retrying in %ds.",
                        burn_ata, refund_ata, INIT_RETRY_INTERVAL,
                    )
                    await asyncio.sleep(INIT_RETRY_INTERVAL)
                    continue

                log.info("Resolved ATAs: burn=%s, refund=%s", burn_ata, refund_ata)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.exception(
                    "ATA resolution failed: %s. Retrying in %ds.", e, INIT_RETRY_INTERVAL
                )
                await asyncio.sleep(INIT_RETRY_INTERVAL)

        # Step 2 : steady-state polling.
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
    if not state.backfill_done:
        if burn_ata:
            log.info("Backfill: burn ATA %s", burn_ata)
            txs = await _full_history(client, burn_ata)
            log.info("Backfill: parsed %d burn transfers", len(txs))
            for tx in txs:
                burn = _parse_burn_tx(tx)
                if burn is not None:
                    state.add_burn(burn)

        if refund_ata:
            log.info("Backfill: refund ATA %s", refund_ata)
            txs = await _full_history(client, refund_ata)
            log.info("Backfill: parsed %d refund transfers", len(txs))
            for tx in txs:
                recipient = _parse_refund_recipient(tx)
                if recipient is not None:
                    state.apply_refund(tx.get("signature", ""), recipient)

        state.backfill_done = True
        snap = state.snapshot()
        log.info(
            "Backfill complete. burns=%d, total_xbt=%.2f",
            snap.total_burns, snap.total_xbt_burned,
        )
        return

    # Steady-state : just the latest page on each ATA.
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
    """Send a JSON-RPC request and return the `result` field."""
    r = await client.post(
        SOLANA_RPC_URL,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    )
    r.raise_for_status()
    body = r.json()
    if "error" in body:
        raise RuntimeError(f"RPC {method} error: {body['error']}")
    return body.get("result")


async def _resolve_ata(client: httpx.AsyncClient, wallet: str, mint: str) -> Optional[str]:
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


async def _hydrate_one(client: httpx.AsyncClient, signature: str) -> Optional[dict[str, Any]]:
    """Standard `getTransaction` + parse pre/postTokenBalances into our shape.

    Returns the same dict shape the previous Helius parsed-tx returned :
    `{signature, timestamp, tokenTransfers: [{fromUserAccount, toUserAccount, mint, tokenAmount}]}`.
    Returns None if the tx didn't move any token balances we care about.
    """
    try:
        tx = await _rpc(
            client,
            "getTransaction",
            [
                signature,
                {
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0,
                    "commitment": "confirmed",
                },
            ],
        )
    except Exception as e:
        log.warning("getTransaction(%s) failed: %s", signature[:8], e)
        return None

    if tx is None:
        return None

    block_time = int(tx.get("blockTime") or 0)
    meta = tx.get("meta") or {}
    if meta.get("err") is not None:
        return None  # failed tx

    pre_balances = {b["accountIndex"]: b for b in (meta.get("preTokenBalances") or [])}
    post_balances = {b["accountIndex"]: b for b in (meta.get("postTokenBalances") or [])}

    # Aggregate per (owner, mint, decimals).
    deltas: dict[tuple[str, str, int], int] = {}
    indexes = set(pre_balances) | set(post_balances)
    for idx in indexes:
        pre_b = pre_balances.get(idx)
        post_b = post_balances.get(idx)
        ref = post_b or pre_b
        owner = ref.get("owner")
        mint = ref.get("mint")
        if not owner or not mint:
            continue
        decimals = int((ref.get("uiTokenAmount") or {}).get("decimals", 0) or 0)
        pre_amt = int((pre_b or {}).get("uiTokenAmount", {}).get("amount", "0") or 0)
        post_amt = int((post_b or {}).get("uiTokenAmount", {}).get("amount", "0") or 0)
        delta = post_amt - pre_amt
        if delta != 0:
            key = (owner, mint, decimals)
            deltas[key] = deltas.get(key, 0) + delta

    if not deltas:
        return None

    senders = [(k, -v) for k, v in deltas.items() if v < 0]
    receivers = [(k, v) for k, v in deltas.items() if v > 0]

    # Match senders to receivers by mint. Burn-style txs are typically
    # one-sender-one-receiver per mint, which is what we care about.
    transfers: list[dict[str, Any]] = []
    for (s_owner, s_mint, decimals), amt_sent in senders:
        for (r_owner, r_mint, _), amt_recv in receivers:
            if s_mint != r_mint:
                continue
            amount_raw = min(amt_sent, amt_recv)
            if amount_raw <= 0:
                continue
            ui_amount = amount_raw / (10 ** decimals)
            transfers.append(
                {
                    "fromUserAccount": s_owner,
                    "toUserAccount": r_owner,
                    "mint": s_mint,
                    "tokenAmount": ui_amount,
                }
            )
            break

    return {
        "signature": signature,
        "timestamp": block_time,
        "tokenTransfers": transfers,
    }


async def _hydrate_transactions(
    client: httpx.AsyncClient, signatures: list[str]
) -> list[dict[str, Any]]:
    """Hydrate signatures sequentially with a small inter-call sleep.

    Sequential rather than concurrent on purpose : free tiers across
    providers rate-limit bursts. 50ms between calls = ~20 req/s, gentle.
    """
    out: list[dict[str, Any]] = []
    for sig in signatures:
        parsed = await _hydrate_one(client, sig)
        if parsed is not None:
            out.append(parsed)
        await asyncio.sleep(0.05)
    return out


async def _full_history(client: httpx.AsyncClient, account: str) -> list[dict[str, Any]]:
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
    page = await _signatures_page(client, account, None, 100)
    sigs = [s["signature"] for s in page if s.get("signature")]
    return await _hydrate_transactions(client, sigs)


# ---------- Parsing (operates on our internal shape) ----------


def _parse_burn_tx(tx: dict[str, Any]) -> Optional[BurnTx]:
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
