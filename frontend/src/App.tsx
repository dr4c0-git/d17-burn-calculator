import { useEffect, useState } from "react";
import { fetchState, simulate, State, SimulateResult } from "./lib/api";
import { TrancheBar } from "./components/TrancheBar";
import { Docs } from "./components/Docs";

type View = "calculator" | "docs";

export default function App() {
  const [view, setView] = useState<View>("calculator");

  const [state, setState] = useState<State | null>(null);
  const [stateError, setStateError] = useState<string | null>(null);

  const [amount, setAmount] = useState<string>("");
  const [extra, setExtra] = useState<string>("0");
  const [result, setResult] = useState<SimulateResult | null>(null);
  const [simError, setSimError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [refreshing, setRefreshing] = useState(false);
  const [lastFetchedAt, setLastFetchedAt] = useState<number>(Date.now());
  const [tick, setTick] = useState(0);

  async function refresh() {
    setRefreshing(true);
    try {
      const s = await fetchState();
      setState(s);
      setStateError(null);
      setLastFetchedAt(Date.now());
    } catch (e: unknown) {
      setStateError((e as Error).message);
    } finally {
      setRefreshing(false);
    }
  }

  // Live state polling.
  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 30_000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Tick every second so the "X s ago" label updates without re-fetching.
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const ago = Math.max(0, Math.floor((Date.now() - lastFetchedAt) / 1000));
  void tick;

  async function onSimulate(e: React.FormEvent) {
    e.preventDefault();
    setSimError(null);
    setResult(null);
    const a = Number(amount);
    const x = Number(extra);
    if (!Number.isFinite(a) || a <= 0) {
      setSimError("Enter a positive XBT amount.");
      return;
    }
    if (!Number.isFinite(x) || x < 0) {
      setSimError("Extra burns must be 0 or more.");
      return;
    }
    setLoading(true);
    try {
      const r = await simulate(a, Math.floor(x));
      setResult(r);
    } catch (err: unknown) {
      setSimError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex flex-col">
      <header className="px-6 py-10 border-b border-white/10">
        <div className="max-w-4xl mx-auto">
          <h1 className="font-serif italic font-bold text-5xl tracking-wide text-glow">
            D17 Burn Calculator
          </h1>
          <p className="mt-3 text-white/70 max-w-2xl">
            Estimate your D17 allocation when burning XBT. Built around the
            official mechanics from{" "}
            <a
              href="https://x.com/xbt2027"
              className="underline decoration-dotted hover:text-white"
              target="_blank"
              rel="noreferrer"
            >
              @xbt2027
            </a>
            .
          </p>
          <nav className="mt-6 flex gap-2 text-sm">
            <NavTab active={view === "calculator"} onClick={() => setView("calculator")}>
              Calculator
            </NavTab>
            <NavTab active={view === "docs"} onClick={() => setView("docs")}>
              How it works
            </NavTab>
          </nav>
        </div>
      </header>

      <div className="flex-1">
        {view === "docs" ? (
          <Docs />
        ) : (
          <>
            {/* Live state panel */}
            <section className="px-6 py-8 border-b border-white/10">
              <div className="max-w-4xl mx-auto space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm uppercase tracking-widest text-white/50">
                    Current event
                  </h2>
                  <div className="flex items-center gap-3 text-xs text-white/50">
                    <span>updated {ago < 5 ? "just now" : `${ago}s ago`}</span>
                    <button
                      type="button"
                      onClick={refresh}
                      disabled={refreshing}
                      className="px-2 py-1 rounded border border-white/15 hover:border-white/40 disabled:opacity-50"
                      title="Force a refresh from the indexer"
                    >
                      {refreshing ? "refreshing…" : "refresh"}
                    </button>
                  </div>
                </div>
                {stateError && (
                  <p className="text-red-400 text-sm">
                    Could not load state : {stateError}
                  </p>
                )}
                {state && (
                  <>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <Stat
                        label="Burn transactions"
                        value={state.total_burns.toLocaleString()}
                      />
                      <Stat
                        label="XBT burned"
                        value={state.total_xbt_burned.toLocaleString(undefined, {
                          maximumFractionDigits: 0,
                        })}
                      />
                      <Stat
                        label="Event allocation"
                        value={`${state.event_allocation_tokens.toLocaleString()} D17 (${state.event_share_pct}%)`}
                      />
                    </div>
                    <TrancheBar activeTranche={result?.your_tranche} />
                    <p className="text-xs text-white/40">
                      Last indexed :{" "}
                      {state.last_indexed_at
                        ? new Date(state.last_indexed_at).toLocaleString()
                        : "—"}
                    </p>
                  </>
                )}
              </div>
            </section>

            {/* Calculator form + result */}
            <section className="px-6 py-10">
              <div className="max-w-4xl mx-auto">
                <h2 className="text-sm uppercase tracking-widest text-white/50 mb-4">
                  Simulate your burn
                </h2>
                <form
                  onSubmit={onSimulate}
                  className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end"
                >
                  <Field label="XBT amount to burn">
                    <input
                      inputMode="decimal"
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                      placeholder="e.g. 100000"
                      className="w-full bg-white/5 border border-white/10 rounded-md px-3 py-2 outline-none focus:border-glow"
                    />
                  </Field>
                  <Field label="Extra burns expected after you">
                    <input
                      inputMode="numeric"
                      value={extra}
                      onChange={(e) => setExtra(e.target.value)}
                      placeholder="0"
                      className="w-full bg-white/5 border border-white/10 rounded-md px-3 py-2 outline-none focus:border-glow"
                    />
                  </Field>
                  <button
                    type="submit"
                    disabled={loading}
                    className="bg-white text-black font-medium px-4 py-2 rounded-md hover:bg-white/90 disabled:opacity-50"
                  >
                    {loading ? "Computing…" : "Calculate"}
                  </button>
                </form>
                <div className="mt-2 space-y-1 text-xs text-white/40">
                  <p>
                    Not sure what "Extra burns expected after you" means ?{" "}
                    <button
                      type="button"
                      onClick={() => setView("docs")}
                      className="underline decoration-dotted hover:text-white"
                    >
                      See How it works
                    </button>
                    .
                  </p>
                  <p>
                    This calculator simulates a <strong>new</strong> burn. Your
                    existing on-chain burns are already counted in the live state
                    above, but they don't pre-fill this form.
                  </p>
                </div>
                {simError && <p className="mt-4 text-red-400 text-sm">{simError}</p>}

                {result && (
                  <div className="mt-8 box-glow rounded-xl p-6 bg-white/[0.02] space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <Stat label="Your position" value={`#${result.your_position}`} />
                      <Stat
                        label="Your tranche"
                        value={`${result.your_tranche} / 10`}
                      />
                      <Stat
                        label="Your multiplier"
                        value={`${result.your_multiplier.toFixed(1)}x`}
                      />
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <Stat
                        label="Estimated D17 (tokens)"
                        value={result.your_allocation_tokens.toLocaleString(undefined, {
                          maximumFractionDigits: 0,
                        })}
                        large
                      />
                      <Stat
                        label="Estimated D17 (% of supply)"
                        value={`${result.your_allocation_pct.toFixed(4)}%`}
                        large
                      />
                    </div>
                    <p className="text-xs text-white/50">{result.note}</p>
                  </div>
                )}
              </div>
            </section>
          </>
        )}
      </div>

      <footer className="px-6 py-6 border-t border-white/10 text-xs text-white/40">
        <div className="max-w-4xl mx-auto flex flex-wrap gap-x-6 gap-y-2 justify-between">
          <span>
            Built by{" "}
            <a
              href="https://x.com/__dr4c0__"
              target="_blank"
              rel="noreferrer"
              className="underline decoration-dotted hover:text-white"
            >
              @__dr4c0__
            </a>{" "}
            · Mechanics by{" "}
            <a
              href="https://x.com/xbt2027"
              target="_blank"
              rel="noreferrer"
              className="underline decoration-dotted hover:text-white"
            >
              @xbt2027
            </a>
          </span>
          <span>
            <a
              href="https://github.com/dr4c0-git/d17-burn-calculator"
              target="_blank"
              rel="noreferrer"
              className="underline decoration-dotted hover:text-white"
            >
              Open-source on GitHub
            </a>
            {" "}· Always verify on{" "}
            <a
              href="https://x.com/xbt2027"
              target="_blank"
              rel="noreferrer"
              className="underline decoration-dotted hover:text-white"
            >
              the official profile
            </a>
            .
          </span>
        </div>
      </footer>
    </main>
  );
}

function NavTab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "px-4 py-2 rounded-md border transition-colors",
        active
          ? "border-glow bg-glow/15 text-white text-glow"
          : "border-white/10 bg-white/[0.03] text-white/60 hover:text-white",
      ].join(" ")}
    >
      {children}
    </button>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="text-xs uppercase tracking-widest text-white/50 mb-1">
        {label}
      </div>
      {children}
    </label>
  );
}

function Stat({
  label,
  value,
  large = false,
}: {
  label: string;
  value: string;
  large?: boolean;
}) {
  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-lg px-4 py-3">
      <div className="text-[11px] uppercase tracking-widest text-white/50">
        {label}
      </div>
      <div
        className={
          large
            ? "font-serif italic font-bold text-3xl mt-1 text-glow"
            : "font-serif italic font-bold text-2xl mt-1"
        }
      >
        {value}
      </div>
    </div>
  );
}
