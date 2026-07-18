import type { GameStats } from "@/lib/insights";

function pct(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${Math.round(v * 100)}%`;
}

function goldK(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${(v / 1000).toFixed(1)}k`;
}

/** 单局官方战绩面板：阵容 + KDA + 经济 + 输出 + MVP + 禁用 */
export default function GameStatsBoard({ stats }: { stats: GameStats }) {
  const camps = [1, 2] as const;
  const min = Math.floor(stats.duration_s / 60);
  const sec = stats.duration_s % 60;

  return (
    <div className="mb-5 rounded border border-border/50">
      {/* 局头：比分与时长 */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/40 px-4 py-2.5">
        <div className="flex flex-wrap items-center gap-2 text-[15px]">
          {camps.map((c, i) => {
            const t = stats.teams[String(c)];
            return (
              <span key={c} className="flex items-center gap-2">
                <span className={t?.win ? "font-semibold" : "text-muted"}>
                  {t?.name}
                  {t?.win && <span className="tag tag--accent ml-1.5">胜</span>}
                </span>
                <span className="font-mono">{t?.kills ?? "-"}</span>
                {i === 0 && <span className="text-faint">:</span>}
              </span>
            );
          })}
        </div>
        <span className="tag">
          时长 {min}:{String(sec).padStart(2, "0")}
        </span>
      </div>

      {/* 禁用 */}
      {stats.bans.length > 0 && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-border/30 px-4 py-2 text-xs text-muted">
          {camps.map((c) => (
            <span key={c} className="flex items-center gap-1.5">
              <span className="text-faint">{stats.teams[String(c)]?.name} 禁</span>
              {stats.bans
                .filter((b) => b.camp === c)
                .map((b, i) => (
                  <span key={i}>{b.hero}</span>
                ))
                .reduce<React.ReactNode[]>(
                  (acc, cur, i) => (i === 0 ? [cur] : [...acc, " / ", cur]),
                  [],
                )}
            </span>
          ))}
        </div>
      )}

      {/* 战绩表 */}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[460px] text-sm">
          <thead>
            <tr className="border-b border-border/30 text-left">
              <th className="tag px-4 py-1.5 font-normal">选手</th>
              <th className="tag py-1.5 font-normal">英雄</th>
              <th className="tag py-1.5 text-center font-normal">K / D / A</th>
              <th className="tag py-1.5 text-right font-normal">经济</th>
              <th className="tag py-1.5 text-right font-normal">输出</th>
              <th className="tag py-1.5 pr-4 text-right font-normal">参团</th>
            </tr>
          </thead>
          <tbody>
            {camps.map((c) =>
              stats.players
                .filter((p) => p.camp === c)
                .map((p, i) => (
                  <tr
                    key={`${c}-${p.player}`}
                    className={`${i === 0 && c === 2 ? "border-t-2 border-border/40" : "border-t border-border/20"}`}
                  >
                    <td className="px-4 py-1.5">
                      <span className="font-medium">{p.player}</span>
                      {p.mvp && <span className="seal-ai ml-1.5">MVP</span>}
                    </td>
                    <td className="py-1.5">
                      <span className="flex items-center gap-1.5">
                        {p.hero_icon && (
                          /* eslint-disable-next-line @next/next/no-img-element */
                          <img
                            src={p.hero_icon}
                            alt={p.hero}
                            className="h-5 w-5 rounded-full border border-border/40"
                          />
                        )}
                        <span className="text-muted">{p.hero}</span>
                      </span>
                    </td>
                    <td className="py-1.5 text-center font-mono">
                      {p.k}/{p.d}/{p.a}
                    </td>
                    <td className="py-1.5 text-right font-mono">{goldK(p.gold)}</td>
                    <td className="py-1.5 text-right font-mono">{pct(p.hurt_rate)}</td>
                    <td className="py-1.5 pr-4 text-right font-mono">{pct(p.participation)}</td>
                  </tr>
                )),
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
