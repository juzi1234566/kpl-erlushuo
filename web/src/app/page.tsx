import Link from "next/link";
import Ornament from "@/components/Ornament";

const 卖点 = [
  { 题: "BP 点评", 文: "这手 BP 布置了什么思路，赛前预判有没有应验" },
  { 题: "选手评价", 文: "各家解说眼中谁是本场关键，表现如何、原话为证" },
  { 题: "赛后复盘", 文: "胜负手在哪一波，解说怎么看关键决策" },
  { 题: "金句时刻", 文: "解说的精彩原声，点时间戳直跳原视频" },
];

export default function HomePage() {
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
