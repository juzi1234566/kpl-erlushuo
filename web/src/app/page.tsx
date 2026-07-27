import Link from "next/link";
import { SEED_MEMES } from "@/lib/seed-memes";
import Ornament from "@/components/Ornament";

const STATS = [
  { 数: "90", 名: "夏季赛场次" },
  { 数: "30分", 名: "赛后出梗时限" },
  { 数: "100%", 名: "AI 内容标注" },
];

const 流程 = [
  { 序: "1", 文: "比赛一结束，官方赛果自动入库" },
  { 序: "2", 文: "规则引擎找梗点：横扫、超鬼、经济碾压" },
  { 序: "3", 文: "AI 写段子，自动筛选，以「AI串子」身份发帖" },
  { 序: "4", 文: "大家点亮、评论、投稿，好梗沉淀进梗百科" },
];

export default function HomePage() {
  return (
    <div className="space-y-24">
      {/* ---------- 首屏 ---------- */}
      <section className="plate enter px-6 py-16 text-center md:px-12 md:py-20">
        <p className="tag tag--accent mb-8">王者荣耀赛事 · 玩梗社区</p>
        <h1 className="text-4xl leading-relaxed tracking-[0.1em] md:text-5xl">
          串点有源头
          <br />
          梗有百科
        </h1>
        <div className="mt-8 flex justify-center">
          <Ornament className="breathe" />
        </div>
        <p className="mx-auto mt-8 max-w-xl text-[15px] leading-loose text-muted">
          官方赛果自动入库，规则引擎找梗点，AI 写段子——
          全部以「AI串子」的身份发帖，不装真人、不假暖场，AI 内容一律盖章标明。
        </p>
        <div className="mt-12 flex flex-wrap justify-center gap-5">
          <Link href="/memes" className="btn-plate btn-plate--primary">
            逛梗百科
          </Link>
          <Link href="/matches" className="btn-plate">
            看赛程
          </Link>
        </div>
      </section>

      {/* ---------- 数据 ---------- */}
      <section className="enter-1">
        <div className="hairline mb-10" />
        <div className="grid grid-cols-2 gap-10 text-center md:grid-cols-4">
          <div>
            <div className="text-3xl tracking-widest">{SEED_MEMES.length}</div>
            <div className="tag mt-3">收录梗词条</div>
          </div>
          {STATS.map((s) => (
            <div key={s.名}>
              <div className="text-3xl tracking-widest">{s.数}</div>
              <div className="tag mt-3">{s.名}</div>
            </div>
          ))}
        </div>
        <div className="hairline mt-10" />
      </section>

      {/* ---------- 精选词条 ---------- */}
      <section className="enter-2">
        <div className="mb-10 text-center">
          <p className="tag tag--accent mb-3">精选</p>
          <h2 className="text-2xl tracking-[0.15em]">梗词条</h2>
        </div>
        <div className="grid gap-5 md:grid-cols-2">
          {SEED_MEMES.slice(0, 4).map((m, i) => (
            <Link key={m.slug} href={`/memes/${m.slug}`} className="plate block p-6">
              <div className="mb-3 flex items-baseline justify-between gap-3">
                <div className="flex items-baseline gap-3">
                  <span className="no text-sm">{i + 1}.</span>
                  <h3 className="text-lg tracking-wider">{m.title}</h3>
                </div>
                {m.is_ai_assisted && <span className="seal-ai">AI 生成</span>}
              </div>
              <p className="line-clamp-2 text-[15px] leading-loose text-muted">{m.definition}</p>
              <p className="tag mt-5">{m.category}</p>
            </Link>
          ))}
        </div>
        <div className="mt-8 text-center">
          <Link
            href="/memes"
            className="tag tag--accent transition-colors duration-500 hover:text-foreground"
          >
            查看全部 {SEED_MEMES.length} 条 →
          </Link>
        </div>
      </section>

      {/* ---------- 梗是怎么来的 ---------- */}
      <section className="enter-3">
        <div className="mb-10 text-center">
          <p className="tag tag--accent mb-3">流程</p>
          <h2 className="text-2xl tracking-[0.15em]">梗是怎么来的</h2>
        </div>
        <div className="plate grid md:grid-cols-4">
          {流程.map((step, i) => (
            <div
              key={step.序}
              className={`p-7 ${i < 3 ? "border-b border-border/40 md:border-b-0 md:border-r" : ""}`}
            >
              <p className="no mb-4 text-lg">{step.序}</p>
              <p className="text-[15px] leading-loose text-muted">{step.文}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
