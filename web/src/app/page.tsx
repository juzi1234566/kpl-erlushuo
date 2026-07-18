import Link from "next/link";
import { listAnalyzedMatches } from "@/lib/insights";
import Ornament from "@/components/Ornament";

export const dynamic = "force-dynamic";

const 卖点 = [
  { 题: "BP 点评", 文: "教练这手 ban 选亏不亏，赛前预测应验还是打脸" },
  { 题: "选手评价", 文: "谁 carry 谁拉胯，各家解说打分与原话引用" },
  { 题: "赛后分锅", 文: "这把输在谁，解说点名+锅因，一目了然" },
  { 题: "金句时刻", 文: "毒奶、暴论、整活原声，点时间戳直跳原视频" },
];

function fmtDate(iso: string | null): string {
  if (!iso) return "";
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? `${Number(m[2])}月${Number(m[3])}日` : "";
}

export default async function HomePage() {
  const analyzed = await listAnalyzedMatches();

  return (
    <div className="space-y-20">
      {/* ---------- 首屏 ---------- */}
      <section className="plate enter px-6 py-16 text-center md:px-12 md:py-20">
        <p className="tag tag--accent mb-8">KPL 二路解说观点聚合</p>
        <h1 className="text-4xl leading-relaxed tracking-[0.1em] md:text-5xl">
          比赛打得怎么样
          <br />
          听二路怎么说
        </h1>
        <div className="mt-8 flex justify-center">
          <Ornament className="breathe" />
        </div>
        <p className="mx-auto mt-8 max-w-xl text-[15px] leading-loose text-muted">
          二路解说视频看不完？AI 自动听完每一家，把观点整理成 3 分钟能看完的赛评：
          谁打得好、锅是谁的、预测有没有应验——原话引用全部可跳转回原视频。
        </p>
        <div className="mt-12 flex flex-wrap justify-center gap-5">
          <Link href="/matches" className="btn-plate btn-plate--primary">
            看比赛观点
          </Link>
          <Link href="/about" className="btn-plate">
            这是什么
          </Link>
        </div>
      </section>

      {/* ---------- 最新观点 ---------- */}
      {analyzed.length > 0 && (
        <section className="enter-1">
          <div className="mb-8 text-center">
            <p className="tag tag--accent mb-3">最新</p>
            <h2 className="text-2xl tracking-[0.15em]">已出观点的比赛</h2>
          </div>
          <div className="grid gap-5 md:grid-cols-2">
            {analyzed.slice(0, 6).map((m) => (
              <Link key={m.match_id} href={`/matches/${m.match_id}`} className="plate block p-6">
                <p className="tag mb-3">
                  {fmtDate(m.match?.start_time || null)}
                  {m.match?.stage_desc ? ` · ${m.match.stage_desc}` : ""}
                </p>
                <p className="text-lg tracking-wider">
                  {m.teamNames[0] || "对阵"}{" "}
                  <span className="no mx-1 text-sm">
                    {m.match ? `${m.match.score1} : ${m.match.score2}` : "对"}
                  </span>{" "}
                  {m.teamNames[1] || ""}
                </p>
                <p className="tag tag--accent mt-4">
                  {m.casters.length} 位解说观点 · {m.casters.slice(0, 4).join(" / ")}
                </p>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* ---------- 能看到什么 ---------- */}
      <section className="enter-2">
        <div className="mb-8 text-center">
          <p className="tag tag--accent mb-3">你能看到什么</p>
          <h2 className="text-2xl tracking-[0.15em]">每场比赛四个板块</h2>
        </div>
        <div className="plate grid md:grid-cols-4">
          {卖点.map((s, i) => (
            <div
              key={s.题}
              className={`p-7 ${i < 3 ? "border-b border-border/40 md:border-b-0 md:border-r" : ""}`}
            >
              <p className="mb-3 text-base font-semibold tracking-wide">{s.题}</p>
              <p className="text-sm leading-loose text-muted">{s.文}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
