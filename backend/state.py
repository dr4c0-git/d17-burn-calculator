"""
In-memory state for the burn calculator.

Holds the chronologically ordered list of valid burn transactions for the
current event, with refund-aware invalidation. Recomputes tranches on demand.

Multipliers per @xbt2027 (April 29, 2026):
  [2.4, 2.0, 1.8, 1.6, 1.5, 1.4, 1.3, 1.2, 1.1, 1.0]
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

# Tranche multipliers from the lowest tranche index (1st 10% of senders) to
# the highest (last 10%). Order matters - kept here as the single source of truth.
MULTIPLIERS: tuple[float, ...] = (
    2.4, 2.0, 1.8, 1.6, 1.5, 1.4, 1.3, 1.2, 1.1, 1.0,
)


@dataclass
class BurnTx:
    """A single XBT burn transaction observed on-chain."""

    signature: str
    sender: str
    amount: float  # XBT
    block_time: int  # unix seconds


@dataclass
class StateSnapshot:
    total_burns: int
    total_xbt_burned: float
    last_indexed_at: Optional[str]


class BurnState:
    """Thread-safe state holder for burns + refunds."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # Chronological list of valid burn txs (ones that haven't been
        # invalidated by a refund). Order matters.
        self._burns: list[BurnTx] = []
        # Set of signatures already seen (to avoid double-counting on poll).
        self._seen_burn_sigs: set[str] = set()
        self._seen_refund_sigs: set[str] = set()
        self._last_indexed_at: Optional[datetime] = None
        # True once the initial backward pagination has covered full history
        # for both burn and refund addresses. Subsequent polls only fetch the
        # most recent page (sufficient given POLL_INTERVAL).
        self.backfill_done: bool = False

    # ---------- Mutation (called from the indexer) ----------

    def add_burn(self, tx: BurnTx) -> None:
        with self._lock:
            if tx.signature in self._seen_burn_sigs:
                return
            self._seen_burn_sigs.add(tx.signature)
            self._burns.append(tx)
            # Burns from a single poll may arrive out of order across pages;
            # keep the canonical list sorted by block_time (then signature for
            # tie-breaking on identical timestamps).
            self._burns.sort(key=lambda t: (t.block_time, t.signature))

    def apply_refund(self, refund_sig: str, sender: str) -> None:
        """A refund from `sender` invalidates all of their prior burns.

        Per @xbt2027 (May 4, 2026): "i didn't see a partial refund yet but
        resets position completely". So any refund clears the sender's history.
        """
        with self._lock:
            if refund_sig in self._seen_refund_sigs:
                return
            self._seen_refund_sigs.add(refund_sig)
            self._burns = [t for t in self._burns if t.sender != sender]

    def mark_indexed(self) -> None:
        with self._lock:
            self._last_indexed_at = datetime.now(timezone.utc)

    # ---------- Read (called from the API) ----------

    def snapshot(self) -> StateSnapshot:
        with self._lock:
            return StateSnapshot(
                total_burns=len(self._burns),
                total_xbt_burned=sum(t.amount for t in self._burns),
                last_indexed_at=(
                    self._last_indexed_at.isoformat() if self._last_indexed_at else None
                ),
            )

    def simulate(self, amount: float, extra_burns_after: int, event_share_pct: float) -> dict:
        """Project a hypothetical new burn's tranche, multiplier, and allocation.

        We assume the burn happens *now* (i.e. it joins at the end of the
        current queue). `extra_burns_after` lets the caller model how many
        additional burns they expect to follow theirs before the event closes.
        """
        with self._lock:
            current_count = len(self._burns)
            # The user's position in 1-indexed terms is current_count + 1.
            your_position = current_count + 1
            total_after_you = current_count + 1 + extra_burns_after

            tranche = _tranche_index(your_position, total_after_you)
            multiplier = MULTIPLIERS[tranche - 1]

            # Allocation share: contribution_user / total_weighted_contribution.
            # We don't know the *amounts* of the extra_burns_after yet; for a
            # pessimistic-but-honest estimate we assume they each match the
            # current average burn size. Falls back to the user's amount if
            # there's no burn history yet.
            avg_amount = (
                sum(t.amount for t in self._burns) / len(self._burns)
                if self._burns
                else amount
            )

            user_weighted = amount * multiplier
            existing_weighted = sum(
                t.amount * MULTIPLIERS[_tranche_index(idx + 1, total_after_you) - 1]
                for idx, t in enumerate(self._burns)
            )
            extra_weighted = sum(
                avg_amount
                * MULTIPLIERS[_tranche_index(current_count + 2 + j, total_after_you) - 1]
                for j in range(extra_burns_after)
            )
            denom = user_weighted + existing_weighted + extra_weighted
            share = (user_weighted / denom) if denom > 0 else 0.0

            allocation_pct = share * event_share_pct

            note = (
                "Estimate assumes future burns match the average size of "
                "current burns. Actual allocation depends on real volume "
                "and the exact closing time of the current event."
            )

            return {
                "your_position": your_position,
                "total_after_you": total_after_you,
                "your_tranche": tranche,
                "your_multiplier": multiplier,
                "your_allocation_pct": allocation_pct,
                "note": note,
            }


def _tranche_index(position: int, total: int) -> int:
    """Return the 1-indexed tranche (1..10) a tx at `position` (1-indexed)
    falls into when the queue ends at `total` total transactions.

    The 10 tranches are equal-size by count. With non-divisible counts we
    use ceil division so the first tranche absorbs any extra.
    """
    if total <= 0:
        return 10
    if position < 1:
        position = 1
    if position > total:
        position = total
    # tranche size = ceil(total / 10)
    size = -(-total // 10)
    tranche = ((position - 1) // size) + 1
    return min(max(tranche, 1), 10)
