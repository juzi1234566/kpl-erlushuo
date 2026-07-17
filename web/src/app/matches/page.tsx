import { readFile } from "fs/promises";
import path from "path";

type Summary = {
  league_id: string;
  match_count: number;
  finished: number;
  matches: Array<{
    match_id: string;
    status: number;
    start_time: string;
    score: string;
    teams: string[];
  }>;
};

async function loadSummary(): Promise<Summary | null> {
  try {
    const p = path.join(process.cwd(), "..", "pipeline", "data", "raw", "summary_20260003.json");
    const raw = await readFile(p, "utf-8");
    return JSON.parse(raw) as Summary;
  } catch {
    return null;
  }
}

export default async function MatchesPage() {
  const summary = await loadSummary();

  return (
    <div className="space-y-10">
      <header className="enter">
        <p className="hud-label mb-3 flex items-center gap-3">
          <span className="dot-live" />
          Season 2026 · Summer
        </p>
        <h1 className="text-3xl font-extralight tracking-wide">夏季赛赛程</h1>
        <p className="mt-3 text-xs text-faint">数据来自官方 leaguesite 开放接口</p>
      </header>

      {!summary ? (
        <div className="card enter-1 p-8">
          <p className="hud-label mb-4">No Local Cache</p>
          <p className="mb-4 text-sm text-muted">还没有本地赛程缓存，先跑回填脚本：</p>
          <pre className="overflow-x-auto rounded border border-border bg-black/30 p-4 text-xs leading-relaxed text-muted">
            {`cd pipeline
pip install -r requirements.txt
python -m scripts.backfill_league --league-id 20260003 --out data/raw --with-signals`}
          </pre>
        </div>
      ) : (
        <>
          <div className="enter-1">
            <div className="hairline mb-8" />
            <div className="grid grid-cols-3 gap-8">
              <div>
                <div className="text-3xl font-extralight tracking-wider">
                  {summary.match_count}
                </div>
                <div className="hud-label mt-2">总场次</div>
              </div>
              <div>
                <div className="text-3xl font-extralight tracking-wider">{summary.finished}</div>
                <div className="hud-label mt-2">已完赛</div>
              </div>
              <div>
                <div className="text-3xl font-extralight tracking-wider">
                  {summary.match_count - summary.finished}
                </div>
                <div className="hud-label mt-2">待打</div>
              </div>
            </div>
            <div className="hairline mt-8" />
          </div>

          <div className="enter-2 space-y-px overflow-hidden rounded-md border border-border">
            {summary.matches.slice(0, 30).map((m) => (
              <div
                key={m.match_id}
                className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-card px-5 py-4 text-sm transition-colors duration-500 last:border-b-0 hover:bg-white/[0.03]"
              >
                <div className="flex items-center gap-4">
                  <span className="hud-label w-28 shrink-0">{m.start_time?.slice(5, 16)}</span>
                  <span className="font-light tracking-wide">
                    {m.teams?.[0] || "—"}
                    <span className="mx-3 text-faint">vs</span>
                    {m.teams?.[1] || "—"}
                  </span>
                </div>
                <div className="flex items-center gap-4 font-mono text-sm">
                  <span className={m.status === 2 ? "text-foreground" : "text-faint"}>
                    {m.score}
                  </span>
                  {m.status === 2 ? (
                    <span className="hud-label hud-label--accent">Final</span>
                  ) : (
                    <span className="hud-label">Upcoming</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
