// Public ranked allocations table.
// Aggregates per wallet, sorted by projected D17 allocation desc.

import { useEffect, useMemo, useState } from "react";
import { Allocation, fetchAllocations } from "../lib/api";

type Props = {
  /** Notifies the parent so it can reset the highlighted-tranche bar. */
  onTrancheBarReset?: () => void;
};

export function Allocations({ onTrancheBarReset }: Props) {
  const [rows, setRows] = useState<Allocation[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [copied, setCopied] = useState<string | null>(null);

  // The shared TrancheBar in the parent reads from the simulator result,
  // which doesn't apply on this view — clear it once when we mount.
  useEffect(() => {
    onTrancheBarReset?.();
  }, [onTrancheBarReset]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAllocations();
      setRows(data);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 60_000);
    return () => clearInterval(id);
  }, []);

  const filtered = useMemo(() => {
    if (!rows) return [];
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => r.wallet.toLowerCase().includes(q));
  }, [rows, query]);

  function copy(wallet: string) {
    navigator.clipboard.writeText(wallet).then(() => {
      setCopied(wallet);
      setTimeout(() => setCopied((c) => (c === wallet ? null : c)), 1500);
    });
  }

  const totalAllocated = rows?.reduce((s, r) => s + r.allocation_tokens, 0) ?? 0;
  const totalBurned = rows?.reduce((s, r) => s + r.total_burned, 0) ?? 0;

  return (
    <section className="px-6 py-8">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-baseline justify-between gap-4 flex-wrap">
          <h2 className="text-sm uppercase tracking-widest text-white/50">
            Current allocations
          </h2>
          {rows && (
            <span className="text-xs text-white/40">
              {rows.length.toLocaleString()} wallets · {totalBurned.toLocaleString(undefined, { maximumFractionDigits: 0 })} XBT burned · {totalAllocated.toLocaleString(undefined, { maximumFractionDigits: 0 })} D17 allocated
            </span>
          )}
        </div>

        <p className="text-sm text-white/60">
          Live ranked table of every burner and their projected D17 allocation
          for the current event. Numbers shift as new burns and refunds land.
          The total across all wallets equals the event share (
          <strong>30,000,000 D17</strong>) by construction.
        </p>

        {/* Search */}
        <div className="relative">
          <input
            type="text"
            inputMode="search"
            placeholder="Search by wallet address (paste any portion)…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-md pl-3 pr-10 py-2 text-sm outline-none focus:border-glow"
          />
          {query && (
            <button
              onClick={() => setQuery("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-white/40 hover:text-white text-sm"
              aria-label="Clear search"
            >
              ×
            </button>
          )}
        </div>

        {error && (
          <p className="text-red-400 text-sm">Could not load allocations : {error}</p>
        )}
        {loading && !rows && <p className="text-white/50 text-sm">Loading…</p>}

        {rows && (
          <>
            {filtered.length === 0 && (
              <p className="text-white/50 text-sm py-8 text-center">
                No wallet matches “{query}”.
              </p>
            )}

            {filtered.length > 0 && (
              <div className="overflow-x-auto rounded-lg border border-white/10">
                <table className="w-full text-sm">
                  <thead className="bg-white/[0.03] text-white/50 text-xs uppercase tracking-wider">
                    <tr>
                      <th className="text-left px-3 py-2">#</th>
                      <th className="text-left px-3 py-2">Wallet</th>
                      <th className="text-right px-3 py-2">Burns</th>
                      <th className="text-right px-3 py-2">XBT burned</th>
                      <th className="text-left px-3 py-2">Tranches</th>
                      <th className="text-right px-3 py-2">D17 allocation</th>
                      <th className="text-right px-3 py-2">% of event</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {filtered.map((r) => (
                      <tr key={r.wallet} className="hover:bg-white/[0.02]">
                        <td className="px-3 py-2 font-serif italic text-white/70">
                          {r.rank}
                        </td>
                        <td className="px-3 py-2">
                          <button
                            onClick={() => copy(r.wallet)}
                            className="font-mono text-xs text-white/80 hover:text-white inline-flex items-center gap-2 group"
                            title="Click to copy"
                          >
                            <span>
                              {r.wallet.slice(0, 6)}…{r.wallet.slice(-6)}
                            </span>
                            <span
                              className={[
                                "text-[10px] px-1.5 py-0.5 rounded transition-opacity",
                                copied === r.wallet
                                  ? "bg-glow/30 text-white opacity-100"
                                  : "bg-white/5 text-white/40 opacity-0 group-hover:opacity-100",
                              ].join(" ")}
                            >
                              {copied === r.wallet ? "copied" : "copy"}
                            </span>
                          </button>
                          <a
                            href={`https://solscan.io/account/${r.wallet}`}
                            target="_blank"
                            rel="noreferrer"
                            className="ml-2 text-[10px] text-white/30 hover:text-white/70 underline decoration-dotted"
                            title="View on Solscan"
                          >
                            solscan ↗
                          </a>
                        </td>
                        <td className="px-3 py-2 text-right text-white/70">
                          {r.tx_count}
                        </td>
                        <td className="px-3 py-2 text-right tabular-nums">
                          {r.total_burned.toLocaleString(undefined, {
                            maximumFractionDigits: 0,
                          })}
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex flex-wrap gap-1">
                            {r.tranches.map((t) => (
                              <span
                                key={t}
                                className={[
                                  "text-[10px] px-1.5 py-0.5 rounded",
                                  t <= 3
                                    ? "bg-glow/25 text-white"
                                    : "bg-white/5 text-white/50",
                                ].join(" ")}
                                title={`Tranche ${t}`}
                              >
                                T{t}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="px-3 py-2 text-right tabular-nums font-serif italic font-bold">
                          {r.allocation_tokens.toLocaleString(undefined, {
                            maximumFractionDigits: 0,
                          })}
                        </td>
                        <td className="px-3 py-2 text-right text-white/60 tabular-nums">
                          {r.allocation_pct_of_event.toFixed(2)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        <p className="text-xs text-white/40">
          Rankings refresh automatically every minute. New burns can shift
          tranche boundaries and allocations across the whole table.
        </p>
      </div>
    </section>
  );
}
