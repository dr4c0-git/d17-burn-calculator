// Thin client over the FastAPI backend.
// Configure VITE_API_BASE in the .env files (different per env).

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export interface State {
  total_burns: number;
  total_xbt_burned: number;
  last_indexed_at: string | null;
  burn_address: string;
  refund_address: string;
  multipliers: number[];
  event_share_pct: number;
  event_allocation_tokens: number;
  d17_total_supply: number;
}

export interface SimulateResult {
  your_position: number;
  total_after_you: number;
  your_tranche: number;
  your_multiplier: number;
  your_allocation_pct: number;
  your_allocation_tokens: number;
  note: string;
}

export async function fetchState(): Promise<State> {
  const r = await fetch(`${API_BASE}/state`);
  if (!r.ok) throw new Error(`/state failed: ${r.status}`);
  return r.json();
}

export async function simulate(
  amount: number,
  extraBurnsAfter: number,
): Promise<SimulateResult> {
  const r = await fetch(`${API_BASE}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ amount, extra_burns_after: extraBurnsAfter }),
  });
  if (!r.ok) throw new Error(`/simulate failed: ${r.status}`);
  return r.json();
}
