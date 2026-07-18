import Link from "next/link";
import { fetchPlayerReviews, biliUrl, fmtTimestamp } from "@/lib/insights";
import Ornament from "@/components/Ornament";

export const dynamic = "force-dynamic";

function SentimentTag({ sentiment }: { sentiment: string }) {
  const cls =
    sentiment === "好评" ? "tag tag--accent" : sentiment === "差评" ? "tag text-seal" : "tag";
  return <span className={cls}>{sentiment}</span>;
}

export default async function PlayerPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name: raw } = await params;
  const name = decodeURIComponent(raw);
  const reviews = await fetchPlayerReviews(name);

  const good = reviews.filter((r) => r.sentiment === "好评").length;
  const bad = reviews.filter((r) => r.sentiment === "差评").length;
  const rated = reviews.filter((r) => r.rating);
  const avg = rated.length
    ? (rated.reduce((s, r) => s + (r.rating || 0), 0) / rated.length).toFixed(1)
    : null;

  return (
    <div className="mx-auto max-w-2xl space-y-12">
      <Link
        href="/matches"
        className="tag enter inline-block transition-colors duration-500 hover:text-foreground"
      >
        ← 返回赛程
      </Link>

      <header className="enter-1 text-center">
        <p className="tag tag--accent mb-4">选手 · 解说团评价档案</p>
        <h1 className="text-4xl tracking-[0.15em]">{name}</h1>
        <div className="mt-6 flex justify-center">
          <Ornament className="breathe" />
        </div>
        {reviews.length > 0 && (
          <p className="mt-5 text-sm text-muted">
            共 {reviews.length} 条评价 · 好评 {good} / 差评 {bad}
            {avg && ` · 平均 ★${avg}`}
          </p>
        )}
      </header>

      {reviews.length === 0 ? (
        <div className="plate enter-2 p-10 text-center">
          <p className="text-[15px] leading-loose text-muted">
            还没有收录对 {name} 的解说评价，完赛分析后会自动出现。
          </p>
        </div>
      ) : (
        <div className="enter-2 space-y-5">
          {reviews.map((r, i) => (
            <div key={i} className="plate p-5 md:p-6">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2.5">
                  <span className="font-semibold">{r.caster}</span>
                  <SentimentTag sentiment={r.sentiment} />
                  {r.rating && (
                    <span className="text-xs tracking-widest text-accent">
                      {"●".repeat(r.rating)}
                      {"○".repeat(5 - r.rating)}
                    </span>
                  )}
                </div>
                <Link
                  href={`/matches/${r.match_id}`}
                  className="tag transition-colors duration-500 hover:text-foreground"
                >
                  查看该场 →
                </Link>
              </div>
              {r.verdict && <p className="mb-2 text-[15px] font-medium">{r.verdict}</p>}
              <ul className="space-y-1">
                {r.points.map((pt, j) => (
                  <li key={j} className="flex gap-2 text-sm leading-relaxed text-muted">
                    <span className="text-accent">·</span>
                    <span>{pt}</span>
                  </li>
                ))}
              </ul>
              {r.quotes.slice(0, 1).map((q, j) => (
                <p key={j} className="mt-2 border-l-2 border-accent/30 pl-3 text-sm text-muted">
                  「{q.text}」
                  <a
                    href={biliUrl(r.bvid, q.start_ms, r.page_start)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="no ml-1 text-xs underline-offset-4 hover:underline"
                  >
                    [{fmtTimestamp(q.start_ms)}]
                  </a>
                </p>
              ))}
            </div>
          ))}
        </div>
      )}

      <p className="text-center text-xs leading-loose text-faint">
        评价由 AI 自动提取自各解说公开视频，仅代表解说个人观点，与本站立场无关。
      </p>
    </div>
  );
}
