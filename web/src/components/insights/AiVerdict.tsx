import Link from "next/link";
import type { MatchAggregate } from "@/lib/insights";

function ConsensusTag({ consensus }: { consensus: string }) {
  if (consensus === "存在分歧") return <span className="seal-ai">{consensus}</span>;
  if (consensus === "一致好评") return <span className="tag tag--accent">{consensus}</span>;
  if (consensus === "一致差评") return <span className="tag text-seal">{consensus}</span>;
  return <span className="tag">{consensus}</span>;
}

/** AI 综合评：汇总全部解说观点后的醒目整体评价（deepseek-reasoner 生成） */
export default function AiVerdict({ aggregate }: { aggregate: MatchAggregate }) {
  return (
    <div className="plate p-6 md:p-9">
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <p className="tag tag--accent">AI 综合评</p>
        <span className="tag">综合 {aggregate.caster_count} 位解说观点</span>
        <span className="seal-ai">AI 生成</span>
      </div>

      {aggregate.headline && (
        <p className="mb-4 text-xl font-semibold leading-snug md:text-2xl">
          {aggregate.headline}
        </p>
      )}
      {aggregate.overall && (
        <p className="mb-6 text-[15px] leading-loose text-muted">{aggregate.overall}</p>
      )}

      {/* BP 思路与节奏：按观赛逻辑放最前 */}
      {(aggregate.bp_read || aggregate.pace) && (
        <div className="mb-6 grid gap-4 md:grid-cols-2">
          {aggregate.bp_read && (
            <div className="rounded border border-border/50 p-4">
              <p className="tag tag--accent mb-2">BP 怎么看</p>
              <p className="text-[15px] leading-loose">{aggregate.bp_read}</p>
            </div>
          )}
          {aggregate.pace && (
            <div className="rounded border border-border/50 p-4">
              <p className="tag tag--accent mb-2">节奏怎么走</p>
              <p className="text-[15px] leading-loose">{aggregate.pace}</p>
            </div>
          )}
        </div>
      )}

      {/* 两队综合评：醒目大块 */}
      {aggregate.teams.length > 0 && (
        <div className="mb-6 grid gap-4 md:grid-cols-2">
          {aggregate.teams.map((t) => (
            <div key={t.name} className="rounded border border-border/50 p-4">
              <div className="mb-2 flex flex-wrap items-center gap-2.5">
                <span className="text-lg font-semibold tracking-wide">{t.name}</span>
                <ConsensusTag consensus={t.consensus} />
              </div>
              <p className="text-[15px] leading-loose">{t.text}</p>
            </div>
          ))}
        </div>
      )}

      {/* 选手综合评 */}
      {aggregate.players.length > 0 && (
        <div className="grid gap-3 md:grid-cols-2">
          {aggregate.players.map((p) => (
            <div key={p.name} className="rounded border border-border/40 p-3.5">
              <div className="mb-1.5 flex flex-wrap items-center gap-2">
                <Link
                  href={`/players/${encodeURIComponent(p.name)}`}
                  className="font-semibold underline-offset-4 hover:underline"
                >
                  {p.name}
                </Link>
                <ConsensusTag consensus={p.consensus} />
              </div>
              <p className="text-sm leading-relaxed text-muted">{p.text}</p>
            </div>
          ))}
        </div>
      )}

      {aggregate.controversy && (
        <p className="mt-5 text-[15px]">
          <span className="seal-ai mr-2">最大争议</span>
          <span className="text-muted">{aggregate.controversy}</span>
        </p>
      )}
    </div>
  );
}
