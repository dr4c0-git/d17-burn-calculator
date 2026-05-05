// Static docs page - explains what the tool does and how to read it.
// Aimed at first-time visitors who haven't followed every @xbt2027 tweet.

export function Docs() {
  return (
    <div className="prose-invert max-w-3xl mx-auto py-10 px-2 space-y-10 text-white/80">
      <section>
        <h2 className="font-serif italic text-3xl text-white text-glow mb-3">
          What is this ?
        </h2>
        <p>
          A free, open-source calculator for the{" "}
          <strong>D17 XBT burn allocation</strong>. You enter how much XBT you
          plan to burn, and the tool tells you what your projected D17 token
          allocation looks like under different scenarios.
        </p>
        <p>
          Built around the official mechanics announced by{" "}
          <a
            className="underline decoration-dotted hover:text-white"
            href="https://x.com/xbt2027"
            target="_blank"
            rel="noreferrer"
          >
            @xbt2027
          </a>
          . The mechanics in this tool reflect the latest verified tweets.{" "}
          <strong>Always cross-check on the official profile</strong> before
          acting on financial decisions.
        </p>
      </section>

      <section>
        <h2 className="font-serif italic text-3xl text-white text-glow mb-3">
          How the burn works
        </h2>
        <ol className="list-decimal list-inside space-y-2">
          <li>
            You burn XBT by sending it to the official burn address. Each
            transaction is recorded on-chain with a timestamp.
          </li>
          <li>
            At the end of the current allocation event, all valid burn
            transactions are <strong>ordered chronologically</strong> and
            divided into <strong>10 equal-size tranches</strong> by count.
          </li>
          <li>
            Each transaction inherits the multiplier of the tranche it falls
            into (earliest tranche = highest multiplier) :
          </li>
        </ol>
        <div className="grid grid-cols-5 sm:grid-cols-10 gap-1 text-center text-xs mt-4">
          {[2.4, 2.0, 1.8, 1.6, 1.5, 1.4, 1.3, 1.2, 1.1, 1.0].map((m, i) => (
            <div
              key={i}
              className="rounded-md py-2 border border-white/10 bg-white/[0.03]"
            >
              <div className="font-serif italic font-bold text-base text-white">
                {m}x
              </div>
              <div className="opacity-50">tranche {i + 1}</div>
            </div>
          ))}
        </div>
        <p className="mt-4">
          Your D17 allocation per transaction is :
        </p>
        <pre className="bg-black border border-white/10 rounded-md p-3 text-sm overflow-x-auto">
          {`allocation = (your_amount × your_multiplier)
             / total_weighted_volume
             × event_share`}
        </pre>
        <p>
          Where <code className="text-white">event_share = 30,000,000 D17</code>{" "}
          (3% of total supply) for the current event. There are{" "}
          <strong>5 successive events</strong>, so XBT burners receive 15% of
          D17 supply across all events.
        </p>
      </section>

      <section>
        <h2 className="font-serif italic text-3xl text-white text-glow mb-3">
          How to use this tool
        </h2>

        <h3 className="font-serif italic text-xl text-white mt-4 mb-1">
          Input 1 - XBT amount to burn
        </h3>
        <p>
          The amount of XBT you intend to send to the burn address. Whole
          numbers, no commas.
        </p>

        <h3 className="font-serif italic text-xl text-white mt-6 mb-1">
          Input 2 - Extra burns expected after you
        </h3>
        <p>
          This is the input that confuses people the most. Here's what it means :
        </p>
        <p>
          If you burn <em>right now</em>, you join at the back of the queue
          (you're the most recent burner). At this exact moment you'd be in
          the <strong>last</strong> tranche → multiplier 1.0x.
        </p>
        <p>
          But the event isn't over. <strong>More people will burn after you.</strong>
          Every new burn pushes you up the queue. So your <em>final</em> tranche
          depends on how many more burns happen between now and event close.
        </p>
        <p>
          This input lets you simulate that. Examples :
        </p>
        <ul className="list-disc list-inside space-y-1">
          <li>
            <code className="text-white">0</code> — pessimistic. No one burns
            after you. You stay in the last tranche (1.0x).
          </li>
          <li>
            <code className="text-white">100</code> — moderate. 100 more burns
            after yours. Your tranche moves up the queue.
          </li>
          <li>
            <code className="text-white">1000</code> — optimistic. 1,000 more
            burns. You'd land in one of the top tranches if you got in early.
          </li>
        </ul>
        <p>
          Run a few values to see the spread. The point isn't to predict the
          exact future — it's to understand the <em>sensitivity</em> of your
          position to event growth.
        </p>

        <h3 className="font-serif italic text-xl text-white mt-6 mb-1">
          Reading the result
        </h3>
        <ul className="list-disc list-inside space-y-1">
          <li>
            <strong>Your position</strong> — your rank if you burn now (1 = first to burn).
          </li>
          <li>
            <strong>Your tranche</strong> — which of the 10 tranches you fall
            into, given your position relative to the projected total.
          </li>
          <li>
            <strong>Your multiplier</strong> — the multiplier applied to your
            burn amount when computing your D17 share.
          </li>
          <li>
            <strong>Estimated D17 (tokens)</strong> — your projected absolute
            allocation in D17 tokens.
          </li>
          <li>
            <strong>Estimated D17 (% of supply)</strong> — same thing as a
            percentage of total D17 supply (1B).
          </li>
        </ul>
      </section>

      <section>
        <h2 className="font-serif italic text-3xl text-white text-glow mb-3">
          Important details
        </h2>
        <ul className="list-disc list-inside space-y-2">
          <li>
            <strong>Refunds reset your position completely.</strong> Even a
            partial refund invalidates all your prior burns in the current
            event. Re-burning afterwards puts you at the tail of the queue.
          </li>
          <li>
            <strong>Each tx counts independently.</strong> If you burn 3 times,
            each transaction gets its own multiplier based on its own
            position. Splitting a burn doesn't help or hurt by itself - what
            matters is when each tx hits the chain.
          </li>
          <li>
            <strong>Event closing trigger is not formalized yet.</strong> The
            current event remains open until @xbt2027 announces otherwise.
            All current burns are treated as belonging to event 1 of 5.
          </li>
          <li>
            <strong>Estimates assume future burns match current average.</strong>
            For a more accurate estimate, vary the "extra burns" input across
            scenarios.
          </li>
        </ul>
      </section>

      <section>
        <h2 className="font-serif italic text-3xl text-white text-glow mb-3">
          Sources
        </h2>
        <ul className="list-disc list-inside space-y-1">
          <li>
            <a
              className="underline decoration-dotted hover:text-white"
              href="https://x.com/xbt2027/status/2049515425122128352"
              target="_blank"
              rel="noreferrer"
            >
              The Plan - D17 (April 29, 2026, pinned)
            </a>
          </li>
          <li>
            <a
              className="underline decoration-dotted hover:text-white"
              href="https://x.com/xbt2027/status/2049516159586709785"
              target="_blank"
              rel="noreferrer"
            >
              XBT Burn mechanics (April 29, 2026)
            </a>
          </li>
          <li>
            Direct clarifications from @xbt2027 on multi-tx, partial refunds,
            and event structure (May 4-5, 2026).
          </li>
        </ul>
      </section>

      <section>
        <h2 className="font-serif italic text-3xl text-white text-glow mb-3">
          Disclaimer
        </h2>
        <p>
          This is a personal tool built by{" "}
          <a
            className="underline decoration-dotted hover:text-white"
            href="https://x.com/__dr4c0__"
            target="_blank"
            rel="noreferrer"
          >
            @__dr4c0__
          </a>{" "}
          as a contribution to the D17 ecosystem. It is not financial advice.
          Burns are irreversible without explicit refund. Always verify the
          rules and addresses on the official @xbt2027 profile before acting.
        </p>
      </section>
    </div>
  );
}
