import type { DbCommentaryInsight, DbVodSource, InsightQuote } from "@/lib/insights";
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

function TsLink({ bvid, page, ms }: { bvid: string; page: number | null; ms: number }) {
  return (
    <a
      href={biliUrl(bvid, ms, page)}
      target="_blank"
      rel="noopener noreferrer"
      className="no ml-2 text-xs underline-offset-4 hover:underline"
    >
      [{fmtTimestamp(ms)}]
    </a>
  );
}

function QuoteLine({
  bvid,
  page,
  quote,
}: {
  bvid: string;
  page: number | null;
  quote: InsightQuote;
}) {
  return (
    <p className="text-sm leading-relaxed text-muted">
      「{quote.text}」
      <TsLink bvid={bvid} page={page} ms={quote.start_ms} />
    </p>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <p className="tag tag--accent mb-3">{children}</p>;
}

export default function UpOpinionCard({
  vod,
  insights,
}: {
  vod: DbVodSource;
  insights: DbCommentaryInsight[];
}) {
  const get = (t: DbCommentaryInsight["subject_type"]) =>
    insights.find((i) => i.subject_type === t);
  const bp = get("bp");
  const flow = get("flow");
  const overall = get("overall");
  const blame = get("blame");
  const golden = get("golden");
  const teams = insights.filter((i) => i.subject_type === "team");
  const players = insights.filter((i) => i.subject_type === "player");
  const page = vod.page_start;

  return (
    <div className="plate p-6 md:p-9">
      {/* 头部 */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-border/40 pb-5">
        <div className="flex items-center gap-3">
          <h3 className="text-xl tracking-wider">{vod.caster_name || vod.up_name || "二路解说"}</h3>
          {overall && <SentimentTag sentiment={overall.sentiment} />}
          {overall && <Rating value={overall.rating} />}
          <span className="seal-ai">AI 提取</span>
        </div>
        <a
          href={biliUrl(vod.bvid, undefined, page)}
          target="_blank"
          rel="noopener noreferrer"
          className="tag tag--accent transition-colors duration-500 hover:text-foreground"
        >
          看原视频 →
        </a>
      </div>

      <div className="space-y-8">
        {/* BP 点评 + 预测 */}
        {bp && (
          <section>
            <div className="mb-3 flex items-center gap-3">
              <SectionTitle>BP 与阵容</SectionTitle>
              <Rating value={bp.rating} />
            </div>
            <p className="text-[15px] leading-loose">{bp.summary}</p>
            {(bp.extra?.predictions || []).length > 0 && (
              <div className="mt-4 space-y-2">
                {(bp.extra?.predictions || []).map((q, i) => (
                  <div key={i} className="flex flex-wrap items-baseline gap-2 text-sm">
                    {q.verdict && (
                      <span
                        className={
                          q.verdict === "打脸"
                            ? "seal-ai"
                            : q.verdict === "应验"
                              ? "tag tag--accent"
                              : "tag"
                        }
                      >
                        {q.verdict === "打脸" ? "毒奶打脸" : q.verdict === "应验" ? "预言应验" : "待验证"}
                      </span>
                    )}
                    <span className="text-muted">
                      「{q.text}」
                      <TsLink bvid={vod.bvid} page={page} ms={q.start_ms} />
                    </span>
                    {q.note && <span className="text-xs text-faint">{q.note}</span>}
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* 局势走向 */}
        {flow && (
          <section>
            <SectionTitle>局势走向</SectionTitle>
            <p className="whitespace-pre-line text-[15px] leading-loose">{flow.summary}</p>
            {(flow.extra?.turning_points || []).length > 0 && (
              <div className="mt-4 space-y-2">
                {(flow.extra?.turning_points || []).map((tp, i) => (
                  <div key={i} className="text-sm">
                    <span className="no mr-2">转折</span>
                    <span>{tp.desc}</span>
                    {tp.quote && (
                      <span className="text-muted">
                        {" "}
                        「{tp.quote.text}」
                        <TsLink bvid={vod.bvid} page={page} ms={tp.quote.start_ms} />
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* 整场总评 */}
        {overall && (
          <section>
            <SectionTitle>整场总评</SectionTitle>
            <p className="text-[15px] leading-loose">{overall.summary}</p>
          </section>
        )}

        {/* 战队 */}
        {teams.length > 0 && (
          <section>
            <SectionTitle>战队表现</SectionTitle>
            <div className="space-y-5">
              {teams.map((t) => (
                <div key={t.id}>
                  <div className="mb-2 flex flex-wrap items-center gap-3">
                    <span className="text-base font-medium tracking-wide">{t.subject_name}</span>
                    <SentimentTag sentiment={t.sentiment} />
                    <Rating value={t.rating} />
                  </div>
                  <p className="text-[15px] leading-loose text-muted">{t.summary}</p>
                  {(t.quotes || []).map((q, i) => (
                    <QuoteLine key={i} bvid={vod.bvid} page={page} quote={q} />
                  ))}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 选手（全过程评价 + 高光低谷） */}
        {players.length > 0 && (
          <section>
            <SectionTitle>选手点评</SectionTitle>
            <div className="space-y-6">
              {players.map((p) => (
                <div key={p.id} className="border-l-2 border-border/50 pl-4">
                  <div className="mb-2 flex flex-wrap items-center gap-3">
                    <span className="text-base font-medium tracking-wide">{p.subject_name}</span>
                    <SentimentTag sentiment={p.sentiment} />
                    <Rating value={p.rating} />
                  </div>
                  <p className="text-[15px] leading-loose text-muted">{p.summary}</p>
                  {p.extra?.highlight && (
                    <p className="mt-2 text-sm">
                      <span className="tag tag--accent mr-2">高光</span>
                      <span className="text-muted">{p.extra.highlight}</span>
                    </p>
                  )}
                  {p.extra?.lowlight && (
                    <p className="mt-1 text-sm">
                      <span className="tag text-seal mr-2">低谷</span>
                      <span className="text-muted">{p.extra.lowlight}</span>
                    </p>
                  )}
                  <div className="mt-2">
                    {(p.quotes || []).map((q, i) => (
                      <QuoteLine key={i} bvid={vod.bvid} page={page} quote={q} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 分锅 */}
        {blame && (
          <section>
            <SectionTitle>赛后分锅</SectionTitle>
            <p className="text-[15px] leading-loose">{blame.summary}</p>
            {(blame.extra?.main || []).length > 0 && (
              <div className="mt-3 space-y-1">
                {(blame.extra?.main || []).map((m, i) => (
                  <p key={i} className="text-sm text-muted">
                    <span className="seal-ai mr-2">锅</span>
                    <span className="font-medium">{m.name}</span>：{m.reason}
                  </p>
                ))}
              </div>
            )}
          </section>
        )}

        {/* 金句 */}
        {golden && (golden.quotes || []).length > 0 && (
          <section>
            <SectionTitle>金句时刻</SectionTitle>
            <div className="space-y-2">
              {(golden.quotes || []).map((q, i) => (
                <div key={i} className="text-sm">
                  <QuoteLine bvid={vod.bvid} page={page} quote={q} />
                  {q.context && <p className="ml-4 text-xs text-faint">{q.context}</p>}
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
