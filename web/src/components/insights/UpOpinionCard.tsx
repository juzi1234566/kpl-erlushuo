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
      className="no ml-1 text-xs underline-offset-4 hover:underline"
    >
      [{fmtTimestamp(ms)}]
    </a>
  );
}

/** 引用行：原话 + 跳转时间戳 */
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
    <p className="border-l-2 border-accent/30 pl-3 text-sm leading-relaxed text-muted">
      「{quote.text}」
      <TsLink bvid={bvid} page={page} ms={quote.start_ms} />
    </p>
  );
}

/** 要点列表：短句 bullet，扫一眼抓重点 */
function Points({ points }: { points?: string[] }) {
  if (!points?.length) return null;
  return (
    <ul className="space-y-1.5">
      {points.map((p, i) => (
        <li key={i} className="flex gap-2 text-[15px] leading-relaxed">
          <span className="text-accent">·</span>
          <span>{p}</span>
        </li>
      ))}
    </ul>
  );
}

/** 板块钩子：一句话结论，加粗放大 */
function Headline({ text }: { text?: string }) {
  if (!text) return null;
  return <p className="mb-3 text-base font-medium leading-snug">{text}</p>;
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
      {/* 头部：主播名 + 一句话总评 */}
      <div className="mb-6 border-b border-border/40 pb-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <h3 className="text-xl tracking-wider">
              {vod.caster_name || vod.up_name || "二路解说"}
            </h3>
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
        {overall?.extra?.headline && (
          <p className="mt-3 text-lg font-medium leading-snug">{overall.extra.headline}</p>
        )}
        {overall && <div className="mt-2"><Points points={overall.extra?.points} /></div>}
      </div>

      <div className="space-y-8">
        {/* BP */}
        {bp && (
          <section>
            <div className="mb-2 flex items-center gap-3">
              <p className="tag tag--accent">BP 与阵容</p>
              <Rating value={bp.rating} />
            </div>
            <Headline text={bp.extra?.headline} />
            <Points points={bp.extra?.points} />
            {(bp.extra?.predictions || []).length > 0 && (
              <div className="mt-3 space-y-2">
                {(bp.extra?.predictions || []).map((q, i) => (
                  <div key={i} className="flex flex-wrap items-baseline gap-2 text-sm">
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

        {/* 局势走向：三阶段各一行 */}
        {flow && (
          <section>
            <p className="tag tag--accent mb-3">局势走向</p>
            <div className="space-y-2">
              {flow.summary.split("\n").map((line, i) => {
                const m = line.match(/^【(.+?)】(.*)$/);
                return (
                  <div key={i} className="flex gap-3 text-[15px] leading-relaxed">
                    <span className="no w-10 shrink-0">{m ? m[1] : ""}</span>
                    <span>{m ? m[2] : line}</span>
                  </div>
                );
              })}
            </div>
            {(flow.extra?.turning_points || []).length > 0 && (
              <div className="mt-3 space-y-1.5">
                {(flow.extra?.turning_points || []).map((tp, i) => (
                  <div key={i} className="flex gap-2 text-sm">
                    <span className="seal-ai shrink-0">转折</span>
                    <span>
                      {tp.desc}
                      {tp.quote && <TsLink bvid={vod.bvid} page={page} ms={tp.quote.start_ms} />}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* 选手：结论加粗 + 要点 + 高光低谷 */}
        {players.length > 0 && (
          <section>
            <p className="tag tag--accent mb-4">选手点评</p>
            <div className="grid gap-5 md:grid-cols-2">
              {players.map((p) => (
                <div key={p.id} className="rounded border border-border/40 p-4">
                  <div className="mb-1.5 flex flex-wrap items-center gap-2.5">
                    <span className="text-base font-semibold tracking-wide">{p.subject_name}</span>
                    <SentimentTag sentiment={p.sentiment} />
                    <Rating value={p.rating} />
                  </div>
                  {p.extra?.verdict && (
                    <p className="mb-2 text-[15px] font-medium leading-snug">{p.extra.verdict}</p>
                  )}
                  <Points points={p.extra?.points} />
                  {(p.extra?.highlight || p.extra?.lowlight) && (
                    <div className="mt-2 space-y-1 text-sm">
                      {p.extra?.highlight && (
                        <p>
                          <span className="tag tag--accent mr-2">高光</span>
                          <span className="text-muted">{p.extra.highlight}</span>
                        </p>
                      )}
                      {p.extra?.lowlight && (
                        <p>
                          <span className="tag text-seal mr-2">低谷</span>
                          <span className="text-muted">{p.extra.lowlight}</span>
                        </p>
                      )}
                    </div>
                  )}
                  {(p.quotes || []).length > 0 && (
                    <div className="mt-2.5 space-y-1.5">
                      {(p.quotes || []).map((q, i) => (
                        <QuoteLine key={i} bvid={vod.bvid} page={page} quote={q} />
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 战队 */}
        {teams.length > 0 && (
          <section>
            <p className="tag tag--accent mb-4">战队表现</p>
            <div className="grid gap-5 md:grid-cols-2">
              {teams.map((t) => (
                <div key={t.id}>
                  <div className="mb-1.5 flex flex-wrap items-center gap-2.5">
                    <span className="text-base font-semibold tracking-wide">{t.subject_name}</span>
                    <SentimentTag sentiment={t.sentiment} />
                    <Rating value={t.rating} />
                  </div>
                  {t.extra?.verdict && (
                    <p className="mb-2 text-[15px] font-medium leading-snug">{t.extra.verdict}</p>
                  )}
                  <Points points={t.extra?.points} />
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 分锅 */}
        {blame && (
          <section>
            <p className="tag tag--accent mb-3">赛后分锅</p>
            <Headline text={blame.extra?.headline} />
            <div className="space-y-1.5">
              {(blame.extra?.main || []).map((m, i) => (
                <p key={i} className="text-[15px]">
                  <span className="seal-ai mr-2">锅</span>
                  <span className="font-semibold">{m.name}</span>
                  <span className="text-muted"> — {m.reason}</span>
                </p>
              ))}
            </div>
          </section>
        )}

        {/* 金句 */}
        {golden && (golden.quotes || []).length > 0 && (
          <section>
            <p className="tag tag--accent mb-3">金句时刻</p>
            <div className="space-y-2">
              {(golden.quotes || []).map((q, i) => (
                <div key={i}>
                  <QuoteLine bvid={vod.bvid} page={page} quote={q} />
                  {q.context && <p className="ml-4 mt-0.5 text-xs text-faint">{q.context}</p>}
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
