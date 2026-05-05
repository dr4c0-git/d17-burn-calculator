# D17 Burn Calculator

A free, open-source tool for the D17 ecosystem. Two views, one source of truth :

- **Calculator** : estimate your D17 allocation if you burn a given amount of XBT, under different volume scenarios.
- **Allocations** : live ranked table of every wallet that has burned, with their projected D17 allocation, tranches, and on-chain links.

Built around the official mechanics announced by [@xbt2027](https://x.com/xbt2027) on April 29, 2026.

> ⚠️ The @xbt2027 project moves fast. The mechanics implemented here reflect the state as of the latest verified tweets. **Always verify the current rules directly on the [@xbt2027 profile](https://x.com/xbt2027) before acting.**

## Live

- **App** : https://d17-burn-calculator.pages.dev
- **API** : https://d17-burn-calculator-api.onrender.com (Swagger : `/docs`)

The backend runs on a free tier with cold starts after ~15 min of
inactivity ; the first request after a sleep can take 30-60 s.

## Mechanics implemented

- **Per-transaction multiplier.** Each individual burn transaction is assigned to a tranche based on its chronological position among all valid burn transactions in the current allocation event.
- **10 equal-size tranches.** Multipliers : `[2.4, 2.0, 1.8, 1.6, 1.5, 1.4, 1.3, 1.2, 1.1, 1.0]`.
- **Refunds reset position.** Any refund (even partial) invalidates all prior burn transactions from the refunding sender. New burns enter the queue at the current tail.
- **5 events × 3% each.** The 15% allocation reserved for XBT burners is split across 5 successive allocation events of 3% each. This tool targets the **current event**.

See [`docs/mechanics.md`](./docs/mechanics.md) for the full reference and source tweets.

## API endpoints

| Endpoint | Description |
| -------- | ----------- |
| `GET /state` | Live indexing snapshot : total burns, XBT burned, event allocation. |
| `GET /allocations` | Per-wallet ranked allocation table (used by the Allocations view). |
| `POST /simulate` | Compute the projected tranche, multiplier, and D17 allocation for a hypothetical new burn. |

## Stack

- **Frontend** : Vite + React + TypeScript + Tailwind CSS
- **Backend** : FastAPI + Python (httpx, in-memory state)
- **Solana indexing** : [Helius RPC](https://helius.xyz) (ATA-based to capture every SPL transfer)
- **Hosting** : Cloudflare Pages (frontend), Render (backend)

## Local development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your HELIUS_API_KEY
uvicorn main:app --reload

# Frontend (in a second terminal)
cd frontend
npm install
npm run dev
```

## Contributing

Contributions welcome. Open an issue or PR.

## Credits

Built by [@__dr4c0__](https://x.com/__dr4c0__) as part of the D17 contributor effort.
The mechanics, vision, and entire system are designed by [@xbt2027](https://x.com/xbt2027).

## License

MIT
