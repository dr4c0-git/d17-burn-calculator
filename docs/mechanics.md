# D17 XBT Burn Mechanics - Reference

This document is the authoritative source for the burn mechanics implemented in this calculator.

> **Always verify against the latest tweets from [@xbt2027](https://x.com/xbt2027) before acting on financial decisions.**

## Source tweets

### Pinned plan - April 29, 2026

> THE PLAN - D17
>
> The token will launch AFTER infrastructure is live. No funds will be raised BEFORE that.
>
> 2027 Holders will receive 1:1 allocations (maximum 35%)
>
> XBT holders can send their XBT to the address: `4Upb3WBoMSAaMC3eytHvSnL4hYLvDEL8zpQr4Q9U6JsB`
>
> Early senders will receive more allocation, and in total 15% will be distributed to XBT holders.
>
> Senders can ask for refunds anytime by sending 1 XBT to `DWUFCjBxqDuXpUGF8KnVzhAuz2uhRyfrky4aFc2JvvgH` and will receive 100% XBT back.

[Source](https://x.com/xbt2027/status/2049515425122128352)

### Burn mechanics tweet - April 29, 2026

> XBT Burn mechanics
>
> However much is burned it will be divided in 10 equal size chunks
> first 10% of senders will receive 2.4x
> second 10% of senders will receive 2x
> third 10%: 1.8x
> fourth: 1.6x
> fifth: 1.5x
> sixth: 1.4x
> seventh: 1.3x
> eight: 1.2x
> ninth: 1.1x
> last 10%: 1x
>
> you can ask for refunds anytime, but if you participate again your burn will be considered as a new burn and your allocation multiplier will reflect the percentile it enters

[Source](https://x.com/xbt2027/status/2049516159586709785)

### Direct clarifications from @xbt2027 (May 4-5, 2026)

> **multi tx :** each transaction gets the multiplier of the tranche it fits in
>
> **partial refund :** i didn't see a partial refund yet but resets position completely
>
> **events :** each allocation event allocates 3% for SOL. 5 events allocate a total of 15%, so this particular event allocated 3%

## Implemented rules

### Tranche assignment

Within a single allocation event :

1. All valid burn transactions are ordered chronologically by their on-chain confirmation timestamp.
2. The full ordered list is split into **10 equal-size tranches** based on transaction count.
3. Each transaction inherits the multiplier of the tranche it falls into :

| Tranche | Multiplier |
| ------- | ---------- |
| 1st 10% | 2.4x       |
| 2nd 10% | 2.0x       |
| 3rd 10% | 1.8x       |
| 4th 10% | 1.6x       |
| 5th 10% | 1.5x       |
| 6th 10% | 1.4x       |
| 7th 10% | 1.3x       |
| 8th 10% | 1.2x       |
| 9th 10% | 1.1x       |
| 10th    | 1.0x       |

### Refunds

A refund is detected when an outgoing XBT transfer is observed from the refund address (`DWUFCjBxqDuXpUGF8KnVzhAuz2uhRyfrky4aFc2JvvgH`) to a wallet.

- Any refund triggered by a wallet **invalidates all prior burn transactions from that wallet** in the current event.
- If the wallet later burns again, the new transactions are appended at the tail of the queue with normal tranche assignment.

### Allocation per transaction

For a transaction `i` in the current event :

```
allocation_i = (amount_i × multiplier_i) / Σ_j (amount_j × multiplier_j) × event_share
```

Where `event_share = 3% of D17 total supply` for the current event.

## Open questions

- **Event closing trigger :** the conditions under which the current event closes (and a new one starts) have not been formally announced. The tool currently treats all valid burn transactions as belonging to the current event until further notice.

## Addresses

- **Burn address (Solana, XBT mint) :** `4Upb3WBoMSAaMC3eytHvSnL4hYLvDEL8zpQr4Q9U6JsB`
- **Refund address (Solana) :** `DWUFCjBxqDuXpUGF8KnVzhAuz2uhRyfrky4aFc2JvvgH` (send 1 XBT to receive 100% of your burned XBT back)
