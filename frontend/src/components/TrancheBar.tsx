// 10-segment tranche bar showing the multiplier ladder.
// Highlights the user's current projected tranche.

const MULTIPLIERS = [2.4, 2.0, 1.8, 1.6, 1.5, 1.4, 1.3, 1.2, 1.1, 1.0];

export function TrancheBar({ activeTranche }: { activeTranche?: number }) {
  return (
    <div className="grid grid-cols-10 gap-1 text-center text-xs">
      {MULTIPLIERS.map((m, i) => {
        const idx = i + 1;
        const active = activeTranche === idx;
        return (
          <div
            key={idx}
            className={[
              "rounded-md py-2 border transition-colors",
              active
                ? "border-glow bg-glow/20 text-white text-glow"
                : "border-white/10 bg-white/[0.03] text-white/60",
            ].join(" ")}
          >
            <div className="font-serif italic font-bold text-base">{m}x</div>
            <div className="opacity-60">tranche {idx}</div>
          </div>
        );
      })}
    </div>
  );
}
