import Link from "next/link";
import { getSupabase } from "@/lib/supabase";

type Row = {
  id: string;
  team1_id: string | null;
  team2_id: string | null;
  score1: number | null;
  score2: number | null;
  status: number | null;
  start_time: string | null;
};

export const dynamic = "force-dynamic";

async function loadMatches(): Promise<Row[] | null> {
  const sb = getSupabase();
  if (!sb) return null;
  try {
    const { data } = await sb
      .from("matches")
      .select("id,team1_id,team2_id,score1,score2,status,start_time")
      .order("start_time", { ascending: false })
      .limit(60);
    return data || [];
  } catch {
    return null;
  }
}

async function loadTeamNames(rows: Row[]): Promise<Record<string, string>> {
  const sb = getSupabase();
  const names: Record<string, string> = {};
  const ids = [...new Set(rows.flatMap((r) => [r.team1_id, r.team2_id]).filter(Boolean))] as string[];
  if (!sb || !ids.length) return names;
  try {
    const { data } = await sb.from("teams").select("id,name").in("id", ids);
    for (const t of data || []) names[t.id] = t.name;
  } catch {
    /* ignore */
  }
  return names;
}

export default async function MatchesPage() {
  const rows = await loadMatches();
  const teamNames = rows?.length ? await loadTeamNames(rows) : {};

  const matchCount = rows?.length ?? 0;
  const finished = rows?.filter((r) => r.status === 2).length ?? 0;

  return (
    <div className="space-y-12">
      <header className="enter text-center">
        <p className="tag tag--accent mb-4">2026 夏季赛</p>
        <h1 className="text-3xl tracking-[0.15em]">赛程</h1>
        <p className="mt-4 text-xs text-faint">数据来自官方公开赛果</p>
      </header>

      {!rows || rows.length === 0 ? (
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
                <div className="text-3xl tracking-widest">{matchCount}</div>
                <div className="tag mt-3">总场次</div>
              </div>
              <div>
                <div className="text-3xl tracking-widest">{finished}</div>
                <div className="tag mt-3">已完赛</div>
              </div>
              <div>
                <div className="text-3xl tracking-widest">{matchCount - finished}</div>
                <div className="tag mt-3">未开始</div>
              </div>
            </div>
            <div className="hairline mt-9" />
          </div>

          <div className="plate enter-2">
            {rows.slice(0, 30).map((m, i) => {
              const t1 = m.team1_id ? teamNames[m.team1_id] : undefined;
              const t2 = m.team2_id ? teamNames[m.team2_id] : undefined;
              const row = (
                <>
                  <div className="flex items-baseline gap-5">
                    <span className="tag w-28 shrink-0">{m.start_time?.slice(5, 16)}</span>
                    <span className="tracking-wider">
                      {t1 || "待定"}
                      <span className="no mx-3 text-xs">对</span>
                      {t2 || "待定"}
                    </span>
                  </div>
                  <div className="flex items-baseline gap-5">
                    <span className={`tracking-[0.15em] ${m.status === 2 ? "" : "text-faint"}`}>
                      {m.status === 2 ? `${m.score1 ?? "-"} : ${m.score2 ?? "-"}` : ""}
                    </span>
                    <span className={`tag ${m.status === 2 ? "tag--accent" : ""}`}>
                      {m.status === 2 ? "看观点 →" : "未开始"}
                    </span>
                  </div>
                </>
              );
              const cls = `flex flex-wrap items-center justify-between gap-3 px-6 py-4 text-sm transition-colors duration-500 hover:bg-[rgba(47,122,125,0.07)] ${
                i > 0 ? "border-t border-border/30" : ""
              }`;
              return m.status === 2 ? (
                <Link key={m.id} href={`/matches/${m.id}`} className={cls}>
                  {row}
                </Link>
              ) : (
                <div key={m.id} className={cls}>
                  {row}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
