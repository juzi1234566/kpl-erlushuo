import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchMatchInsights } from "@/lib/insights";
import UpOpinionCard from "@/components/insights/UpOpinionCard";
import Ornament from "@/components/Ornament";

export const dynamic = "force-dynamic";

function fmtTime(iso: string | null): string {
  if (!iso) return "时间待定";
  const d = new Date(iso);
  return d.toLocaleString("zh-CN", {
    timeZone: "Asia/Shanghai",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default async function MatchDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { match, teams, vods, insightsByVod } = await fetchMatchInsights(id);
  if (!match) notFound();

  const t1 = match.team1_id ? teams[match.team1_id] : null;
  const t2 = match.team2_id ? teams[match.team2_id] : null;
  const finished = match.status === 2;
  const vodsWithInsights = vods.filter((v) => (insightsByVod[v.id] || []).length > 0);

  return (
    <div className="space-y-14">
      <Link
        href="/matches"
        className="tag enter inline-block transition-colors duration-500 hover:text-foreground"
      >
        ← 返回赛程
      </Link>

      {/* 比赛头部 */}
      <header className="plate enter-1 px-6 py-12 text-center md:px-12">
        <p className="tag tag--accent mb-6">
          {match.stage_desc || match.stage_name || "2026 夏季赛"} · {fmtTime(match.start_time)}
        </p>
        <div className="flex items-center justify-center gap-6 md:gap-10">
          <span className="text-2xl tracking-wider md:text-3xl">{t1?.name || "待定"}</span>
          <span className="text-3xl tracking-[0.2em] md:text-4xl">
            {finished ? `${match.score1 ?? "-"} : ${match.score2 ?? "-"}` : "对阵"}
          </span>
          <span className="text-2xl tracking-wider md:text-3xl">{t2?.name || "待定"}</span>
        </div>
        <p className="tag mt-6">{finished ? "已完赛" : "未开始"}</p>
      </header>

      {/* 二路观点 */}
      <section className="enter-2">
        <div className="mb-8 text-center">
          <p className="tag tag--accent mb-3">这场比赛，二路怎么说</p>
          <h2 className="text-2xl tracking-[0.15em]">解说观点</h2>
          <div className="mt-6 flex justify-center">
            <Ornament className="breathe" />
          </div>
        </div>

        {vodsWithInsights.length === 0 ? (
          <div className="plate p-10 text-center">
            <p className="text-[15px] leading-loose text-muted">
              这场比赛的二路解说观点还没上架。
              <br />
              完赛后我们会自动分析各家二路视频，稍后再来看看。
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {vodsWithInsights.map((v) => (
              <UpOpinionCard key={v.id} vod={v} insights={insightsByVod[v.id] || []} />
            ))}
          </div>
        )}

        <p className="mx-auto mt-8 max-w-xl text-center text-xs leading-loose text-faint">
          以上观点由 AI 自动提取自各 UP主 的公开解说视频，引用归属原作者，
          点击时间戳可跳转 B站 原视频对应位置。AI 转述可能有误，以原视频为准。
        </p>
      </section>
    </div>
  );
}
