import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchMatchInsights } from "@/lib/insights";
import UpOpinionCard from "@/components/insights/UpOpinionCard";
import AiVerdict from "@/components/insights/AiVerdict";
import Ornament from "@/components/Ornament";

export const dynamic = "force-dynamic";

function fmtTime(iso: string | null): string {
  // 库里的 start_time 数值本身就是北京时间（官方接口原样入库），
  // 只是带了 +00:00 后缀——直接按字面量取，不做时区换算
  if (!iso) return "时间待定";
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
  if (!m) return iso;
  return `${Number(m[2])}月${Number(m[3])}日 ${m[4]}:${m[5]}`;
}

export default async function MatchDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { match, teams, opinions, aggregate } = await fetchMatchInsights(id);
  if (!match) notFound();

  const t1 = match.team1_id ? teams[match.team1_id] : null;
  const t2 = match.team2_id ? teams[match.team2_id] : null;
  const finished = match.status === 2;

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

        {aggregate && (
          <div className="mb-6">
            <AiVerdict aggregate={aggregate} />
          </div>
        )}

        {opinions.length === 0 ? (
          <div className="plate p-10 text-center">
            <p className="text-[15px] leading-loose text-muted">
              这场比赛的二路解说观点还没上架。
              <br />
              完赛后我们会自动分析各家二路视频，稍后再来看看。
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {opinions.map((o) => (
              <UpOpinionCard key={o.vod.id} opinion={o} />
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
