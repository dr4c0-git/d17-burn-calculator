# D17 Burn Calculator

A free, open-source tool that helps XBT holders estimate their D17 allocation when burning XBT.

Built around the official mechanics announced by [@xbt2027](https://x.com/xbt2027) on April 29, 2026.

> ⚠️ The @xbt2027 project moves fast. The mechanics implemented here reflect the state as of the latest verified tweets. **Always verify the current rules directly on the [@xbt2027 profile](https://x.com/xbt2027) before acting.**

## Mechanics implemented

- **Per-transaction multiplier.** Each individual burn transaction is assigned to a tranche based on its chronological position among all valid burn transactions in the current allocation event.
- **10 equal-size tranches.** Multipliers : `[2.4, 2.0, 1.8, 1.6, 1.5, 1.4, 1.3, 1.2, 1.1, 1.0]`.
- **Refunds reset position.** Any refund (even partial) invalidates all prior burn transactions from the refunding sender. New burns enter the queue at the current tail.
- **5 events × 3% each.** The 15% allocation reserved for XBT burners is split across 5 successive allocation events of 3% each. This calculator targets the **current event**.

See [`docs/mechanics.md`](./docs/mechanics.md) for the full reference and source tweets.

## Stack

- **Frontend** : Vite + React + TypeScript + Tailwind CSS
- **Backend** : FastAPI + Python (httpx, sqlite)
- **Solana indexing** : [Helius RPC](https://helius.xyz)
- **Hosting** : Cloudflare Pages (frontend), Railway (backend)

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

## Live

- **App** : https://d17-burn-calculator.pages.dev
- **API** : https://d17-burn-calculator-api.onrender.com (Swagger : `/docs`)

The backend runs on a free tier with cold starts after ~15 min of
inactivity ; the first request after a sleep can take 30-60 s.

## Contributing

Contributions welcome. Open an issue or PR.

## Credits

Built by [@__dr4c0__](https://x.com/__dr4c0__) as part of the D17 contributor effort.
The mechanics, vision, and entire system are designed by [@xbt2027](https://x.com/xbt2027).

## License

MIT

