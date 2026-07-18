import type { DbCommentaryInsight, DbVodSource } from "@/lib/insights";
import { biliUrl, fmtTimestamp } from "@/lib/insights";

function SentimentTag({ sentiment }: { sentiment: string }) {
  const cls =
    sentiment === "好评"
      ? "tag tag--accent"
      : sentiment === "差评"
        ? "tag text-seal"
        : "tag";
  return <span className={cls}>{sentiment}</span>;
}

function Rating({ value }: { value: number | null }) {
  if (!value) return null;
  return (
    <span className="text-xs tracking-widest text-accent" aria-label={`评分 ${value} / 5`}>
      {"●".repeat(value)}
      {"○".repeat(5 - value)}
    </span>
  );
}

function QuoteLine({
  bvid,
  page,
  text,
  startMs,
}: {
  bvid: string;
  page: number | null;
  text: string;
  startMs: number;
}) {
  return (
    <p className="text-sm leading-relaxed text-muted">
      「{text}」
      <a
        href={biliUrl(bvid, startMs, page)}
        target="_blank"
        rel="noopener noreferrer"
        className="no ml-2 text-xs underline-offset-4 hover:underline"
      >
        [{fmtTimestamp(startMs)}]
      </a>
    </p>
  );
}

export default function UpOpinionCard({
  vod,
  insights,
}: {
  vod: DbVodSource;
  insights: DbCommentaryInsight[];
}) {
  const overall = insights.find((i) => i.subject_type === "overall");
  const teams = insights.filter((i) => i.subject_type === "team");
  const players = insights.filter((i) => i.subject_type === "player");

  return (
    <div className="plate p-6 md:p-8">
      {/* 头部：UP主 + 原视频 */}
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h3 className="text-lg tracking-wider">{vod.caster_name || vod.up_name || "二路解说"}</h3>
          <span className="seal-ai">AI 提取</span>
        </div>
        <a
          href={biliUrl(vod.bvid, undefined, vod.page_start)}
          target="_blank"
          rel="noopener noreferrer"
          className="tag tag--accent transition-colors duration-500 hover:text-foreground"
        >
          看原视频 →
        </a>
      </div>

      {/* 整体观感 */}
      {overall && (
        <div className="mb-6">
          <div className="mb-2 flex items-center gap-3">
            <SentimentTag sentiment={overall.sentiment} />
            <Rating value={overall.rating} />
          </div>
          <p className="text-[15px] leading-loose">{overall.summary}</p>
        </div>
      )}

      {/* 战队与选手评价 */}
      {[...teams, ...players].map((i) => (
        <div key={i.id} className="border-t border-border/30 py-4">
          <div className="mb-2 flex flex-wrap items-center gap-3">
            <span className="font-medium tracking-wide">{i.subject_name}</span>
            <SentimentTag sentiment={i.sentiment} />
            <Rating value={i.rating} />
          </div>
          <p className="mb-2 text-[15px] leading-relaxed text-muted">{i.summary}</p>
          {(i.quotes || []).map((q, idx) => (
            <QuoteLine
              key={idx}
              bvid={vod.bvid}
              page={vod.page_start}
              text={q.text}
              startMs={q.start_ms}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
