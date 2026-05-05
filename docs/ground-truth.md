# Ground-truth allocation snapshot

Reference allocations shared by [@xbt2027](https://x.com/xbt2027) on May 5, 2026.

These allocations are computed against the current event :

- **Event allocation** : 30,000,000 D17 tokens (3% of 1B total supply)
- **Source** : direct snapshot from the team

The calculator's backend, when running against the same on-chain state, must reproduce this exact distribution. If our numbers diverge from this list, we have a bug.

## Top recipients (excerpt from the snapshot)

| Wallet                                            | Allocation |
| ------------------------------------------------- | ---------: |
| AVAKYWbH16aqkT6T4jjsmYFCGl3vpnzUn9ZcgPGWnReA      |  3,529,179 |
| 2ezfMTMFUNk8dQAZfC3BP7kpQvS4HjAF6CZ8ryOD63c4V     |  2,328,995 |
| 4Z r4y1h3pofPiKoH2V9syiUjlL5r9vMxX67Q3iydDwrB     |  2,259,460 |
| 7ajjAvuvzY9Lxttbyz4REmkwZZ3VShEZCuza2fVbMNjU      |  1,961,984 |

(Full list in the image attached on May 5, 2026.)

## Notes

- The top allocation (~3.5M tokens) is roughly **11.7%** of the per-event 30M cap.
- The tail goes down to single-digit hundreds of tokens (smallest visible : 261).
- Total recipients in this snapshot reflect the count of valid burn transactions in the current event.

## Use as test fixture

When the indexer is implemented, we'll store this list as `tests/fixtures/event1_allocations.json` and run a regression test : `compute_allocations(on_chain_state) == fixture`.
