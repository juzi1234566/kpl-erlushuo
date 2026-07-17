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
    <div className="space-y-12">
      <header className="enter text-center">
        <p className="tag tag--accent mb-4">2026 夏季赛</p>
        <h1 className="text-3xl tracking-[0.15em]">赛程</h1>
        <p className="mt-4 text-xs text-faint">数据来自官方公开赛果</p>
      </header>

      {!summary ? (
        <div className="plate enter-1 p-8 text-center">
          <p className="tag tag--accent mb-4">暂无赛程数据</p>
          <p className="text-[15px] leading-loose text-muted">
            数据管线尚未回填本地赛程，稍后再来看看。
          </p>
        </div>
      ) : (
        <>
          <div className="enter-1">
            <div className="hairline mb-9" />
            <div className="grid grid-cols-3 gap-8 text-center">
              <div>
                <div className="text-3xl tracking-widest">{summary.match_count}</div>
                <div className="tag mt-3">总场次</div>
              </div>
              <div>
                <div className="text-3xl tracking-widest">{summary.finished}</div>
                <div className="tag mt-3">已完赛</div>
              </div>
              <div>
                <div className="text-3xl tracking-widest">
                  {summary.match_count - summary.finished}
                </div>
                <div className="tag mt-3">未开始</div>
              </div>
            </div>
            <div className="hairline mt-9" />
          </div>

          <div className="plate enter-2">
            {summary.matches.slice(0, 30).map((m, i) => (
              <div
                key={m.match_id}
                className={`flex flex-wrap items-center justify-between gap-3 px-6 py-4 text-sm transition-colors duration-500 hover:bg-[rgba(47,122,125,0.07)] ${
                  i > 0 ? "border-t border-border/30" : ""
                }`}
              >
                <div className="flex items-baseline gap-5">
                  <span className="tag w-28 shrink-0">{m.start_time?.slice(5, 16)}</span>
                  <span className="tracking-wider">
                    {m.teams?.[0] || "待定"}
                    <span className="no mx-3 text-xs">对</span>
                    {m.teams?.[1] || "待定"}
                  </span>
                </div>
                <div className="flex items-baseline gap-5">
                  <span className={`tracking-[0.15em] ${m.status === 2 ? "" : "text-faint"}`}>
                    {m.score}
                  </span>
                  <span className={`tag ${m.status === 2 ? "tag--accent" : ""}`}>
                    {m.status === 2 ? "已完赛" : "未开始"}
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
