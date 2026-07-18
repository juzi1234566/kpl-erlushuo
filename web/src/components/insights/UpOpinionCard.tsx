"use client";

import Link from "next/link";
import { useState } from "react";
import type { CasterOpinion, DbCommentaryInsight, InsightQuote } from "@/lib/insights";
import { biliUrl, fmtTimestamp } from "@/lib/insights";

function SentimentTag({ sentiment }: { sentiment: string }) {
  const cls =
    sentiment === "好评" ? "tag tag--accent" : sentiment === "差评" ? "tag text-seal" : "tag";
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

/** 单局全部板块（BP/局势/选手/分锅/金句） */
function GameSections({
  rows,
  bvid,
  page,
}: {
  rows: DbCommentaryInsight[];
  bvid: string;
  page: number | null;
}) {
  const get = (t: DbCommentaryInsight["subject_type"]) => rows.find((i) => i.subject_type === t);
  const bp = get("bp");
  const flow = get("flow");
  const blame = get("blame");
  const golden = get("golden");
  const players = rows.filter((i) => i.subject_type === "player");

  return (
    <div className="space-y-6">
      {bp && (
        <section>
          <div className="mb-2 flex items-center gap-3">
            <p className="tag tag--accent">BP 与阵容</p>
            <Rating value={bp.rating} />
          </div>
          {bp.extra?.headline && <p className="mb-2 text-[15px] font-medium">{bp.extra.headline}</p>}
          <Points points={bp.extra?.points} />
          {(bp.extra?.predictions || []).map((q, i) => (
            <div key={i} className="mt-2 flex flex-wrap items-baseline gap-2 text-sm">
              <span
                className={
                  q.verdict === "打脸" ? "seal-ai" : q.verdict === "应验" ? "tag tag--accent" : "tag"
                }
              >
                {q.verdict === "打脸" ? "毒奶打脸" : q.verdict === "应验" ? "预言应验" : "待验证"}
              </span>
              <span className="text-muted">
                「{q.text}」
                <TsLink bvid={bvid} page={page} ms={q.start_ms} />
              </span>
              {q.note && <span className="text-xs text-faint">{q.note}</span>}
            </div>
          ))}
        </section>
      )}

      {flow && (
        <section>
          <p className="tag tag--accent mb-2">局势走向</p>
          <div className="space-y-1.5">
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
          {(flow.extra?.turning_points || []).map((tp, i) => (
            <div key={i} className="mt-1.5 flex gap-2 text-sm">
              <span className="seal-ai shrink-0">转折</span>
              <span>
                {tp.desc}
                {tp.quote && <TsLink bvid={bvid} page={page} ms={tp.quote.start_ms} />}
              </span>
            </div>
          ))}
        </section>
      )}

      {players.length > 0 && (
        <section>
          <p className="tag tag--accent mb-3">本局选手</p>
          <div className="grid gap-4 md:grid-cols-2">
            {players.map((p) => (
              <div key={p.id} className="rounded border border-border/40 p-3.5">
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <span className="font-semibold">{p.subject_name}</span>
                  <SentimentTag sentiment={p.sentiment} />
                  <Rating value={p.rating} />
                </div>
                {p.extra?.verdict && <p className="mb-1.5 text-sm font-medium">{p.extra.verdict}</p>}
                <Points points={p.extra?.points} />
                {(p.quotes || []).slice(0, 2).map((q, i) => (
                  <div key={i} className="mt-1.5">
                    <QuoteLine bvid={bvid} page={page} quote={q} />
                  </div>
                ))}
              </div>
            ))}
          </div>
        </section>
      )}

      {blame && (
        <section>
          <p className="tag tag--accent mb-2">本局复盘</p>
          {blame.extra?.headline && (
            <p className="mb-1.5 text-[15px] font-medium">{blame.extra.headline}</p>
          )}
          {(blame.extra?.main || []).map((m, i) => (
            <p key={i} className="text-sm text-muted">
              <span className="seal-ai mr-2">主责</span>
              <span className="font-semibold text-foreground">{m.name}</span> — {m.reason}
            </p>
          ))}
        </section>
      )}

      {golden && (golden.quotes || []).length > 0 && (
        <section>
          <p className="tag tag--accent mb-2">金句</p>
          <div className="space-y-1.5">
            {(golden.quotes || []).map((q, i) => (
              <div key={i}>
                <QuoteLine bvid={bvid} page={page} quote={q} />
                <p className="ml-4 mt-0.5 flex gap-3 text-xs text-faint">
                  {q.context && <span>{q.context}</span>}
                  <a
                    href={`/api/og/quote-card?text=${encodeURIComponent(q.text)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="tag--accent underline-offset-4 hover:underline"
                  >
                    生成分享卡 →
                  </a>
                </p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export default function UpOpinionCard({ opinion }: { opinion: CasterOpinion }) {
  const { vod, series, games } = opinion;
  const [openGame, setOpenGame] = useState<number | null>(null);

  const get = (t: DbCommentaryInsight["subject_type"]) => series.find((i) => i.subject_type === t);
  const overall = get("overall");
  const blame = get("blame");
  const seriesPlayers = series.filter((i) => i.subject_type === "player");
  const briefs = overall?.extra?.games_brief || [];

  return (
    <div className="plate p-6 md:p-9">
      {/* 头部：主播 + 整场结论 */}
      <div className="mb-5 border-b border-border/40 pb-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <h3 className="text-xl tracking-wider">{vod.caster_name || vod.up_name || "解说"}</h3>
            {overall && <SentimentTag sentiment={overall.sentiment} />}
            {overall && <Rating value={overall.rating} />}
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
        {overall?.extra?.headline && (
          <p className="mt-3 text-lg font-medium leading-snug">{overall.extra.headline}</p>
        )}
        {overall && (
          <div className="mt-2">
            <Points points={overall.extra?.points} />
          </div>
        )}
        {blame?.extra?.headline && (
          <p className="mt-3 text-[15px]">
            <span className="seal-ai mr-2">整场败因</span>
            <span className="text-muted">{blame.extra.headline}</span>
          </p>
        )}
      </div>

      {/* 整场选手总评 */}
      {seriesPlayers.length > 0 && (
        <section className="mb-6">
          <p className="tag tag--accent mb-3">整场选手总评</p>
          <div className="grid gap-4 md:grid-cols-2">
            {seriesPlayers.map((p) => (
              <div key={p.id} className="rounded border border-border/40 p-3.5">
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <Link
                    href={`/players/${encodeURIComponent(p.subject_name)}`}
                    className="font-semibold underline-offset-4 hover:underline"
                  >
                    {p.subject_name}
                  </Link>
                  <SentimentTag sentiment={p.sentiment} />
                  <Rating value={p.rating} />
                </div>
                {p.extra?.verdict && <p className="mb-1.5 text-sm font-medium">{p.extra.verdict}</p>}
                <Points points={p.extra?.points} />
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 分局：一局一行，点开看该局详情 */}
      <section>
        <p className="tag tag--accent mb-3">逐局详情</p>
        <div className="space-y-2">
          {games.map((g) => {
            const brief = briefs.find((b) => b.game_no === g.game_no)?.one_line;
            const open = openGame === g.game_no;
            return (
              <div key={g.game_no} className="rounded border border-border/40">
                <button
                  type="button"
                  onClick={() => setOpenGame(open ? null : g.game_no)}
                  className="flex w-full flex-wrap items-baseline gap-3 px-4 py-3 text-left transition-colors duration-300 hover:bg-[rgba(47,122,125,0.06)]"
                >
                  <span className="no shrink-0">第{g.game_no}局</span>
                  <span className="flex-1 text-[15px] text-muted">{brief || "点开看本局详情"}</span>
                  <span className="tag">{open ? "收起" : "展开"}</span>
                </button>
                {open && (
                  <div className="border-t border-border/30 px-4 py-5">
                    <GameSections rows={g.rows} bvid={vod.bvid} page={g.page} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
