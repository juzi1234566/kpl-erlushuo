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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">2026 夏季赛赛程</h1>
        <p className="text-sm text-muted mt-1">
          数据来自官方 leaguesite 开放接口。先跑 pipeline 回填脚本生成本地 summary。
        </p>
      </div>

      {!summary ? (
        <div className="rounded-xl border border-border bg-card/40 p-6 text-sm text-muted">
          <p className="text-foreground font-medium mb-2">还没有本地赛程缓存</p>
          <pre className="whitespace-pre-wrap text-xs bg-black/30 p-3 rounded-lg overflow-x-auto">
            {`cd pipeline
pip install -r requirements.txt
python -m scripts.backfill_league --league-id 20260003 --out data/raw --with-signals`}
          </pre>
        </div>
      ) : (
        <>
          <p className="text-sm text-muted">
            league_id={summary.league_id} · 共 {summary.match_count} 场 · 已完赛{" "}
            {summary.finished}
          </p>
          <div className="space-y-2">
            {summary.matches.slice(0, 30).map((m) => (
              <div
                key={m.match_id}
                className="rounded-lg border border-border bg-card/40 px-4 py-3 flex flex-wrap items-center justify-between gap-2 text-sm"
              >
                <div>
                  <span className="text-muted mr-2">{m.start_time}</span>
                  <span className="font-medium">
                    {m.teams?.[0] || "?"} vs {m.teams?.[1] || "?"}
                  </span>
                </div>
                <div className="font-mono">
                  {m.score}
                  <span className="ml-2 text-xs text-muted">
                    {m.status === 2 ? "完赛" : `状态 ${m.status}`}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
